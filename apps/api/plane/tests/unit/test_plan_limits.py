# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Empat rem kolam gratis, diuji lewat fungsi yang sungguh dipakai view.

Sengaja menguji `plane.utils.plan_limits` langsung, bukan lewat HTTP. Yang perlu
dijaga di sini adalah ATURANNYA, dan aturan itu hidup di satu berkas yang
dipanggil delapan titik. Uji lewat HTTP akan menguji satu titik saja, lalu
memberi rasa aman yang salah tentang tujuh sisanya.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from plane.db.models import (
    FileAsset,
    User,
    Workspace,
    WorkspaceMember,
    WorkspacePlan,
)
from plane.utils import plan_limits as pl


def _pengguna(email, terakhir_aktif=None):
    u = User.objects.create(email=email, username=email.replace("@", "_").replace(".", "_"))
    if terakhir_aktif is not None:
        User.objects.filter(pk=u.pk).update(last_active=terakhir_aktif)
        u.refresh_from_db()
    return u


def _workspace(pemilik, slug):
    ws = Workspace.objects.create(name=slug, slug=slug, owner=pemilik)
    WorkspaceMember.objects.create(workspace=ws, member=pemilik, role=20)
    return ws


@pytest.mark.unit
@pytest.mark.django_db
class TestBatasTingkatan:
    def test_workspace_tanpa_baris_dianggap_gratis(self):
        """Baris WorkspacePlan boleh tidak ada, dan itu bukan berarti tanpa batas."""
        ws = _workspace(_pengguna("a@demo.test"), "ws-a")

        assert pl.tingkatan(ws.id) == "FREE"
        assert pl.batas(ws.id, "storage_bytes") == pl.BATAS_TINGKATAN["FREE"]["storage_bytes"]
        assert pl.plan_for(ws.id) is None

    def test_nilai_per_baris_menang_atas_bawaan_tingkatan(self):
        """Ini yang membuat Enterprise 'khusus' bisa ada tanpa tabel kedua."""
        ws = _workspace(_pengguna("b@demo.test"), "ws-b")
        WorkspacePlan.objects.create(
            workspace=ws, tier="ENTERPRISE", max_storage_bytes=7 * pl.GIB
        )

        assert pl.batas(ws.id, "storage_bytes") == 7 * pl.GIB
        # Yang tidak diisi tetap jatuh ke bawaan tingkatannya, di sini tak terbatas.
        assert pl.batas(ws.id, "members") is None

    def test_tingkatan_tak_dikenal_ditutup_bukan_dibuka(self):
        """Data rusak harus menutup. Kalau membuka, satu baris rusak = kuota hilang."""
        ws = _workspace(_pengguna("c@demo.test"), "ws-c")
        WorkspacePlan.objects.create(workspace=ws, tier="TIDAK-ADA-TINGKATAN-INI")

        assert pl.batas(ws.id, "storage_bytes") == pl.BATAS_TINGKATAN["FREE"]["storage_bytes"]


@pytest.mark.unit
@pytest.mark.django_db
class TestRemSatuJumlahWorkspace:
    def test_workspace_pertama_selalu_boleh(self):
        """Kalau yang pertama pun ditolak, tidak ada orang baru yang bisa mulai."""
        pl.periksa_pembuatan_workspace(_pengguna("d@demo.test"))  # tidak melempar

    def test_workspace_kedua_ditolak_untuk_akun_gratis(self):
        pengguna = _pengguna("e@demo.test")
        _workspace(pengguna, "ws-e1")

        with pytest.raises(pl.BatasTerlampaui) as galat:
            pl.periksa_pembuatan_workspace(pengguna)

        assert galat.value.kode == "WORKSPACE_LIMIT_REACHED"
        assert galat.value.status_code == 403

    def test_batas_terlonggar_yang_dipakai_bukan_yang_terketat(self):
        """Pelanggan Pro yang masih punya workspace gratis lama tidak ikut terkunci."""
        pengguna = _pengguna("f@demo.test")
        _workspace(pengguna, "ws-f1")  # gratis, batas 1
        ws2 = _workspace(pengguna, "ws-f2")
        WorkspacePlan.objects.create(workspace=ws2, tier="PRO")  # batas 3

        pl.periksa_pembuatan_workspace(pengguna)  # 2 dari 3, masih boleh


@pytest.mark.unit
@pytest.mark.django_db
class TestRemEmpatVerifikasiSurel:
    def test_mati_secara_bawaan(self, monkeypatch):
        """Instance pasang-sendiri sering tanpa SMTP. Menyala di sana = jalan buntu."""
        monkeypatch.setattr(pl, "WAJIB_VERIFIKASI_EMAIL", False)
        pl.periksa_pembuatan_workspace(_pengguna("g@demo.test"))

    def test_menutup_saat_dinyalakan_dan_surel_belum_terverifikasi(self, monkeypatch):
        monkeypatch.setattr(pl, "WAJIB_VERIFIKASI_EMAIL", True)

        with pytest.raises(pl.BatasTerlampaui) as galat:
            pl.periksa_pembuatan_workspace(_pengguna("h@demo.test"))

        assert galat.value.kode == "EMAIL_NOT_VERIFIED"

    def test_lolos_kalau_surelnya_sudah_terverifikasi(self, monkeypatch):
        monkeypatch.setattr(pl, "WAJIB_VERIFIKASI_EMAIL", True)
        pengguna = _pengguna("i@demo.test")
        User.objects.filter(pk=pengguna.pk).update(is_email_verified=True)
        pengguna.refresh_from_db()

        pl.periksa_pembuatan_workspace(pengguna)


@pytest.mark.unit
@pytest.mark.django_db
class TestRemDuaKuotaPenyimpanan:
    def test_hanya_yang_benar_benar_terunggah_yang_dihitung(self):
        ws = _workspace(_pengguna("j@demo.test"), "ws-j")
        FileAsset.objects.create(workspace=ws, asset="x/a.png", size=100, is_uploaded=True)
        FileAsset.objects.create(workspace=ws, asset="x/b.png", size=900, is_uploaded=False)

        assert pl.penyimpanan_terpakai(ws.id) == 100

    def test_berkas_terhapus_mengembalikan_kuotanya(self):
        ws = _workspace(_pengguna("k@demo.test"), "ws-k")
        aset = FileAsset.objects.create(
            workspace=ws, asset="x/c.png", size=500, is_uploaded=True
        )
        assert pl.penyimpanan_terpakai(ws.id) == 500

        FileAsset.objects.filter(pk=aset.pk).update(deleted_at=timezone.now())
        assert pl.penyimpanan_terpakai(ws.id) == 0

    def test_unggahan_yang_melewati_kuota_ditolak(self):
        ws = _workspace(_pengguna("l@demo.test"), "ws-l")
        WorkspacePlan.objects.create(workspace=ws, tier="FREE", max_storage_bytes=1000)
        FileAsset.objects.create(workspace=ws, asset="x/d.png", size=900, is_uploaded=True)

        pl.periksa_unggahan(ws.id, 100)  # pas di batas, masih boleh

        with pytest.raises(pl.BatasTerlampaui) as galat:
            pl.periksa_unggahan(ws.id, 101)
        assert galat.value.kode == "STORAGE_QUOTA_EXCEEDED"
        assert galat.value.status_code == 413

    def test_aset_tanpa_workspace_tidak_pernah_ditagih(self):
        """Avatar dan sampul pengguna tidak menempel ke workspace mana pun."""
        pl.periksa_unggahan(None, 10**12)


@pytest.mark.unit
@pytest.mark.django_db
class TestRemTigaTidur:
    def test_workspace_beku_menolak_unggahan(self):
        ws = _workspace(_pengguna("m@demo.test", timezone.now() - timedelta(days=400)), "ws-m")
        WorkspacePlan.objects.create(workspace=ws, tier="FREE", uploads_frozen_at=timezone.now())

        with pytest.raises(pl.BatasTerlampaui) as galat:
            pl.periksa_unggahan(ws.id, 1)
        assert galat.value.kode == "WORKSPACE_DORMANT"
        assert galat.value.status_code == 409

    def test_yang_kembali_dibangunkan_saat_itu_juga_bukan_besok(self):
        """Pesan galatnya menyuruh orang masuk lagi lalu coba. Ini yang membuatnya jujur."""
        ws = _workspace(_pengguna("n@demo.test", timezone.now()), "ws-n")
        baris = WorkspacePlan.objects.create(
            workspace=ws,
            tier="FREE",
            uploads_frozen_at=timezone.now(),
            dormant_warned_at=timezone.now(),
            pending_deletion_at=timezone.now(),
        )

        pl.periksa_unggahan(ws.id, 1)  # tidak melempar

        baris.refresh_from_db()
        assert baris.uploads_frozen_at is None
        assert baris.dormant_warned_at is None
        assert baris.pending_deletion_at is None

    def test_sapuan_membekukan_yang_menganggur(self):
        from plane.bgtasks.dormancy_task import sapu_workspace_tidur

        ws = _workspace(_pengguna("o@demo.test", timezone.now() - timedelta(days=120)), "ws-o")

        sapu_workspace_tidur()

        baris = WorkspacePlan.objects.get(workspace=ws, deleted_at__isnull=True)
        assert baris.uploads_frozen_at is not None
        assert baris.pending_deletion_at is None  # 120 hari belum sampai 180

    def test_sapuan_menandai_calon_hapus_tapi_TIDAK_menghapus(self):
        """Penghapusan lewat timer tidak bisa dibatalkan, jadi memang tidak dilakukan."""
        from plane.bgtasks.dormancy_task import sapu_workspace_tidur

        ws = _workspace(_pengguna("p@demo.test", timezone.now() - timedelta(days=400)), "ws-p")

        sapu_workspace_tidur()

        assert Workspace.objects.filter(pk=ws.pk).exists()
        baris = WorkspacePlan.objects.get(workspace=ws, deleted_at__isnull=True)
        assert baris.pending_deletion_at is not None
        assert baris.uploads_frozen_at is not None

    def test_sapuan_tidak_pernah_menidurkan_yang_berbayar(self):
        from plane.bgtasks.dormancy_task import sapu_workspace_tidur

        ws = _workspace(_pengguna("q@demo.test", timezone.now() - timedelta(days=400)), "ws-q")
        WorkspacePlan.objects.create(workspace=ws, tier="PRO")

        sapu_workspace_tidur()

        baris = WorkspacePlan.objects.get(workspace=ws, deleted_at__isnull=True)
        assert baris.uploads_frozen_at is None


@pytest.mark.unit
@pytest.mark.django_db
class TestBatasAnggota:
    def test_menolak_saat_kursi_habis(self):
        ws = _workspace(_pengguna("r@demo.test"), "ws-r")
        WorkspacePlan.objects.create(workspace=ws, tier="FREE", max_members=1)

        with pytest.raises(pl.BatasTerlampaui) as galat:
            pl.periksa_penambahan_anggota(ws.id, jumlah_baru=1)
        assert galat.value.kode == "MEMBER_LIMIT_REACHED"

    def test_tingkatan_tanpa_batas_tidak_pernah_menolak(self):
        ws = _workspace(_pengguna("s@demo.test"), "ws-s")
        WorkspacePlan.objects.create(workspace=ws, tier="EXPERT")

        pl.periksa_penambahan_anggota(ws.id, jumlah_baru=1000)

    def test_undangan_yang_belum_dijawab_IKUT_memakai_kursi(self):
        """Kalau tidak, satu kursi tersisa bisa dipakai mengundang sepuluh orang,
        dan kesepuluhnya akan diterima."""
        from plane.db.models import WorkspaceMemberInvite

        ws = _workspace(_pengguna("t@demo.test"), "ws-t")
        WorkspacePlan.objects.create(workspace=ws, tier="FREE", max_members=3)
        WorkspaceMemberInvite.objects.create(
            workspace=ws, email="calon1@demo.test", token="a", role=15
        )
        WorkspaceMemberInvite.objects.create(
            workspace=ws, email="calon2@demo.test", token="b", role=15
        )

        assert pl.kursi_terpakai(ws.id) == 3  # 1 anggota + 2 undangan

        with pytest.raises(pl.BatasTerlampaui):
            pl.periksa_penambahan_anggota(ws.id, jumlah_baru=1)

    def test_undangan_yang_sudah_dijawab_membebaskan_pesanannya(self):
        from django.utils import timezone as tz
        from plane.db.models import WorkspaceMemberInvite

        ws = _workspace(_pengguna("u@demo.test"), "ws-u")
        WorkspaceMemberInvite.objects.create(
            workspace=ws, email="sudah@demo.test", token="c", role=15,
            responded_at=tz.now(),
        )

        assert pl.kursi_terpakai(ws.id) == 1  # undangan terjawab tidak dihitung lagi

    def test_gratis_bawaannya_PERORANGAN(self):
        """Keputusan user 28 Agt. Pemiliknya sendiri sudah memenuhi kursinya."""
        ws = _workspace(_pengguna("v@demo.test"), "ws-v")

        assert pl.batas(ws.id, "members") == 1
        with pytest.raises(pl.BatasTerlampaui) as galat:
            pl.periksa_penambahan_anggota(ws.id, jumlah_baru=1)
        assert galat.value.kode == "MEMBER_LIMIT_REACHED"
