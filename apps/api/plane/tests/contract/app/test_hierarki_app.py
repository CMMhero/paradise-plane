# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tes kontrak hierarki peran
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tes kontrak: jenjang, pengawasan divisi, dan gerbang penugasan.

Rancangan + pertanyaan yang belum dijawab: `.herdr/hierarki-desain.md`.

Yang dibuktikan di sini bukan cuma "yang boleh bisa", tapi juga **yang tidak boleh
memang tidak bisa** — bagian yang paling mudah hilang saat seseorang merapikan kode
enam bulan lagi.

Kontrol negatif yang dikunci:

* **Dengan katup MATI (default), tidak ada satu pun perilaku yang berubah.** Ini
  kontrak terpenting di berkas ini: 88 user tidak boleh terpengaruh oleh fitur yang
  belum diputuskan.
* Anggota tidak bisa menugaskan ke orang lain (dengan katup dinyalakan).
* Supervisor tidak bisa menugaskan di divisi yang BUKAN diawasinya.
* Pelaku yang tidak diketahui ditolak (gagal ke arah aman, prinsip #3).
* `tingkat_anggota` mengembalikan **None** untuk jenjang yang belum diisi — bukan 10
  ("member"). Kalau ini berubah, "datanya kurang" diam-diam jadi "dia staf".
* Dua baris jenjang aktif untuk satu orang DITOLAK database. Tanpa ini, orangnya punya
  dua jenjang sekaligus dan hasilnya bergantung urutan baris — gagal senyap.
* Orang biasa TIDAK bisa membaca `GET /api/instances/hierarki/`.
* Baris jenjang yang pernah di-soft-delete bisa dipasang lagi (jebakan A21).
"""

from uuid import uuid4

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from plane.db.models import (
    Issue,
    IssueAssignee,
    IssueTemplate,
    JabatanOrganisasi,
    PengawasanDivisi,
    PersetujuanPenugasan,
    Project,
    ProjectMember,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    User,
    WorkspaceMember,
)
from plane.license.api.views.hierarki import InstanceHierarkiEndpoint
from plane.license.models import Instance, InstanceAdmin
from plane.utils.hierarki import (
    BUTUH_PERSETUJUAN,
    FLAG_GERBANG,
    TANPA_ATASAN,
    _bawahan_ids,
    calon_penyetuju,
    divisi_diawasi,
    galat_penugasan,
    gerbang_aktif,
    periksa_penugasan,
    tingkat_anggota,
)
URL_HIERARKI = "/api/instances/hierarki/"
URL_ISSUES = "/api/workspaces/{slug}/projects/{project_id}/issues/"
URL_PERSETUJUAN = "/api/workspaces/{slug}/projects/{project_id}/persetujuan-penugasan/"
URL_DRAFTS = "/api/workspaces/{slug}/draft-issues/"
URL_TEMPLATE_APPLY = "/api/workspaces/{slug}/projects/{project_id}/issue-templates/{template_id}/apply/"
URL_ISSUE_DETAIL = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/"


# --------------------------------------------------------------------------
# Pembantu
# --------------------------------------------------------------------------


def _buat_user(prefix, workspace=None, peran_workspace=15):
    unik = uuid4().hex[:8]
    user = User.objects.create(
        email=f"{prefix}-{unik}@plane.so",
        username=f"{prefix}_{unik}",
        first_name=prefix.capitalize(),
        last_name="Uji",
    )
    user.set_password("test-password")
    user.save()
    if workspace is not None:
        WorkspaceMember.objects.create(workspace=workspace, member=user, role=peran_workspace)
    return user


def _buat_project(nama, identifier, workspace, pembuat, anggota=()):
    project = Project.objects.create(
        name=nama, identifier=identifier, workspace=workspace, created_by=pembuat
    )
    for user, role in anggota:
        ProjectMember.objects.create(project=project, member=user, workspace=workspace, role=role)
    return project


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# --------------------------------------------------------------------------
# Fixtures: dua divisi + satu orang luar + satu instance God Mode
# --------------------------------------------------------------------------


@pytest.fixture
def bos_divisi_a(db, workspace):
    return _buat_user("bosa", workspace, peran_workspace=15)


@pytest.fixture
def staf_a(db, workspace):
    return _buat_user("stafa", workspace, peran_workspace=15)


@pytest.fixture
def staf_a2(db, workspace):
    return _buat_user("stafa2", workspace, peran_workspace=15)


@pytest.fixture
def bos_divisi_b(db, workspace):
    return _buat_user("bosb", workspace, peran_workspace=15)


@pytest.fixture
def staf_b(db, workspace):
    return _buat_user("stafb", workspace, peran_workspace=15)


@pytest.fixture
def direktur(db, workspace):
    return _buat_user("dir", workspace, peran_workspace=15)


@pytest.fixture
def orang_luar(db, workspace):
    return _buat_user("luar", workspace, peran_workspace=15)


@pytest.fixture
def divisi_a(db, workspace, bos_divisi_a, staf_a, staf_a2):
    """Divisi A: Bos (supervisor) + dua staf."""
    return _buat_project(
        "Divisi A",
        "DIVA",
        workspace,
        bos_divisi_a,
        anggota=[(bos_divisi_a, 20), (staf_a, 15), (staf_a2, 15)],
    )


@pytest.fixture
def divisi_b(db, workspace, bos_divisi_b, staf_b):
    """Divisi B: Bos B (supervisor) + satu staf. Bos A BUKAN anggotanya."""
    return _buat_project(
        "Divisi B",
        "DIVB",
        workspace,
        bos_divisi_b,
        anggota=[(bos_divisi_b, 20), (staf_b, 15)],
    )


@pytest.fixture
def jenjang(db, workspace, bos_divisi_a, bos_divisi_b, staf_a, staf_a2, staf_b, direktur):
    """Jenjang awal: 2 supervisor, 1 direktur, 3 member."""
    for user, tingkat in (
        (direktur, TINGKAT_DIREKTUR),
        (bos_divisi_a, TINGKAT_SUPERVISOR),
        (bos_divisi_b, TINGKAT_SUPERVISOR),
        (staf_a, TINGKAT_MEMBER),
        (staf_a2, TINGKAT_MEMBER),
        (staf_b, TINGKAT_MEMBER),
    ):
        JabatanOrganisasi.objects.create(workspace=workspace, member=user, tingkat=tingkat)
    return True


@pytest.fixture
def instance_god_mode(db):
    return Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-hierarki-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )


@pytest.fixture
def super_admin(db, instance_god_mode, workspace):
    user = _buat_user("super", workspace, peran_workspace=20)
    InstanceAdmin.objects.create(instance=instance_god_mode, user=user, role=20)
    return user


# --------------------------------------------------------------------------
# 1. Penyimpanan jenjang
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestJabatanOrganisasi:
    @pytest.mark.django_db
    def test_jenjang_belum_diisi_mengembalikan_None_bukan_member(self, workspace, staf_a):
        """Kontrak inti: "datanya kurang" != "dia staf"."""
        assert tingkat_anggota(staf_a.id, workspace.id) is None

    @pytest.mark.django_db
    def test_dua_jenjang_aktif_untuk_satu_orang_DITOLAK(self, workspace, staf_a):
        """Tanpa constraint parsial ini, orangnya punya dua jenjang sekaligus.

        `unique_together` saja TIDAK cukup: di Postgres NULL tidak sama dengan NULL,
        jadi dua baris ber-`deleted_at = NULL` tetap lolos.
        """
        JabatanOrganisasi.objects.create(workspace=workspace, member=staf_a, tingkat=TINGKAT_MEMBER)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                JabatanOrganisasi.objects.create(
                    workspace=workspace, member=staf_a, tingkat=TINGKAT_SUPERVISOR
                )

    @pytest.mark.django_db
    def test_multi_departemen_diperbolehkan_untuk_orang_yang_sama(self, workspace, staf_a):
        """2026-10-23: satu orang boleh punya dua baris beda departemen.

        Constraint parsial hanya melarang duplikat (orang, departemen) yang sama."""
        from plane.db.models import Departemen, Divisi

        div = Divisi.objects.create(workspace=workspace, kode="D", nama="Div")
        a = Departemen.objects.create(workspace=workspace, divisi=div, kode="A", nama="A")
        b = Departemen.objects.create(workspace=workspace, divisi=div, kode="B", nama="B")
        JabatanOrganisasi.objects.create(
            workspace=workspace, member=staf_a, tingkat=TINGKAT_SUPERVISOR, departemen=a
        )
        JabatanOrganisasi.objects.create(
            workspace=workspace, member=staf_a, tingkat=TINGKAT_SUPERVISOR, departemen=b
        )
        assert JabatanOrganisasi.objects.filter(workspace=workspace, member=staf_a).count() == 2

    @pytest.mark.django_db
    def test_departemen_sama_dua_kali_DITOLAK(self, workspace, staf_a):
        """Duplikat (orang, departemen) yang sama tetap ditolak."""
        from plane.db.models import Departemen, Divisi

        div = Divisi.objects.create(workspace=workspace, kode="D", nama="Div")
        a = Departemen.objects.create(workspace=workspace, divisi=div, kode="A", nama="A")
        JabatanOrganisasi.objects.create(
            workspace=workspace, member=staf_a, tingkat=TINGKAT_SUPERVISOR, departemen=a
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                JabatanOrganisasi.objects.create(
                    workspace=workspace, member=staf_a, tingkat=TINGKAT_MEMBER, departemen=a
                )

    @pytest.mark.django_db
    def test_jenjang_bisa_dipasang_lagi_sesudah_dicabut(self, workspace, staf_a):
        """Jebakan A21: manager bawaan menyaring baris ber-deleted_at.

        Pakai `all_objects` + hidupkan kembali, bukan `create()` kedua -- kalau tidak,
        pencabutan jenjang membuatnya tidak bisa dipasang lagi selamanya.
        """
        baris = JabatanOrganisasi.objects.create(workspace=workspace, member=staf_a, tingkat=TINGKAT_MEMBER)
        baris.delete()

        lama = JabatanOrganisasi.all_objects.filter(workspace=workspace, member=staf_a).first()
        assert lama is not None and lama.deleted_at is not None
        lama.deleted_at = None
        lama.tingkat = TINGKAT_SUPERVISOR
        lama.save(update_fields=["deleted_at", "tingkat"])

        assert tingkat_anggota(staf_a.id, workspace.id) == TINGKAT_SUPERVISOR


# --------------------------------------------------------------------------
# 2. "Divisi yang dia bawahi"
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestPengawasanDivisi:
    @pytest.mark.django_db
    def test_direktur_mengawasi_semua_divisi_tanpa_baris_eksplisit(
        self, workspace, direktur, divisi_a, divisi_b, jenjang
    ):
        """Kata user: "direktur bisa create task cross divisi manapun karena tingkat teratas"."""
        diawasi = divisi_diawasi(direktur.id, workspace.id)
        assert {divisi_a.id, divisi_b.id} <= diawasi

    @pytest.mark.django_db
    def test_supervisor_mengawasi_divisinya_sendiri(self, workspace, bos_divisi_a, divisi_a, divisi_b, jenjang):
        diawasi = divisi_diawasi(bos_divisi_a.id, workspace.id)
        assert divisi_a.id in diawasi
        assert divisi_b.id not in diawasi

    @pytest.mark.django_db
    def test_baris_eksplisit_di_luar_keanggotaan_DIABAIKAN(self, workspace, bos_divisi_a, divisi_a, divisi_b, jenjang):
        """Keputusan user 2026-10-15: "tidak cross divisi kecuali direktur".

        Rancangan pertama saya membiarkan baris `PengawasanDivisi` memberi kewenangan
        lintas divisi. Itu bertabrakan dengan keputusan user, jadi sekarang baris
        eksplisit **dipotong** ke divisi tempat orangnya memang anggota. Satu baris salah
        isi (atau warisan) tidak lagi bisa memberi kewenangan lintas divisi -- dan itu
        penting karena kegagalannya akan senyap.

        Efeknya ke direktur diuji terpisah: bagi dia, semua divisi memang sah.
        """
        JabatanOrganisasi.objects.filter(workspace=workspace, member=bos_divisi_a).update(
            tingkat=TINGKAT_MANAGER
        )
        PengawasanDivisi.objects.create(workspace=workspace, project=divisi_b, member=bos_divisi_a)

        diawasi = divisi_diawasi(bos_divisi_a.id, workspace.id)
        assert diawasi == {divisi_a.id}, "baris di divisi yang bukan anggotanya harus diabaikan"

    @pytest.mark.django_db
    def test_direktur_dengan_baris_eksplisit_DIBATASI(
        self, workspace, direktur, divisi_a, divisi_b, jenjang
    ):
        """Bagi direktur, baris eksplisit MEMBATASI, bukan memperluas.

        Gunanya nyata: direktur operasional yang hanya mengurus sebagian divisi tidak
        perlu diberi tahu seluruh papan perusahaan.
        """
        assert {divisi_a.id, divisi_b.id} <= divisi_diawasi(direktur.id, workspace.id)
        PengawasanDivisi.objects.create(workspace=workspace, project=divisi_a, member=direktur)
        assert divisi_diawasi(direktur.id, workspace.id) == {divisi_a.id}

    @pytest.mark.django_db
    def test_baris_eksplisit_di_divisi_sendiri_tetap_berlaku(
        self, workspace, bos_divisi_a, staf_a, divisi_a, jenjang
    ):
        """Pasangan positifnya: pengawasan di divisi sendiri tetap dihormati."""
        PengawasanDivisi.objects.create(workspace=workspace, project=divisi_a, member=bos_divisi_a)
        assert divisi_diawasi(bos_divisi_a.id, workspace.id) == {divisi_a.id}

    @pytest.mark.django_db
    def test_tanpa_jenjang_tidak_mengawasi_apa_pun(self, workspace, orang_luar, divisi_a):
        assert divisi_diawasi(orang_luar.id, workspace.id) == set()

    @pytest.mark.django_db
    def test_calon_penyetuju_hanya_orang_di_ATAS_pembuat_di_divisi_itu(
        self, workspace, bos_divisi_a, bos_divisi_b, direktur, staf_a, staf_a2, divisi_a, divisi_b, jenjang
    ):
        penyetuju_a = calon_penyetuju(workspace.id, divisi_a.id, tingkat_pembuat=TINGKAT_MEMBER)
        # Direktur mengawasi SEMUA divisi, jadi ia ikut berwenang. Supervisor divisi A
        # juga. Yang tidak boleh: supervisor divisi LAIN, dan sesama staf.
        assert set(penyetuju_a) == {bos_divisi_a.id, direktur.id}
        assert bos_divisi_b.id not in penyetuju_a
        assert staf_a.id not in penyetuju_a
        assert staf_a2.id not in penyetuju_a

        # Direktur tidak punya atasan: tidak ada yang lebih tinggi darinya.
        assert calon_penyetuju(workspace.id, divisi_a.id, tingkat_pembuat=TINGKAT_DIREKTUR) == []


# --------------------------------------------------------------------------
# 3. Gerbang penugasan — dengan katup MATI (kontrak terpenting)
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestKatupMati:
    @pytest.mark.django_db
    def test_katup_mati_secara_default(self, monkeypatch):
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        assert gerbang_aktif() is False

    @pytest.mark.django_db
    def test_dengan_katup_mati_anggota_boleh_menugaskan_siapa_pun(
        self, workspace, staf_a, staf_a2, divisi_a, jenjang, monkeypatch
    ):
        """Ini yang menjamin 88 user tidak berubah perilakunya.

        Anggota menugaskan orang lain: justru inilah yang nanti dilarang. Dengan katup
        mati, ia HARUS lolos — kalau tidak, fitur yang belum diputuskan sudah mengubah
        pekerjaan orang.
        """
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        assert galat_penugasan(divisi_a.id, [staf_a2.id], actor=staf_a) is None
        assert periksa_penugasan(divisi_a.id, [staf_a2.id], actor=staf_a) is None

    @pytest.mark.django_db
    def test_dengan_katup_mati_tidak_menyentuh_database(
        self, workspace, staf_a, staf_a2, divisi_a, monkeypatch, django_assert_num_queries
    ):
        """Katup tertutup harus benar-benar gratis, bukan 'lolos setelah memeriksa'."""
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        with django_assert_num_queries(0):
            assert galat_penugasan(divisi_a.id, [staf_a2.id], actor=staf_a) is None


# --------------------------------------------------------------------------
# 4. Gerbang penugasan — dengan katup dinyalakan
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestGerbangPenugasan:
    @pytest.mark.django_db
    def test_anggota_hanya_boleh_assign_dirinya_sendiri(
        self, workspace, staf_a, staf_a2, divisi_a, jenjang
    ):
        """Kata user: "normal member ... hanya bisa assign diri sendiri"."""
        assert galat_penugasan(divisi_a.id, [staf_a.id], actor=staf_a, abaikan_katup=True) is None

        galat = galat_penugasan(divisi_a.id, [staf_a2.id], actor=staf_a, abaikan_katup=True)
        assert galat, "anggota menugaskan orang lain seharusnya ditolak"

    @pytest.mark.django_db
    def test_tugas_tanpa_penerima_tidak_pernah_butuh_gerbang(self, workspace, staf_a, divisi_a, jenjang):
        """Approval melekat pada PENUGASAN, bukan pada pembuatan tugas."""
        assert galat_penugasan(divisi_a.id, [], actor=staf_a, abaikan_katup=True) is None
        assert galat_penugasan(divisi_a.id, None, actor=staf_a, abaikan_katup=True) is None

    @pytest.mark.django_db
    def test_supervisor_boleh_menugaskan_di_divisi_yang_diawasinya(
        self, workspace, bos_divisi_a, staf_a, staf_a2, divisi_a, jenjang
    ):
        assert galat_penugasan(divisi_a.id, [staf_a.id, staf_a2.id], actor=bos_divisi_a, abaikan_katup=True) is None

    @pytest.mark.django_db
    def test_supervisor_DITOLAK_di_divisi_yang_bukan_diawasinya(
        self, workspace, bos_divisi_a, staf_b, divisi_a, divisi_b, jenjang
    ):
        """Kontrol negatif yang paling penting: kewenangan tidak bocor antar divisi."""
        galat = galat_penugasan(divisi_b.id, [staf_b.id], actor=bos_divisi_a, abaikan_katup=True)
        assert galat, "supervisor divisi A seharusnya tidak boleh menugaskan di divisi B"

    @pytest.mark.django_db
    def test_direktur_otomatis_anggota_semua_divisi(
        self, workspace, direktur, staf_a, staf_b, divisi_a, divisi_b, jenjang
    ):
        """Keputusan user: "by default, direktur can view all division in projects".

        Signal `plane/db/direktur.py` menjadikan direktur anggota setiap project
        di workspace-nya (saat project dibuat DAN saat seseorang diangkat
        direktur), jadi KEP-02 tidak lagi menguncinya keluar. Pertanyaan #13 di
        rancangan TERJAWAB oleh keputusan ini: jawabannya opsi (a), keanggotaan
        otomatis — bukan Intake/lintas divisi.
        """
        from plane.db.direktur import direktur_user_ids, sinkronkan_direktur

        assert direktur.id in direktur_user_ids(workspace.id)
        # Signal sudah menyusulkan saat fixture `jenjang` lahir, jadi barisnya
        # ADA walau sinkron ulang tidak mengubah apa-apa.
        assert sinkronkan_direktur(workspace_id=workspace.id) == 0
        assert ProjectMember.objects.filter(project=divisi_a, member=direktur, is_active=True).exists()
        assert ProjectMember.objects.filter(project=divisi_b, member=direktur, is_active=True).exists()

        assert galat_penugasan(divisi_a.id, [staf_a.id], actor=direktur, abaikan_katup=True) is None
        assert galat_penugasan(divisi_b.id, [staf_b.id], actor=direktur, abaikan_katup=True) is None

    @pytest.mark.django_db
    def test_pengangkatan_direktur_disusulkan_ke_project_lama(
        self, workspace, staf_a, divisi_a, divisi_b, jenjang
    ):
        """Staf yang naik jadi direktur langsung bisa masuk semua divisinya."""
        # Satu orang satu baris: naik pangkat = ubah barisnya, bukan buat baru.
        baris = JabatanOrganisasi.objects.get(workspace=workspace, member=staf_a)
        baris.tingkat = TINGKAT_DIREKTUR
        baris.save(update_fields=["tingkat"])

        assert ProjectMember.objects.filter(project=divisi_a, member=staf_a, is_active=True).exists()
        assert ProjectMember.objects.filter(project=divisi_b, member=staf_a, is_active=True).exists()

    @pytest.mark.django_db
    def test_pelaku_tidak_diketahui_DITOLAK(self, workspace, staf_a, divisi_a, jenjang):
        """Prinsip #3: gagal ke arah aman. Termasuk jalur Celery yang tidak punya aktor."""
        galat = galat_penugasan(divisi_a.id, [staf_a.id], actor=None, abaikan_katup=True)
        assert galat, "pelaku tidak diketahui seharusnya ditolak, bukan diloloskan"

    @pytest.mark.django_db
    def test_orang_di_luar_divisi_DITOLAK(self, workspace, orang_luar, staf_a, divisi_a, jenjang):
        """Batas KEP-02, dipertahankan sebagai pertahanan kedua."""
        galat = galat_penugasan(divisi_a.id, [staf_a.id], actor=orang_luar, abaikan_katup=True)
        assert galat

    @pytest.mark.django_db
    def test_jenjang_belum_diisi_boleh_assign_diri_sendiri(
        self, workspace, orang_luar, divisi_a, jenjang
    ):
        """Kekosongan jenjang TIDAK boleh berarti orang tidak bisa bekerja.

        Ia hanya kehilangan kewenangan menugaskan orang lain.
        """
        ProjectMember.objects.create(project=divisi_a, member=orang_luar, workspace=workspace, role=15)
        assert galat_penugasan(divisi_a.id, [orang_luar.id], actor=orang_luar, abaikan_katup=True) is None
        assert galat_penugasan(divisi_a.id, [], actor=orang_luar, abaikan_katup=True) is None

    @pytest.mark.django_db
    def test_super_admin_boleh_di_divisi_mana_pun(
        self, workspace, instance_god_mode, super_admin, staf_a, divisi_a, jenjang
    ):
        """Super Admin mengurus sistem (B1), jadi ia di luar tangga divisi.

        Pertanyaan #7 di rancangan menanyakan apakah ini yang diinginkan user.
        """
        assert galat_penugasan(divisi_a.id, [staf_a.id], actor=super_admin, abaikan_katup=True) is None

    @pytest.mark.django_db
    def test_assign_diri_sendiri_oleh_MEMBER_menghasilkan_BUTUH_PERSETUJUAN(
        self, workspace, staf_a, divisi_a, jenjang
    ):
        """Inilah letak aturan user: "hanya bisa assign diri sendiri, dan harus di approve".

        Kewenangannya BOLEH (tidak ditolak), tapi statusnya menunggu persetujuan -- dan
        status itu keputusan KEDUA yang terpisah dari "boleh/tidak".
        """
        putusan = periksa_penugasan(divisi_a.id, [staf_a.id], actor=staf_a, abaikan_katup=True)
        assert putusan == BUTUH_PERSETUJUAN, f"dapat: {putusan!r}"

    @pytest.mark.django_db
    def test_assign_diri_sendiri_oleh_SUPERVISOR_tidak_butuh_persetujuan(
        self, workspace, bos_divisi_a, divisi_a, jenjang
    ):
        assert periksa_penugasan(divisi_a.id, [bos_divisi_a.id], actor=bos_divisi_a, abaikan_katup=True) is None

    @pytest.mark.django_db
    def test_tanpa_penyetuju_hasilnya_TANPA_ATASAN_bukan_gagal_senyap(
        self, workspace, staf_a, bos_divisi_a, direktur, divisi_a, jenjang
    ):
        """Kontrol negatif untuk rancangan §5.6: kalau tidak ada atasan, hasilnya BERLABEL.

        Tugasnya sendiri tetap BOLEH dibuat -- kalau ditolak, kekosongan data organisasi
        berubah jadi larangan bekerja. Yang tidak boleh adalah menggantung diam-diam.
        """
        JabatanOrganisasi.objects.filter(workspace=workspace, member=bos_divisi_a).delete()
        JabatanOrganisasi.objects.filter(workspace=workspace, member=direktur).delete()
        assert calon_penyetuju(workspace.id, divisi_a.id, tingkat_pembuat=TINGKAT_MEMBER) == []
        assert periksa_penugasan(divisi_a.id, [staf_a.id], actor=staf_a, abaikan_katup=True) == TANPA_ATASAN

    @pytest.mark.django_db
    def test_anggota_menugaskan_ORANG_LAIN_ditolak_bukan_menunggu(
        self, workspace, staf_a, staf_a2, divisi_a, jenjang
    ):
        """Beda yang mudah keliru: "orang lain" bukan "menunggu persetujuan".

        Menugaskan rekan TANPA menyertakan diri sendiri tidak diizinkan: staf hanya
        membuat tugasnya sendiri, rekan hanya boleh DITAMBAH di samping dirinya.
        """
        putusan = periksa_penugasan(divisi_a.id, [staf_a2.id], actor=staf_a, abaikan_katup=True)
        assert putusan not in (None, BUTUH_PERSETUJUAN, TANPA_ATASAN), f"dapat: {putusan!r}"

    @pytest.fixture
    def satu_departemen(self, workspace, staf_a, staf_a2, jenjang):
        from plane.db.models import Departemen, Divisi  # noqa: PLC0415

        divisi = Divisi.objects.create(workspace=workspace, kode="D1", nama="Divisi 1")
        dept = Departemen.objects.create(workspace=workspace, divisi=divisi, kode="DP1", nama="Dept 1")
        JabatanOrganisasi.objects.filter(workspace=workspace, member__in=[staf_a, staf_a2]).update(
            departemen=dept, divisi=divisi
        )
        return dept

    @pytest.mark.django_db
    def test_staf_boleh_ajak_rekan_setingkat_sedepartemen_dan_butuh_persetujuan(
        self, workspace, staf_a, staf_a2, divisi_a, satu_departemen
    ):
        ids = [staf_a.id, staf_a2.id]
        assert periksa_penugasan(divisi_a.id, ids, actor=staf_a, abaikan_katup=True) == BUTUH_PERSETUJUAN

    @pytest.mark.django_db
    def test_staf_tidak_boleh_melepas_dirinya_dari_tugasnya(
        self, workspace, staf_a, staf_a2, divisi_a, satu_departemen
    ):
        galat = galat_penugasan(divisi_a.id, [staf_a2.id], actor=staf_a, abaikan_katup=True)
        assert galat and "melepas dirinya" in galat

    @pytest.mark.django_db
    def test_staf_tidak_boleh_ajak_atasan_atau_beda_departemen(
        self, workspace, staf_a, bos_divisi_a, divisi_a, satu_departemen
    ):
        # atasan: bukan setingkat
        assert galat_penugasan(divisi_a.id, [staf_a.id, bos_divisi_a.id], actor=staf_a, abaikan_katup=True)
        # keluar departemen: lepas penempatan rekan
        orang_lain = _buat_user("stafx", workspace)
        JabatanOrganisasi.objects.create(workspace=workspace, member=orang_lain, tingkat=TINGKAT_MEMBER)
        ProjectMember.objects.create(project=divisi_a, member=orang_lain, workspace=workspace, role=15)
        assert galat_penugasan(divisi_a.id, [staf_a.id, orang_lain.id], actor=staf_a, abaikan_katup=True)

    @pytest.mark.django_db
    def test_supervisor_boleh_menugaskan_bawahan_tanpa_dirinya(
        self, workspace, bos_divisi_a, staf_a, divisi_a, jenjang
    ):
        assert galat_penugasan(divisi_a.id, [staf_a.id], actor=bos_divisi_a, abaikan_katup=True) is None


# --------------------------------------------------------------------------
# 5. Endpoint God Mode (baca-saja) + gerbang di jalur HTTP
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestEndpointHierarki:
    def _get(self, aktor):
        request = APIRequestFactory().get(URL_HIERARKI)
        if aktor is not None:
            force_authenticate(request, user=aktor)
        return InstanceHierarkiEndpoint.as_view()(request)

    @pytest.mark.django_db
    def test_super_admin_bisa_membaca(
        self, workspace, instance_god_mode, super_admin, jenjang
    ):
        response = self._get(super_admin)
        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        data = response.data
        assert data["workspace"]["slug"] == workspace.slug
        assert data["ringkasan"]["punya_jenjang"] >= 1
        assert data["flag_gerbang"] == FLAG_GERBANG
        emails = {b["email"] for b in data["anggota"]}
        assert super_admin.email in emails

    @pytest.mark.django_db
    def test_anggota_biasa_TIDAK_bisa_membaca(self, workspace, instance_god_mode, staf_a, jenjang):
        response = self._get(staf_a)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_tanpa_login_TIDAK_bisa_membaca(self, workspace, instance_god_mode, jenjang):
        response = self._get(None)
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    @pytest.mark.django_db
    def test_jenjang_yang_belum_diisi_terhitung_sebagai_belum_diisi(
        self, workspace, instance_god_mode, super_admin, staf_a, jenjang
    ):
        """Kontrol: staf_a memang sudah punya jenjang di fixture, jadi cari yang lain."""
        response = self._get(super_admin)
        data = response.data
        belum = [b for b in data["anggota"] if b["tingkat"] is None]
        assert all(b["tingkat_nama"] is None for b in belum)
        assert data["ringkasan"]["belum_diisi"] == len(belum)

    @pytest.mark.django_db
    def test_melaporkan_baris_role20_di_banyak_divisi(
        self, workspace, instance_god_mode, super_admin, bos_divisi_a, divisi_a, divisi_b, jenjang
    ):
        """5 akun role=20 di ~27 divisi adalah warisan yang HARUS terlihat.

        Kalau laporan ini hilang, orang berikutnya akan memakai `role = 20` sebagai
        proksi "atasan" dan mendapat 5 atasan palsu per divisi tanpa satu pun error.
        """
        lintas = _buat_user("lintas", workspace, peran_workspace=15)
        for i in range(5):
            p = _buat_project(f"Proyek {i}", f"PX{i}", workspace, lintas, anggota=[(lintas, 20)])
            assert p is not None

        response = self._get(super_admin)
        dilaporkan = {b["email"] for b in response.data["admin_lintas_divisi"]}
        assert lintas.email in dilaporkan
        # Kontrol negatif: admin divisi yang sah mengurus satu divisi saja TIDAK dilaporkan.
        assert bos_divisi_a.email not in dilaporkan

    @pytest.mark.django_db
    def test_super_admin_ikut_terlapor_karena_keanggotaan_otomatis(
        self, workspace, instance_god_mode, super_admin, divisi_a, divisi_b, jenjang
    ):
        """Temuan yang harus terlihat, bukan dianggap remeh.

        Signal `project_baru_untuk_super_admin` (`plane/db/superadmin.py`) membuat setiap
        Super Admin jadi Admin (role 20) di SETIAP project yang dibuat. Jadi kalau sebuah
        tes membuat >= 5 project, Super Admin otomatis muncul di daftar peringatan ini.
        Itu memang benar: di produksi 12 Super Admin x 31 project = 372 baris role 20.
        """
        for i in range(5):
            _buat_project(f"Proyek S{i}", f"PS{i}", workspace, super_admin)
        response = self._get(super_admin)
        dilaporkan = {b["email"] for b in response.data["admin_lintas_divisi"]}
        assert super_admin.email in dilaporkan


@pytest.mark.contract
class TestGerbangDiJalurHttp:
    @pytest.mark.django_db
    def test_dengan_katup_mati_penugasan_ke_orang_lain_tetap_jalan(
        self, workspace, staf_a, staf_a2, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        client = _klien(staf_a)
        response = client.post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas uji", "assignee_ids": [str(staf_a2.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)
        assert IssueAssignee.objects.filter(assignee_id=staf_a2.id).exists()

    @pytest.mark.django_db
    def test_dengan_katup_nyala_anggota_ditolak_menugaskan_orang_lain(
        self, workspace, staf_a, staf_a2, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        client = _klien(staf_a)
        response = client.post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas uji", "assignee_ids": [str(staf_a2.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, getattr(response, "data", None)
        assert "assignee_ids" in response.json()
        # Bukan cuma "ditolak": TOLAKANNYA HARUS KARENA KEBIJAKAN, bukan karena pelakunya
        # tidak terbaca. Tanpa asersi pesan ini, tes di atas akan hijau juga kalau gerbangnya
        # menolak SEMUA orang (termasuk dirinya sendiri) karena `actor`-nya None -- dan itu
        # persis kegagalan senyap yang membuat fitur ini berbahaya.
        pesan = " ".join(str(e) for e in response.json()["assignee_ids"])
        assert "diri sendiri" in pesan, pesan
        assert not IssueAssignee.objects.filter(assignee_id=staf_a2.id).exists()

    @pytest.mark.django_db
    def test_dengan_katup_nyala_anggota_masih_bisa_assign_dirinya_sendiri(
        self, workspace, staf_a, divisi_a, jenjang, monkeypatch
    ):
        """Kontrol negatif pasangannya: gerbangnya tidak boleh memblokir pekerjaan sendiri."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        client = _klien(staf_a)
        response = client.post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas sendiri", "assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)

    @pytest.mark.django_db
    def test_dengan_katup_nyala_supervisor_divisi_lain_ditolak(
        self, workspace, bos_divisi_a, staf_b, divisi_b, jenjang, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        client = _klien(bos_divisi_a)
        response = client.post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_b.id),
            {"name": "Tugas lintas", "assignee_ids": [str(staf_b.id)]},
            format="json",
        )
        # Jalur REST sudah menolak lebih dulu karena Bos A bukan anggota divisi B
        # (KEP-02). Kedua gerbang harus sepakat: hasilnya 400/403, bukan 201.
        assert response.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN), getattr(
            response, "data", None
        )

    @pytest.mark.django_db
    def test_dengan_katup_nyala_draft_menugaskan_orang_lain_DITOLAK(
        self, workspace, staf_a, staf_a2, divisi_a, jenjang, monkeypatch
    ):
        """Draft tidak boleh jadi jalur pintas (prinsip #1 Jebakan & Pelajaran)."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        client = _klien(staf_a)
        response = client.post(
            URL_DRAFTS.format(slug=workspace.slug),
            {"name": "Draft uji", "project_id": str(divisi_a.id), "assignee_ids": [str(staf_a2.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, getattr(response, "data", None)
        assert "assignee_ids" in response.json()

    @pytest.mark.django_db
    def test_dengan_katup_nyala_draft_assign_diri_sendiri_BOLEH(
        self, workspace, staf_a, divisi_a, jenjang, monkeypatch
    ):
        """Pasangannya: staf tetap bisa membuat draft untuk dirinya sendiri."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        client = _klien(staf_a)
        response = client.post(
            URL_DRAFTS.format(slug=workspace.slug),
            {"name": "Draft saya", "project_id": str(divisi_a.id), "assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)

    @pytest.mark.django_db
    def test_dengan_katup_mati_draft_bebas_seperti_semula(
        self, workspace, staf_a, staf_a2, divisi_a, jenjang, monkeypatch
    ):
        """Kontrak katup: dengan flag mati, draft tidak berubah perilaku."""
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        client = _klien(staf_a)
        response = client.post(
            URL_DRAFTS.format(slug=workspace.slug),
            {"name": "Draft bebas", "project_id": str(divisi_a.id), "assignee_ids": [str(staf_a2.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)

    @pytest.mark.django_db
    def test_template_apply_ke_orang_lain_tidak_jadi_pintas(
        self, workspace, staf_a, staf_a2, divisi_a, jenjang, monkeypatch
    ):
        """Staf menekan apply template ber-default orang lain: tugas lahir TANPA assignee."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        template = IssueTemplate.objects.create(
            workspace=workspace,
            project=divisi_a,
            name="Template uji",
            title="Tugas dari template",
            default_assignee=staf_a2,
        )
        client = _klien(staf_a)
        response = client.post(
            URL_TEMPLATE_APPLY.format(slug=workspace.slug, project_id=divisi_a.id, template_id=template.id),
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)
        issue = Issue.objects.get(pk=response.json()["id"])
        assert not IssueAssignee.objects.filter(issue=issue).exists()

    @pytest.mark.django_db
    def test_template_apply_default_diri_sendiri_tetap_jalan(
        self, workspace, staf_a, divisi_a, jenjang, monkeypatch
    ):
        """Pasangannya: default = dirinya sendiri tetap terpasang + antrean lahir."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        template = IssueTemplate.objects.create(
            workspace=workspace,
            project=divisi_a,
            name="Template diri",
            title="Tugas saya dari template",
            default_assignee=staf_a,
        )
        client = _klien(staf_a)
        response = client.post(
            URL_TEMPLATE_APPLY.format(slug=workspace.slug, project_id=divisi_a.id, template_id=template.id),
            {},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)
        issue = Issue.objects.get(pk=response.json()["id"])
        assert IssueAssignee.objects.filter(issue=issue, assignee=staf_a).exists()
        assert PersetujuanPenugasan.objects.filter(issue=issue, status="menunggu").exists()

    @pytest.mark.django_db
    def test_staf_create_tanpa_assignee_otomatis_jadi_miliknya(
        self, workspace, staf_a, divisi_a, jenjang, monkeypatch
    ):
        """Keputusan user: create langsung auto-assign diri sendiri + antrean lahir."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        client = _klien(staf_a)
        response = client.post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas tanpa assignee"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)
        issue = Issue.objects.get(pk=response.json()["id"])
        assert set(issue.issue_assignee.values_list("assignee_id", flat=True)) == {staf_a.id}
        assert PersetujuanPenugasan.objects.filter(issue=issue, status="menunggu").exists()

    @pytest.mark.django_db
    def test_staf_tidak_bisa_mengubah_assignee_miliknya_sendiri(
        self, workspace, staf_a, staf_a2, divisi_a, jenjang, monkeypatch
    ):
        """Keputusan user: sesudah create, staf tidak bisa ganti assignee."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        client = _klien(staf_a)
        issue_id = client.post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        ).json()["id"]
        response = client.patch(
            URL_ISSUE_DETAIL.format(slug=workspace.slug, project_id=divisi_a.id, issue_id=issue_id),
            {"assignee_ids": [str(staf_a2.id)]},
            format="json",
        )
        # View gate menolak duluan (403) sebelum serializer (400): keduanya
        # penolakan, dan assignee tetap tidak berubah (asersi di bawah).
        assert response.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN), getattr(
            response, "data", None
        )
        assert set(
            Issue.objects.get(pk=issue_id).issue_assignee.values_list("assignee_id", flat=True)
        ) == {staf_a.id}

    @pytest.mark.django_db
    def test_staf_tidak_bisa_mengubah_tugas_orang_lain(
        self, workspace, staf_a, staf_a2, divisi_a, jenjang, monkeypatch
    ):
        """Keputusan user: member tidak bisa edit work item yang bukan miliknya."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        milik_a2 = Issue.objects.create(
            workspace=workspace, project=divisi_a, name="Tugas A2", created_by=staf_a2
        )
        IssueAssignee.objects.create(
            issue=milik_a2, assignee=staf_a2, project=divisi_a, workspace=workspace
        )
        response = _klien(staf_a).patch(
            URL_ISSUE_DETAIL.format(slug=workspace.slug, project_id=divisi_a.id, issue_id=milik_a2.id),
            {"priority": "urgent"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, getattr(response, "data", None)

    @pytest.mark.django_db
    def test_staf_bisa_mengubah_tugas_miliknya_sendiri(
        self, workspace, staf_a, divisi_a, jenjang, monkeypatch
    ):
        """Pasangannya: tugas sendiri tetap bisa diedit (kecuali assignee) SESUDAH disetujui."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        client = _klien(staf_a)
        issue_id = client.post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        ).json()["id"]
        # Menunggu = boleh diubah (gerbangnya di selesai); di sini yang diuji kepemilikannya.
        PersetujuanPenugasan.objects.filter(issue_id=issue_id).update(status="disetujui")
        response = client.patch(
            URL_ISSUE_DETAIL.format(slug=workspace.slug, project_id=divisi_a.id, issue_id=issue_id),
            {"priority": "urgent"},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT, getattr(response, "data", None)

    @pytest.mark.django_db
    def test_atasan_bisa_mengubah_tugas_bawahannya(
        self, workspace, bos_divisi_a, staf_a, divisi_a, jenjang, monkeypatch
    ):
        """Keputusan user: atasan bisa mengubah (termasuk re-assign) tugas bawahan."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        milik_staf = Issue.objects.create(
            workspace=workspace, project=divisi_a, name="Tugas staf", created_by=staf_a
        )
        IssueAssignee.objects.create(
            issue=milik_staf, assignee=staf_a, project=divisi_a, workspace=workspace
        )
        response = _klien(bos_divisi_a).patch(
            URL_ISSUE_DETAIL.format(slug=workspace.slug, project_id=divisi_a.id, issue_id=milik_staf.id),
            {"priority": "urgent"},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT, getattr(response, "data", None)
# --------------------------------------------------------------------------
# 6. Antrean persetujuan (keputusan user 2026-10-15)
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestPersetujuanPenugasan:
    """Tugasnya TETAP muncul (tidak dipindah ke Triage), tapi berindikator.

    Keputusan user: "tugas (Draft) jadi muncul tapi belum di approve dan ada indikator".
    """

    @pytest.mark.django_db
    def test_member_assign_diri_sendiri_membuat_baris_menunggu_DAN_tugasnya_tetap_muncul(
        self, workspace, staf_a, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        client = _klien(staf_a)
        response = client.post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)

        baris = PersetujuanPenugasan.objects.get(pemohon=staf_a)
        assert baris.status == "menunggu"
        assert baris.issue_id is not None

        # Ini asersi yang menjaga keputusan "tetap muncul": tugasnya harus terlihat dari
        # `issue_objects`, yaitu daftar yang dipakai papan & daftar work item. Kalau kelak
        # ada yang memindahkannya ke state Triage supaya "tersembunyi", asersi ini merah.
        assert Issue.issue_objects.filter(pk=baris.issue_id).exists()

    @pytest.mark.django_db
    def test_katup_mati_TIDAK_membuat_baris_apa_pun(
        self, workspace, staf_a, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        client = _klien(staf_a)
        response = client.post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)
        assert PersetujuanPenugasan.objects.count() == 0

    @pytest.mark.django_db
    def test_supervisor_assign_diri_sendiri_TIDAK_butuh_persetujuan(
        self, workspace, bos_divisi_a, divisi_a, jenjang, monkeypatch
    ):
        """Keputusan user: "khusus yang jabatan member saja"."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        client = _klien(bos_divisi_a)
        response = client.post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas supervisor", "assignee_ids": [str(bos_divisi_a.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)
        assert PersetujuanPenugasan.objects.count() == 0

    @pytest.mark.django_db
    def test_supervisor_menugaskan_member_TIDAK_butuh_persetujuan(
        self, workspace, bos_divisi_a, staf_a, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        client = _klien(bos_divisi_a)
        response = client.post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas untuk staf", "assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)
        assert PersetujuanPenugasan.objects.count() == 0

    @pytest.mark.django_db
    def test_supervisor_TIDAK_boleh_menugaskan_ke_ATASANNYA(
        self, workspace, bos_divisi_a, direktur, divisi_a, jenjang, monkeypatch
    ):
        """\"manager it bawahi supervisor dan member it\" -- arahnya hanya KE BAWAH.

        Direktur bukan anggota... dalam tes ini ia anggota; yang diuji tingkatnya.
        """
        monkeypatch.setenv(FLAG_GERBANG, "1")
        # Signal direktur (`plane/db/direktur.py`) sudah menjadikannya anggota; create()
        # telanjang di sini menabrak unik ProjectUserProperty.
        from plane.db.membership import jadikan_anggota_project

        jadikan_anggota_project(divisi_a.id, direktur.id, 20, workspace_id=workspace.id)
        client = _klien(bos_divisi_a)
        response = client.post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas ke direktur", "assignee_ids": [str(direktur.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, getattr(response, "data", None)

    @pytest.mark.django_db
    def test_pemohon_TIDAK_bisa_menyetujui_tugasnya_sendiri(
        self, workspace, staf_a, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _klien(staf_a).post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        baris = PersetujuanPenugasan.objects.get(pemohon=staf_a)

        response = _klien(staf_a).post(
            URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id) + f"{baris.id}/",
            {"aksi": "setujui"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_rekan_sesama_member_TIDAK_bisa_menyetujui(
        self, workspace, staf_a, staf_a2, divisi_a, jenjang, monkeypatch
    ):
        """Kontrol negatif: yang menyetujui harus ATASAN, bukan rekan setingkat."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _klien(staf_a).post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        baris = PersetujuanPenugasan.objects.get(pemohon=staf_a)

        response = _klien(staf_a2).post(
            URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id) + f"{baris.id}/",
            {"aksi": "setujui"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_atasan_di_divisinya_bisa_menyetujui(
        self, workspace, staf_a, bos_divisi_a, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _klien(staf_a).post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        baris = PersetujuanPenugasan.objects.get(pemohon=staf_a)

        response = _klien(bos_divisi_a).post(
            URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id) + f"{baris.id}/",
            {"aksi": "setujui"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        baris.refresh_from_db()
        assert baris.status == "disetujui"
        assert baris.diputuskan_oleh_id == bos_divisi_a.id
        assert baris.diputuskan_pada is not None

    @pytest.mark.django_db
    def test_penolakan_wajib_beralasan_dan_tugasnya_TIDAK_dihapus(
        self, workspace, staf_a, bos_divisi_a, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _klien(staf_a).post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        baris = PersetujuanPenugasan.objects.get(pemohon=staf_a)
        url = URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id) + f"{baris.id}/"

        kosong = _klien(bos_divisi_a).post(url, {"aksi": "tolak"}, format="json")
        assert kosong.status_code == status.HTTP_400_BAD_REQUEST

        ada_alasan = _klien(bos_divisi_a).post(
            url, {"aksi": "tolak", "alasan": "Belum ada nomor PO"}, format="json"
        )
        assert ada_alasan.status_code == status.HTTP_200_OK, getattr(ada_alasan, "data", None)
        baris.refresh_from_db()
        assert baris.status == "ditolak"
        assert baris.alasan == "Belum ada nomor PO"
        # Tugasnya tetap ada: menghapusnya berarti pekerjaan yang sudah dimulai lenyap.
        assert Issue.objects.filter(pk=baris.issue_id).exists()

    @pytest.mark.django_db
    def test_satu_tugas_hanya_boleh_punya_SATU_permintaan_menunggu(
        self, workspace, staf_a, divisi_a, jenjang, monkeypatch
    ):
        """Kalau tidak dijaga, dua baris menunggu membuat penyetuju menekan yang salah."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        client = _klien(staf_a)
        respons = client.post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        issue_id = respons.json()["id"]

        # Menyimpan ulang tugas yang sama tidak boleh menambah baris menunggu.
        # Staf tetap tidak boleh menyentuh assignee (aturan PINDAH, bukan kunci).
        lagi = client.patch(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id) + f"{issue_id}/",
            {"assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        assert lagi.status_code == status.HTTP_400_BAD_REQUEST, getattr(lagi, "data", None)
        assert PersetujuanPenugasan.objects.filter(issue_id=issue_id, status="menunggu").count() == 1

    @pytest.mark.django_db
    def test_antrean_menyebut_siapa_yang_boleh_memutuskan(
        self, workspace, staf_a, bos_divisi_a, direktur, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _klien(staf_a).post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        )

        sebagai_atasan = _klien(bos_divisi_a).get(
            URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id)
        )
        assert sebagai_atasan.status_code == status.HTTP_200_OK, getattr(sebagai_atasan, "data", None)
        baris = sebagai_atasan.json()["hasil"][0]
        assert baris["boleh_saya_putuskan"] is True
        assert baris["status"] == "menunggu"
        penyetuju = {p["id"] for p in baris["penyetuju_di_divisi"]}
        assert str(bos_divisi_a.id) in penyetuju
        assert str(direktur.id) in penyetuju
        assert str(staf_a.id) not in penyetuju, "pemohon bukan penyetujunya sendiri"

        sebagai_pemohon = _klien(staf_a).get(
            URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id) + "?peran=pemohon"
        )
        assert sebagai_pemohon.json()["hasil"][0]["peran_saya"] == "pemohon"
        assert sebagai_pemohon.json()["hasil"][0]["boleh_saya_putuskan"] is False


# --------------------------------------------------------------------------
# 7. Menulis jenjang dari God Mode (satu-satunya jalan mengisi hierarki)
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestTulisHierarki:
    def _post(self, aktor, data):
        request = APIRequestFactory().post(URL_HIERARKI, data, format="json")
        if aktor is not None:
            force_authenticate(request, user=aktor)
        return InstanceHierarkiEndpoint.as_view()(request)

    def _get(self, aktor):
        request = APIRequestFactory().get(URL_HIERARKI)
        force_authenticate(request, user=aktor)
        return InstanceHierarkiEndpoint.as_view()(request)

    @pytest.mark.django_db
    def test_super_admin_bisa_menyetel_jenjang(self, workspace, instance_god_mode, super_admin, staf_a):
        assert tingkat_anggota(staf_a.id, workspace.id) is None
        response = self._post(super_admin, {"member_id": str(staf_a.id), "tingkat": 20})
        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        assert response.data["member"]["tingkat"] == 20
        assert response.data["member"]["tingkat_nama"] == "Supervisor"
        assert tingkat_anggota(staf_a.id, workspace.id) == 20

    @pytest.mark.django_db
    def test_anggota_biasa_TIDAK_bisa_menulis(self, workspace, instance_god_mode, staf_a, staf_a2):
        response = self._post(staf_a2, {"member_id": str(staf_a.id), "tingkat": 40})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert tingkat_anggota(staf_a.id, workspace.id) is None, "tidak boleh ada yang tertulis"

    @pytest.mark.django_db
    def test_tanpa_login_TIDAK_bisa_menulis(self, workspace, instance_god_mode, staf_a):
        response = self._post(None, {"member_id": str(staf_a.id), "tingkat": 40})
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        assert tingkat_anggota(staf_a.id, workspace.id) is None

    @pytest.mark.django_db
    def test_angka_ROLE_project_ditolak_bukan_dibulatkan(self, workspace, instance_god_mode, super_admin, staf_a):
        """Kontrol negatif yang menjaga dua sumbu angka tidak tertukar.

        15 dikirim dengan maksud \"Member\" (seperti di ProjectMember) akan tersimpan
        sebagai Supervisor dan memberi kewenangan yang tidak diminta -- tanpa error.
        """
        response = self._post(super_admin, {"member_id": str(staf_a.id), "tingkat": 15})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "ROLE project" in response.data["error"]
        assert tingkat_anggota(staf_a.id, workspace.id) is None

    @pytest.mark.django_db
    def test_tingkat_tidak_dikenal_ditolak(self, workspace, instance_god_mode, super_admin, staf_a):
        response = self._post(super_admin, {"member_id": str(staf_a.id), "tingkat": 99})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_jenjang_dicabut_dan_bisa_dipasang_lagi(self, workspace, instance_god_mode, super_admin, staf_a):
        """Kontrak jebakan A21: pencabutan tidak boleh mengunci pemasangan berikutnya."""
        assert self._post(super_admin, {"member_id": str(staf_a.id), "tingkat": 30}).status_code == 200
        assert tingkat_anggota(staf_a.id, workspace.id) == 30

        assert self._post(super_admin, {"member_id": str(staf_a.id), "tingkat": None}).status_code == 200
        assert tingkat_anggota(staf_a.id, workspace.id) is None, "null harus berarti 'belum diisi'"

        assert self._post(super_admin, {"member_id": str(staf_a.id), "tingkat": 10}).status_code == 200
        assert tingkat_anggota(staf_a.id, workspace.id) == 10
        # Dan hanya ada SATU baris aktif, bukan dua.
        assert (
            JabatanOrganisasi.all_objects.filter(workspace=workspace, member=staf_a, deleted_at__isnull=True).count()
            == 1
        )

    @pytest.mark.django_db
    def test_pengawasan_diganti_utuh_bukan_ditambah(
        self, workspace, instance_god_mode, super_admin, staf_a, divisi_a, divisi_b
    ):
        respons = self._post(
            super_admin,
            {"member_id": str(staf_a.id), "tingkat": 30, "pengawasan": [str(divisi_a.id), str(divisi_b.id)]},
        )
        assert respons.status_code == status.HTTP_200_OK, getattr(respons, "data", None)
        assert len(respons.data["member"]["pengawasan"]) == 2

        # Kirim satu saja -> yang lain HARUS lepas. "Tidak dikirim" != "dikirim kosong".
        respons = self._post(super_admin, {"member_id": str(staf_a.id), "pengawasan": [str(divisi_a.id)]})
        assert len(respons.data["member"]["pengawasan"]) == 1
        assert PengawasanDivisi.objects.filter(workspace=workspace, member=staf_a).count() == 1

        respons = self._post(super_admin, {"member_id": str(staf_a.id), "pengawasan": []})
        assert respons.data["member"]["pengawasan"] == []
        assert PengawasanDivisi.objects.filter(workspace=workspace, member=staf_a).count() == 0

    @pytest.mark.django_db
    def test_project_asing_ditolak_dan_TIDAK_menulis_apa_pun(
        self, workspace, instance_god_mode, super_admin, staf_a, divisi_a
    ):
        """Gagal-tertutup: id asing lebih mungkin salah kirim daripada niat."""
        asing = str(uuid4())
        respons = self._post(
            super_admin,
            {"member_id": str(staf_a.id), "tingkat": 20, "pengawasan": [asing]},
        )
        assert respons.status_code == status.HTTP_400_BAD_REQUEST
        assert "tidak dikenal" in respons.data["error"]
        # Validasi di depan: jenjangnya pun tidak ikut tersimpan.
        assert tingkat_anggota(staf_a.id, workspace.id) is None
        assert PengawasanDivisi.objects.filter(workspace=workspace, member=staf_a).count() == 0

    @pytest.mark.django_db
    def test_perubahan_jenjang_masuk_jejak_audit(self, workspace, instance_god_mode, super_admin, staf_a):
        """Perubahan jenjang = perubahan hak akses, jadi wajib bisa ditelusuri.

        Catatan yang mudah salah: `LogEntry` punya DUA kolom id -- `object_id`
        (`BigIntegerField`, untuk primary key angka) dan `object_pk` (`CharField`, untuk
        primary key UUID seperti seluruh model Plane). Jadi yang dicari adalah
        `object_pk`; menyaring dengan `object_id` melempar ValueError, bukan mengembalikan
        kosong. Pemeriksa jejak audit di God Mode sudah membaca `object_pk`.
        """
        from auditlog.models import LogEntry

        self._post(super_admin, {"member_id": str(staf_a.id), "tingkat": 40})
        entri = LogEntry.objects.filter(
            content_type__model="jabatanorganisasi",
            object_pk=str(JabatanOrganisasi.objects.get(member=staf_a).id),
        )
        assert entri.exists(), "perubahan jenjang tidak tercatat di audit log"
        assert entri.first().actor_id == super_admin.id, "pelakunya harus tercatat, bukan kosong"

    @pytest.mark.django_db
    def test_anggota_belum_diisi_terlihat_di_daftar(
        self, workspace, instance_god_mode, super_admin, staf_a, staf_a2, jenjang
    ):
        """Halaman God Mode butuh daftar ini untuk tahu siapa yang masih kosong."""
        response = self._get(super_admin)
        baris = {b["email"]: b for b in response.data["anggota"]}
        assert baris[staf_a.email]["tingkat"] == TINGKAT_MEMBER
        assert baris[super_admin.email]["tingkat"] is None
        assert response.data["ringkasan"]["belum_diisi"] >= 1


@pytest.mark.contract
class TestAntreanPerTugas:
    @pytest.mark.django_db
    def test_filter_tugas_mengembalikan_satu_baris_saja(
        self, workspace, staf_a, bos_divisi_a, divisi_a, jenjang, monkeypatch
    ):
        """Indikator di sidebar work item memakai filter ini; tanpa ini ia harus
        mengunduh seluruh antrean project untuk menjawab satu tugas."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        respons = _klien(staf_a).post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        issue_id = respons.json()["id"]

        dasar = URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id)
        satu = _klien(bos_divisi_a).get(f"{dasar}?tugas={issue_id}")
        assert satu.status_code == status.HTTP_200_OK, getattr(satu, "data", None)
        assert satu.json()["jumlah"] == 1
        assert satu.json()["hasil"][0]["tugas"]["id"] == issue_id
        assert satu.json()["hasil"][0]["tugas"]["nomor"].startswith("DIVA-")

        kosong = _klien(bos_divisi_a).get(f"{dasar}?tugas={uuid4()}")
        assert kosong.json()["jumlah"] == 0


@pytest.mark.contract
class TestBawahanIds:
    """Regresi bug 2026-10-16: dropdown atasan isinya hanya diri sendiri.

    `_bawahan_ids` memeriksa "divisi yang DIAWASI bawahan" — member tidak
    mengawasi apa pun, jadi member tidak pernah muncul sebagai bawahan.
    Syarat yang benar: bawahan = tingkat lebih rendah + ANGGOTA divisi itu,
    dan divisinya diawasi actor.
    """

    @pytest.mark.django_db
    def test_supervisor_melihat_member_divisinya(
        self, workspace, instance_god_mode, divisi_a, bos_divisi_a, staf_a, staf_a2, jenjang
    ):
        bawahan = _bawahan_ids(bos_divisi_a.id, workspace.id, divisi_a.id)
        assert str(staf_a.id) in {str(u) for u in bawahan}
        assert str(staf_a2.id) in {str(u) for u in bawahan}
        assert str(bos_divisi_a.id) not in {str(u) for u in bawahan}

    @pytest.mark.django_db
    def test_bawahan_harus_anggota_divisi_itu(
        self, workspace, instance_god_mode, divisi_a, divisi_b, bos_divisi_a, staf_b, jenjang
    ):
        """staf_b (member divisi B) bukan bawahan bos A di divisi A."""
        bawahan = _bawahan_ids(bos_divisi_a.id, workspace.id, divisi_a.id)
        assert str(staf_b.id) not in {str(u) for u in bawahan}

    @pytest.mark.django_db
    def test_setingkat_bukan_bawahan(
        self, workspace, instance_god_mode, divisi_a, bos_divisi_a, bos_divisi_b, jenjang
    ):
        """Supervisor lain bukan bawahan, walau satu divisi."""
        from plane.db.models import ProjectMember

        ProjectMember.objects.create(
            project=divisi_a, member=bos_divisi_b, workspace=workspace, role=15
        )
        bawahan = _bawahan_ids(bos_divisi_a.id, workspace.id, divisi_a.id)
        assert str(bos_divisi_b.id) not in {str(u) for u in bawahan}

    @pytest.mark.django_db
    def test_member_bukan_pemberi_bawahan(
        self, workspace, instance_god_mode, divisi_a, staf_a, staf_a2, jenjang
    ):
        assert _bawahan_ids(staf_a.id, workspace.id, divisi_a.id) == set()

    @pytest.mark.django_db
    def test_string_uuid_dari_url_tetap_cocok(
        self, workspace, instance_god_mode, divisi_a, bos_divisi_a, staf_a, jenjang
    ):
        """Kwargs URL membawa UUID sebagai string; tanpa normalisasi, `in`
        selalu gagal dan endpoint selalu mengembalikan bawahan kosong."""
        bawahan = _bawahan_ids(bos_divisi_a.id, workspace.id, str(divisi_a.id))
        assert str(staf_a.id) in {str(u) for u in bawahan}

    @pytest.mark.django_db
    def test_endpoint_bawahan_memuat_member(
        self, workspace, instance_god_mode, divisi_a, bos_divisi_a, staf_a, jenjang, monkeypatch
    ):
        """Ujung ke ujung: GET bisa-ditugaskan untuk supervisor berisi member."""
        from plane.app.views.issue.persetujuan import PenggunaBisaDitugaskanEndpoint

        monkeypatch.setenv(FLAG_GERBANG, "1")
        request = APIRequestFactory().get(
            f"/api/workspaces/{workspace.slug}/projects/{divisi_a.id}/persetujuan-penugasan/bisa-ditugaskan/"
        )
        force_authenticate(request, user=bos_divisi_a)
        response = PenggunaBisaDitugaskanEndpoint.as_view()(request, slug=workspace.slug, project_id=divisi_a.id)
        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        assert response.data["mode"] == "bawahan"
        ids = {b["id"] for b in response.data["users"]}
        assert str(staf_a.id) in ids
        assert str(bos_divisi_a.id) in ids

    @pytest.mark.django_db
    def test_anggota_tanpa_jenjang_tetap_bawahan(
        self, workspace, instance_god_mode, divisi_a, bos_divisi_a, staf_a, jenjang
    ):
        """Regresi 2026-10-16: staf yang jenjangnya BELUM DIISI tetap muncul
        sebagai bawahan. Gerbang mengizinkan atasan menugaskan ke mereka (hanya
        menolak yang JELAS setingkat/lebih tinggi), jadi dropdown yang
        menyembunyikannya berbohong tentang apa yang server izinkan."""
        from plane.db.models import JabatanOrganisasi

        JabatanOrganisasi.objects.filter(workspace=workspace, member=staf_a).delete()
        bawahan = _bawahan_ids(bos_divisi_a.id, workspace.id, divisi_a.id)
        assert str(staf_a.id) in {str(u) for u in bawahan}

    @pytest.mark.django_db
    def test_atasan_tanpa_jenjang_tidak_punya_bawahan(
        self, workspace, instance_god_mode, divisi_a, bos_divisi_a, staf_a, jenjang
    ):
        """Kontrol negatif: actor yang jenjangnya belum diisi tetap bukan
        pemberi-bawahan, walau ia anggota divisi itu."""
        from plane.db.models import JabatanOrganisasi

        JabatanOrganisasi.objects.filter(workspace=workspace, member=bos_divisi_a).delete()
        assert _bawahan_ids(bos_divisi_a.id, workspace.id, divisi_a.id) == set()


@pytest.mark.contract
class TestTolakKembaliKeDraft:
    """Keputusan user 2026-10-16 (menggantikan 2026-10-15): tugas yang DITOLAK
    kembali ke draft tak-terlihat (`is_draft=True`), bukan tetap di papan.
    Staf mengajukan ulang dari tab "Pengajuan saya"."""

    @pytest.mark.django_db
    def test_tolak_menyembunyikan_tugas_dari_papan(
        self, workspace, staf_a, bos_divisi_a, divisi_a, jenjang, monkeypatch
    ):
        from plane.db.models import Issue

        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id = _klien(staf_a).post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        ).json()["id"]
        baris = PersetujuanPenugasan.objects.get(pemohon=staf_a)

        tolak = _klien(bos_divisi_a).post(
            URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id) + f"{baris.id}/",
            {"aksi": "tolak", "alasan": "Belum jelas ruang lingkupnya"},
            format="json",
        )
        assert tolak.status_code == status.HTTP_200_OK, getattr(tolak, "data", None)
        assert tolak.json()["status"] == "ditolak"
        assert Issue.objects.filter(pk=issue_id).first().is_draft is True
        # Assignee tidak dicabut: jejak + pengajuan-ulang tanpa menebak.
        assert IssueAssignee.objects.filter(issue_id=issue_id, assignee=staf_a).exists()

    @pytest.mark.django_db
    def test_setuju_tidak_menyembunyikan(
        self, workspace, staf_a, bos_divisi_a, divisi_a, jenjang, monkeypatch
    ):
        from plane.db.models import Issue

        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id = _klien(staf_a).post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        ).json()["id"]
        baris = PersetujuanPenugasan.objects.get(pemohon=staf_a)

        setuju = _klien(bos_divisi_a).post(
            URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id) + f"{baris.id}/",
            {"aksi": "setujui"},
            format="json",
        )
        assert setuju.status_code == status.HTTP_200_OK
        assert Issue.objects.filter(pk=issue_id).first().is_draft is False

    @pytest.mark.django_db
    def test_pemohon_bisa_ajukan_ulang_yang_ditolak(
        self, workspace, staf_a, bos_divisi_a, divisi_a, jenjang, monkeypatch
    ):
        from plane.db.models import Issue

        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id = _klien(staf_a).post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        ).json()["id"]
        baris = PersetujuanPenugasan.objects.get(pemohon=staf_a)
        _klien(bos_divisi_a).post(
            URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id) + f"{baris.id}/",
            {"aksi": "tolak", "alasan": "Perbaiki dulu"},
            format="json",
        )

        ulang = _klien(staf_a).post(
            URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id) + f"{baris.id}/",
            {"aksi": "ajukan-ulang"},
            format="json",
        )
        assert ulang.status_code == status.HTTP_200_OK, getattr(ulang, "data", None)
        assert ulang.json()["status"] == "menunggu"
        assert Issue.objects.filter(pk=issue_id).first().is_draft is False
        # Riwayat utuh: baris lama tetap ditolak, baris baru menunggu.
        assert PersetujuanPenugasan.objects.filter(issue_id=issue_id).count() == 2

    @pytest.mark.django_db
    def test_orang_lain_TIDAK_bisa_ajukan_ulang(
        self, workspace, staf_a, staf_a2, bos_divisi_a, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _klien(staf_a).post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        baris = PersetujuanPenugasan.objects.get(pemohon=staf_a)
        _klien(bos_divisi_a).post(
            URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id) + f"{baris.id}/",
            {"aksi": "tolak", "alasan": "Perbaiki dulu"},
            format="json",
        )

        ulang = _klien(staf_a2).post(
            URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id) + f"{baris.id}/",
            {"aksi": "ajukan-ulang"},
            format="json",
        )
        assert ulang.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_yang_menunggu_TIDAK_bisa_diajukan_ulang(
        self, workspace, staf_a, bos_divisi_a, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _klien(staf_a).post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        baris = PersetujuanPenugasan.objects.get(pemohon=staf_a)

        ulang = _klien(staf_a).post(
            URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id) + f"{baris.id}/",
            {"aksi": "ajukan-ulang"},
            format="json",
        )
        assert ulang.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_tolak_tanpa_alasan_tetap_ditolak(
        self, workspace, staf_a, bos_divisi_a, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _klien(staf_a).post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        baris = PersetujuanPenugasan.objects.get(pemohon=staf_a)

        tolak = _klien(bos_divisi_a).post(
            URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id) + f"{baris.id}/",
            {"aksi": "tolak"},
            format="json",
        )
        assert tolak.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.contract
class TestHapusTugasHierarki:
    """Hapus = aturan ubah: pemilik/assignee atau atasannya. Admin project saja TIDAK cukup."""

    def _tugas_milik_a2(self, workspace, divisi_a, staf_a2):
        tugas = Issue.objects.create(workspace=workspace, project=divisi_a, name="Tugas A2", created_by=staf_a2)
        IssueAssignee.objects.create(issue=tugas, assignee=staf_a2, project=divisi_a, workspace=workspace)
        return tugas

    @pytest.mark.django_db
    def test_staf_berperan_admin_project_TIDAK_bisa_hapus_tugas_orang_lain(
        self, workspace, staf_a, staf_a2, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        ProjectMember.objects.filter(project=divisi_a, member=staf_a).update(role=20)
        tugas = self._tugas_milik_a2(workspace, divisi_a, staf_a2)
        response = _klien(staf_a).delete(
            URL_ISSUE_DETAIL.format(slug=workspace.slug, project_id=divisi_a.id, issue_id=tugas.id)
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, getattr(response, "data", None)
        assert Issue.objects.filter(pk=tugas.id).exists()

    @pytest.mark.django_db
    def test_atasan_bisa_hapus_tugas_bawahan(
        self, workspace, bos_divisi_a, staf_a2, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        tugas = self._tugas_milik_a2(workspace, divisi_a, staf_a2)
        response = _klien(bos_divisi_a).delete(
            URL_ISSUE_DETAIL.format(slug=workspace.slug, project_id=divisi_a.id, issue_id=tugas.id)
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT, getattr(response, "data", None)
        assert not Issue.objects.filter(pk=tugas.id).exists()


URL_KOMENTAR = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/comments/"
URL_TAUTAN = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/issue-links/"


@pytest.mark.contract
class TestPersetujuanSaatSelesai:
    """Keputusan user 2026-10-24: persetujuan hanya di gerbang SELESAI.

    Sebelum disetujui tugas tetap bebas dipindah/diubah/dihapus/diarsipkan.
    Yang diblokir hanyalah MASUK status selesai tanpa baris disetujui.
    Tugas atasan tidak pernah butuh persetujuan.
    """

    def _ajukan(self, workspace, divisi_a, staf_a):
        response = _klien(staf_a).post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        issue_id = response.json()["id"]
        return issue_id, PersetujuanPenugasan.objects.get(issue_id=issue_id, status="menunggu")

    def _detail(self, workspace, divisi_a, issue_id):
        return URL_ISSUE_DETAIL.format(slug=workspace.slug, project_id=divisi_a.id, issue_id=issue_id)

    def _state(self, workspace, divisi_a, grup):
        """Satu state tiap grup yang diminta (mulai/ Selesai)."""
        from plane.db.models import DEFAULT_STATES, State

        siap = {}
        for s in DEFAULT_STATES:
            st, _ = State.objects.get_or_create(
                project=divisi_a,
                workspace=workspace,
                name=s["name"],
                defaults={
                    "color": s["color"],
                    "sequence": s["sequence"],
                    "group": s["group"],
                    "default": s.get("default", False),
                },
            )
            siap.setdefault(st.group, st)
        return siap["started"], siap["completed"]

    @pytest.mark.django_db
    def test_respons_create_langsung_berstatus_menunggu(self, workspace, staf_a, divisi_a, jenjang, monkeypatch):
        """Badge "menunggu persetujuan" harus muncul tanpa refresh: dibaca dari respons create."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        response = _klien(staf_a).post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas saya", "assignee_ids": [str(staf_a.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)
        assert response.json().get("approval_status") == "menunggu"

    @pytest.mark.django_db
    def test_staf_bisa_mengubah_tugas_yang_menunggu(self, workspace, staf_a, divisi_a, jenjang, monkeypatch):
        """Keputusan 2026-10-24: menunggu bukan kunci. Edit bebas, gerbangnya di selesai."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id, _ = self._ajukan(workspace, divisi_a, staf_a)
        response = _klien(staf_a).patch(
            self._detail(workspace, divisi_a, issue_id), {"priority": "urgent"}, format="json"
        )
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(
            response, "data", None
        )
        assert Issue.objects.get(pk=issue_id).priority == "urgent"

    @pytest.mark.django_db
    def test_atasan_bisa_menyunting_yang_menunggu(
        self, workspace, staf_a, bos_divisi_a, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id, _ = self._ajukan(workspace, divisi_a, staf_a)
        response = _klien(bos_divisi_a).patch(
            self._detail(workspace, divisi_a, issue_id), {"priority": "urgent"}, format="json"
        )
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(
            response, "data", None
        )

    @pytest.mark.django_db
    def test_yang_menunggu_bisa_dihapus(self, workspace, staf_a, divisi_a, jenjang, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id, _ = self._ajukan(workspace, divisi_a, staf_a)
        response = _klien(staf_a).delete(self._detail(workspace, divisi_a, issue_id))
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(
            response, "data", None
        )
        assert not Issue.objects.filter(pk=issue_id, deleted_at__isnull=True).exists()

    @pytest.mark.django_db
    def test_bisa_pindah_status_belum_selesai(self, workspace, staf_a, divisi_a, jenjang, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id, _ = self._ajukan(workspace, divisi_a, staf_a)
        mulai, _ = self._state(workspace, divisi_a)
        response = _klien(staf_a).patch(
            self._detail(workspace, divisi_a, issue_id), {"state": str(mulai.id)}, format="json"
        )
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(
            response, "data", None
        )

    @pytest.mark.django_db
    def test_tidak_bisa_selesai_tanpa_persetujuan(self, workspace, staf_a, divisi_a, jenjang, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id, _ = self._ajukan(workspace, divisi_a, staf_a)
        _, selesai = self._state(workspace, divisi_a)
        response = _klien(staf_a).patch(
            self._detail(workspace, divisi_a, issue_id), {"state": str(selesai.id)}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, getattr(response, "data", None)
        assert "disetujui" in str(getattr(response, "data", ""))

    @pytest.mark.django_db
    def test_bisa_selesai_setelah_disetujui(
        self, workspace, staf_a, bos_divisi_a, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id, baris = self._ajukan(workspace, divisi_a, staf_a)
        _klien(bos_divisi_a).post(
            URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id) + f"{baris.id}/",
            {"aksi": "setujui"},
            format="json",
        )
        _, selesai = self._state(workspace, divisi_a)
        response = _klien(staf_a).patch(
            self._detail(workspace, divisi_a, issue_id), {"state": str(selesai.id)}, format="json"
        )
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(
            response, "data", None
        )

    @pytest.mark.django_db
    def test_ditolak_tetap_tidak_bisa_selesai(
        self, workspace, staf_a, bos_divisi_a, divisi_a, jenjang, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id, baris = self._ajukan(workspace, divisi_a, staf_a)
        _klien(bos_divisi_a).post(
            URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id) + f"{baris.id}/",
            {"aksi": "tolak", "alasan": "belum rapi"},
            format="json",
        )
        _, selesai = self._state(workspace, divisi_a)
        response = _klien(staf_a).patch(
            self._detail(workspace, divisi_a, issue_id), {"state": str(selesai.id)}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, getattr(response, "data", None)

    @pytest.mark.django_db
    def test_buat_langsung_selesai_ditolak(self, workspace, staf_a, divisi_a, jenjang, monkeypatch):
        """Create-as-done ikut gerbang: belum ada baris disetujui yang bisa dipakai."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _, selesai = self._state(workspace, divisi_a)
        response = _klien(staf_a).post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Langsung selesai", "assignee_ids": [str(staf_a.id)], "state": str(selesai.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, getattr(response, "data", None)

    @pytest.mark.django_db
    def test_komentar_tetap_terbuka(self, workspace, staf_a, bos_divisi_a, divisi_a, jenjang, monkeypatch):
        """Percakapan bukan pekerjaan: atasan perlu bisa bertanya sebelum memutuskan."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id, baris = self._ajukan(workspace, divisi_a, staf_a)
        response = _klien(bos_divisi_a).post(
            URL_KOMENTAR.format(slug=workspace.slug, project_id=divisi_a.id, issue_id=issue_id),
            {"comment_html": "<p>Maksudnya apa?</p>"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)

    @pytest.mark.django_db
    def test_sesudah_disetujui_tidak_mengantre_lagi(
        self, workspace, staf_a, bos_divisi_a, divisi_a, jenjang, monkeypatch
    ):
        """Regresi: update() staf tidak boleh membuka antrean baru tiap suntingan."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id, baris = self._ajukan(workspace, divisi_a, staf_a)
        _klien(bos_divisi_a).post(
            URL_PERSETUJUAN.format(slug=workspace.slug, project_id=divisi_a.id) + f"{baris.id}/",
            {"aksi": "setujui"},
            format="json",
        )
        response = _klien(staf_a).patch(
            self._detail(workspace, divisi_a, issue_id), {"priority": "urgent"}, format="json"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT, getattr(response, "data", None)
        assert not PersetujuanPenugasan.objects.filter(issue_id=issue_id, status="menunggu").exists()

    @pytest.mark.django_db
    def test_tugas_atasan_TIDAK_butuh_persetujuan(
        self, workspace, bos_divisi_a, divisi_a, jenjang, monkeypatch
    ):
        """Supervisor (dan ke atas) bebas sampai selesai: tak ada baris antrean."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        client = _klien(bos_divisi_a)
        response = client.post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi_a.id),
            {"name": "Tugas supervisor", "assignee_ids": [str(bos_divisi_a.id)]},
            format="json",
        )
        assert response.json().get("approval_status") is None
        _, selesai = self._state(workspace, divisi_a)
        patch = client.patch(
            self._detail(workspace, divisi_a, response.json()["id"]),
            {"priority": "urgent", "state": str(selesai.id)},
            format="json",
        )
        assert patch.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(
            patch, "data", None
        )

    @pytest.mark.django_db
    def test_katup_mati_melepas_gerbang_selesai(self, workspace, staf_a, divisi_a, jenjang, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id, _ = self._ajukan(workspace, divisi_a, staf_a)
        monkeypatch.delenv(FLAG_GERBANG)
        _, selesai = self._state(workspace, divisi_a)
        tutup = _klien(staf_a).patch(
            self._detail(workspace, divisi_a, issue_id), {"state": str(selesai.id)}, format="json"
        )
        assert tutup.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(
            tutup, "data", None
        )


# --------------------------------------------------------------------------
# 7. Pilih departemen sendiri + bawaan staf + otomatis masuk Wiki (2026-10-26)
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestPenempatanMandiriDanWiki:
    @pytest.fixture
    def struktur(self, workspace):
        from plane.db.models import Departemen, Divisi  # noqa: PLC0415

        divisi = Divisi.objects.create(workspace=workspace, kode="D9", nama="Divisi 9")
        return Departemen.objects.create(workspace=workspace, divisi=divisi, kode="DP9", nama="Dept 9")

    @pytest.mark.django_db
    def test_belum_ditempatkan_perlu_pilih_lalu_jadi_staf(self, workspace, staf_a, struktur):
        from plane.app.views.penempatan_saya import perlu_pilih_departemen  # noqa: PLC0415

        assert perlu_pilih_departemen(staf_a, workspace.id) is True
        response = _klien(staf_a).post(
            f"/api/workspaces/{workspace.slug}/penempatan-saya/", {"departemen_id": str(struktur.id)}, format="json"
        )
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)
        baris = JabatanOrganisasi.objects.get(workspace=workspace, member=staf_a)
        assert (baris.tingkat, baris.departemen_id) == (TINGKAT_MEMBER, struktur.id)
        assert perlu_pilih_departemen(staf_a, workspace.id) is False

    @pytest.mark.django_db
    def test_sudah_ditempatkan_tidak_bisa_pindah_sendiri(self, workspace, staf_a, struktur, jenjang):
        JabatanOrganisasi.objects.filter(workspace=workspace, member=staf_a).update(departemen=struktur)
        response = _klien(staf_a).post(
            f"/api/workspaces/{workspace.slug}/penempatan-saya/", {"departemen_id": str(struktur.id)}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_direktur_tanpa_tempat_tidak_diminta_memilih(self, workspace, direktur, struktur, jenjang):
        from plane.app.views.penempatan_saya import perlu_pilih_departemen  # noqa: PLC0415

        assert perlu_pilih_departemen(direktur, workspace.id) is False

    @pytest.mark.django_db
    def test_tanpa_jabatan_dihitung_staf_untuk_kolaborasi(self, workspace, staf_a, staf_a2, divisi_a, struktur):
        from plane.utils.hierarki import tingkat_efektif  # noqa: PLC0415

        assert tingkat_efektif(staf_a.id, workspace.id) == TINGKAT_MEMBER
        for u in (staf_a, staf_a2):
            JabatanOrganisasi.objects.create(workspace=workspace, member=u, tingkat=TINGKAT_MEMBER, departemen=struktur)
        assert galat_penugasan(divisi_a.id, [staf_a.id, staf_a2.id], actor=staf_a, abaikan_katup=True) is None

    @pytest.mark.django_db
    def test_anggota_workspace_baru_dan_lama_masuk_wiki(self, workspace, bos_divisi_a):
        from plane.db.wiki_default import gabungkan_semua_ke_wiki  # noqa: PLC0415

        wiki = Project.objects.create(name="Wiki", identifier="WIKI", workspace=workspace, created_by=bos_divisi_a)
        baru = _buat_user("baru", workspace)  # signal: anggota workspace baru
        assert ProjectMember.objects.filter(project=wiki, member=baru, is_active=True, role=15).exists()
        # lama: dihapus dari Wiki lalu di-backfill; role admin yang sudah ada tidak diturunkan
        ProjectMember.objects.filter(project=wiki, member=baru).update(is_active=False)
        assert gabungkan_semua_ke_wiki(workspace.id) >= 1
        assert ProjectMember.objects.filter(project=wiki, member=baru, is_active=True).exists()
