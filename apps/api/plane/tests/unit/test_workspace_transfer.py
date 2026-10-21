# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Pemindahan workspace antar database, diuji pulang-pergi sungguhan.

Uji terpenting di berkas ini bukan yang pulang-pergi itu, melainkan
`test_tidak_ada_model_yang_lolos_klasifikasi`. Eksporter yang melewatkan satu
model tetap sukses, impornya tetap sukses, dan kehilangannya baru ketahuan
berbulan-bulan kemudian. Uji itulah yang membuat model ke-128 tidak bisa masuk
diam-diam.
"""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from plane.db.models import (
    Page,
    Project,
    ProjectPage,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.utils.workspace_transfer import klasifikasi, kumpulkan, manifes_aset


def _bikin_isi(slug="pindah-a"):
    pemilik = User.objects.create(email=f"{slug}@demo.test", username=f"{slug}_demo_test")
    rekan = User.objects.create(email=f"{slug}2@demo.test", username=f"{slug}2_demo_test")
    ws = Workspace.objects.create(name=slug, slug=slug, owner=pemilik)
    WorkspaceMember.objects.create(workspace=ws, member=pemilik, role=20)
    WorkspaceMember.objects.create(workspace=ws, member=rekan, role=15)
    proyek = Project.objects.create(workspace=ws, identifier="PX", name="Proyek X", network=2)
    halaman = Page.objects.create(workspace=ws, name="Halaman X", owned_by=pemilik, access=0)
    ProjectPage.objects.create(page=halaman, project=proyek, workspace=ws)
    anak = Page.objects.create(
        workspace=ws, name="Anak X", owned_by=pemilik, access=0, parent=halaman
    )
    ProjectPage.objects.create(page=anak, project=proyek, workspace=ws)
    return ws, pemilik, proyek, halaman


@pytest.mark.unit
@pytest.mark.django_db
class TestKlasifikasi:
    def test_tidak_ada_model_yang_lolos_klasifikasi(self):
        """Model baru WAJIB diputuskan nasibnya, tidak boleh menghilang diam-diam.

        Kalau uji ini gagal, jangan menambahkan modelnya ke ekspor secara refleks.
        Putuskan dulu: ia milik workspace (biarkan ber-FK workspace atau daftarkan
        di LEWAT_INDUK) atau milik instance (daftarkan di DILEWATI dengan alasan).
        """
        lolos = klasifikasi()["tidak_dikenal"]
        assert lolos == [], (
            "Model berikut belum diputuskan nasibnya saat workspace dipindahkan, "
            "jadi datanya akan hilang tanpa gejala: " + ", ".join(lolos)
        )

    def test_setiap_pengecualian_punya_alasan_tertulis(self):
        """Daftar pengecualian tanpa alasan berubah jadi tempat sampah."""
        from plane.utils.workspace_transfer import DILEWATI

        tanpa_alasan = [k for k, v in DILEWATI.items() if not v or len(v) < 10]
        assert tanpa_alasan == []

    def test_yang_dilewati_dan_yang_ikut_tidak_pernah_bertumpuk(self):
        from plane.utils.workspace_transfer import DILEWATI, KHUSUS, LEWAT_INDUK

        assert set(DILEWATI) & set(LEWAT_INDUK) == set()
        assert set(DILEWATI) & set(KHUSUS) == set()


@pytest.mark.unit
@pytest.mark.django_db
class TestPengumpulan:
    def test_hanya_baris_workspace_ini_yang_terkumpul(self):
        ws_a, _, _, _ = _bikin_isi("pindah-a")
        _bikin_isi("pindah-b")

        per_model = {label: qs.count() for label, qs in kumpulkan(ws_a)}

        assert per_model["db.Workspace"] == 1
        assert per_model["db.Project"] == 1
        assert per_model["db.Page"] == 2
        assert per_model["db.WorkspaceMember"] == 2

    def test_hanya_anggota_workspace_ini_yang_ikut(self):
        """Identitas itu global. Membawa seluruh tabel User berarti membocorkan
        daftar pengguna kolam gratis ke instance satu pelanggan."""
        ws_a, _, _, _ = _bikin_isi("pindah-c")
        _bikin_isi("pindah-d")

        per_model = dict(kumpulkan(ws_a))
        assert per_model["db.User"].count() == 2
        assert User.objects.count() >= 4

    def test_manifes_aset_kosong_kalau_tidak_ada_berkas(self):
        ws, _, _, _ = _bikin_isi("pindah-e")
        assert manifes_aset(ws) == []


@pytest.mark.unit
@pytest.mark.django_db
class TestPulangPergi:
    def test_workspace_utuh_kembali_dengan_UUID_YANG_SAMA(self, tmp_path):
        """UUID dipertahankan, dan itu syarat mutlak.

        Ribuan baris lain menunjuk workspace, project, halaman, dan orang lewat
        UUID-nya. Kalau impor menerbitkan UUID baru, seluruh rujukan itu harus
        dipetakan ulang, dan pemetaan ulang di 127 model adalah cara yang pasti
        meleset di satu tempat.
        """
        ws, pemilik, proyek, halaman = _bikin_isi("pindah-f")
        ws_id, proyek_id, halaman_id, pemilik_id = ws.id, proyek.id, halaman.id, pemilik.id
        berkas = tmp_path / "pindah-f.json.gz"

        call_command("export_workspace", "pindah-f", out=str(berkas))
        assert berkas.exists()

        # Hapus SUNGGUHAN, bukan hapus lunak: hapus lunak menyisakan barisnya dan
        # membuat uji ini membuktikan sesuatu yang tidak terjadi.
        Workspace.all_objects.filter(pk=ws_id).delete()
        assert not Workspace.all_objects.filter(pk=ws_id).exists()
        assert Project.all_objects.filter(pk=proyek_id).count() == 0

        call_command("import_workspace", str(berkas), terapkan=True)

        assert Workspace.all_objects.get(pk=ws_id).slug == "pindah-f"
        assert Project.all_objects.get(pk=proyek_id).name == "Proyek X"
        assert Page.all_objects.get(pk=halaman_id).name == "Halaman X"
        assert WorkspaceMember.all_objects.filter(workspace_id=ws_id).count() == 2
        # Pengguna tidak ikut terhapus karena mereka bukan anak dari Workspace,
        # jadi impornya menemukan UUID yang sama dan tidak bentrok.
        assert User.objects.filter(pk=pemilik_id).exists()

    def test_rujukan_induk_anak_selamat(self, tmp_path):
        """Page.parent menunjuk Page lain. Inilah yang menuntut constraint ditunda."""
        ws, _, _, halaman = _bikin_isi("pindah-g")
        anak = Page.objects.get(workspace=ws, name="Anak X")
        ws_id, induk_id, anak_id = ws.id, halaman.id, anak.id
        berkas = tmp_path / "pindah-g.json.gz"

        call_command("export_workspace", "pindah-g", out=str(berkas))
        Workspace.all_objects.filter(pk=ws_id).delete()
        call_command("import_workspace", str(berkas), terapkan=True)

        assert Page.all_objects.get(pk=anak_id).parent_id == induk_id

    def test_uji_kering_tidak_menulis_apa_pun(self, tmp_path):
        ws, _, _, _ = _bikin_isi("pindah-h")
        ws_id = ws.id
        berkas = tmp_path / "pindah-h.json.gz"
        call_command("export_workspace", "pindah-h", out=str(berkas))
        Workspace.all_objects.filter(pk=ws_id).delete()

        call_command("import_workspace", str(berkas))  # tanpa --terapkan

        assert not Workspace.all_objects.filter(pk=ws_id).exists()


@pytest.mark.unit
@pytest.mark.django_db
class TestPenolakan:
    def test_menolak_kalau_slug_sudah_ada(self, tmp_path):
        _bikin_isi("pindah-i")
        berkas = tmp_path / "pindah-i.json.gz"
        call_command("export_workspace", "pindah-i", out=str(berkas))

        with pytest.raises(CommandError, match="sudah ada"):
            call_command("import_workspace", str(berkas), terapkan=True)

    def test_menolak_kalau_surel_sama_tapi_UUID_berbeda(self, tmp_path):
        """Melanjutkan berarti FK ribuan baris menunjuk ke ORANG YANG SALAH."""
        ws, _, _, _ = _bikin_isi("pindah-j")
        ws_id = ws.id
        berkas = tmp_path / "pindah-j.json.gz"
        call_command("export_workspace", "pindah-j", out=str(berkas))

        Workspace.all_objects.filter(pk=ws_id).delete()
        # Orang yang sama, mesin berbeda, UUID berbeda.
        User.objects.filter(email="pindah-j@demo.test").delete()
        User.objects.create(email="pindah-j@demo.test", username="orang_lain")

        with pytest.raises(CommandError, match="UUID berbeda"):
            call_command("import_workspace", str(berkas), terapkan=True)

    def test_menolak_format_yang_tidak_dikenali(self, tmp_path):
        import gzip
        import json

        berkas = tmp_path / "asing.json.gz"
        with gzip.open(berkas, "wt", encoding="utf-8") as f:
            json.dump({"format": 99}, f)

        with pytest.raises(CommandError, match="tidak dikenali"):
            call_command("import_workspace", str(berkas))
