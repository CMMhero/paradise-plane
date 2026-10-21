# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Objek penyimpanan saat workspace dipindahkan antar instance.

Diuji dengan ganda penyimpanan, bukan MinIO sungguhan. Uji yang menyambung ke
MinIO akan hijau di mesin yang kebetulan punya MinIO menyala dan merah di mesin
kontributor, dan uji yang merahnya bergantung mesin adalah uji yang segera
diabaikan orang. Yang perlu dijaga di sini logika saya, bukan boto3.
"""

import json
import tarfile
from io import BytesIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from plane.db.models import FileAsset, Workspace
from plane.tests.unit.test_workspace_transfer import _bikin_isi
from plane.utils.workspace_transfer import unduh_aset, unggah_aset


class PenyimpananPalsu:
    """Cukup meniru yang benar-benar dipakai: `s3_client.get_object` dan `upload_file`."""

    def __init__(self, isi=None, gagal_unggah=()):
        self.isi = dict(isi or {})
        self.gagal_unggah = set(gagal_unggah)
        self.aws_storage_bucket_name = "uji"
        self.s3_client = self
        self.terunggah = {}

    def get_object(self, Bucket, Key):  # noqa: N803
        from botocore.exceptions import ClientError

        if Key not in self.isi:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        data, tipe = self.isi[Key]
        return {"ContentLength": len(data), "Body": BytesIO(data), "ContentType": tipe}

    def upload_file(self, file_obj, object_name, content_type=None, extra_args=None):
        if object_name in self.gagal_unggah:
            return False
        self.terunggah[object_name] = (file_obj.read(), content_type)
        return True


def _pasang(monkeypatch, palsu):
    monkeypatch.setattr("plane.settings.storage.S3Storage", lambda *a, **k: palsu)
    return palsu


def _diam(*a, **k):
    pass


@pytest.mark.unit
class TestUnduh:
    def test_menyimpan_isi_DAN_tipe_kontennya(self, monkeypatch, tmp_path):
        """Tipe konten disimpan, bukan ditebak ulang dari ekstensi saat impor.

        Penampil Wiki merender PDF di dalam iframe peramban, dan peramban menolak
        menampilkannya kalau tipenya jatuh jadi application/octet-stream.
        """
        _pasang(
            monkeypatch,
            PenyimpananPalsu(
                {
                    "ws/a.pdf": (b"%PDF-1.4 palsu", "application/pdf"),
                    "ws/b.png": (b"PNG palsu", "image/png"),
                }
            ),
        )
        tar = tmp_path / "aset.tar.gz"

        hasil = unduh_aset(["ws/a.pdf", "ws/b.png"], str(tar), log=_diam)

        assert hasil["disalin"] == 2
        assert hasil["hilang"] == []
        assert hasil["bytes"] == len(b"%PDF-1.4 palsu") + len(b"PNG palsu")

        with tarfile.open(tar, "r:gz") as t:
            manifes = json.loads(t.extractfile("_manifest.json").read())
            assert manifes["content_types"]["ws/a.pdf"] == "application/pdf"
            assert t.extractfile("ws/b.png").read() == b"PNG palsu"

    def test_objek_hilang_DICATAT_bukan_menggagalkan(self, monkeypatch, tmp_path):
        """Berkas yang sudah hilang di asal tidak akan jadi ada karena ekspor dibatalkan."""
        _pasang(monkeypatch, PenyimpananPalsu({"ws/ada.txt": (b"ok", "text/plain")}))

        hasil = unduh_aset(
            ["ws/ada.txt", "ws/lenyap.txt"], str(tmp_path / "a.tar.gz"), log=_diam
        )

        assert hasil["disalin"] == 1
        assert hasil["hilang"] == ["ws/lenyap.txt"]


@pytest.mark.unit
class TestUnggah:
    def test_memulihkan_isi_dan_tipenya(self, monkeypatch, tmp_path):
        _pasang(monkeypatch, PenyimpananPalsu({"ws/a.pdf": (b"isi pdf", "application/pdf")}))
        tar = tmp_path / "a.tar.gz"
        unduh_aset(["ws/a.pdf"], str(tar), log=_diam)

        tujuan = _pasang(monkeypatch, PenyimpananPalsu())
        hasil = unggah_aset(str(tar), log=_diam)

        assert hasil["diunggah"] == 1
        assert tujuan.terunggah["ws/a.pdf"] == (b"isi pdf", "application/pdf")
        assert "_manifest.json" not in tujuan.terunggah, "manifes tidak boleh jadi objek"

    def test_yang_gagal_MENGGAGALKAN(self, monkeypatch, tmp_path):
        """Kebalikan dari kebijakan unduh, dan bedanya disengaja.

        Unggahan tak lengkap menghasilkan instance yang tampak beres padahal
        sebagian berkasnya tidak akan pernah terbuka, dan itu baru ketahuan oleh
        pemakainya.
        """
        _pasang(monkeypatch, PenyimpananPalsu({"ws/a.txt": (b"x", "text/plain")}))
        tar = tmp_path / "a.tar.gz"
        unduh_aset(["ws/a.txt"], str(tar), log=_diam)

        _pasang(monkeypatch, PenyimpananPalsu(gagal_unggah=["ws/a.txt"]))
        with pytest.raises(RuntimeError, match="gagal diunggah"):
            unggah_aset(str(tar), log=_diam)


@pytest.mark.unit
@pytest.mark.django_db
class TestPerintahnya:
    def _dengan_aset(self, slug):
        ws, _, proyek, _ = _bikin_isi(slug)
        FileAsset.objects.create(
            workspace=ws, project=proyek, asset=f"{slug}/materi.pdf", size=8, is_uploaded=True
        )
        return ws

    def test_objeknya_ikut_secara_BAWAAN_tanpa_saklar_apa_pun(self, monkeypatch, tmp_path):
        """Ekspor yang secara bawaan setengah adalah ekspor yang setengahnya terlupa."""
        self._dengan_aset("obj-a")
        _pasang(monkeypatch, PenyimpananPalsu({"obj-a/materi.pdf": (b"isi pdf", "application/pdf")}))

        call_command("export_workspace", "obj-a", out=str(tmp_path / "obj-a.json.gz"))

        assert (tmp_path / "obj-a-assets.tar.gz").exists(), "tar objek bersebelahan dengan barisnya"

    def test_impor_MENOLAK_kalau_tar_objeknya_tertinggal(self, monkeypatch, tmp_path):
        """Menyalin satu berkas lalu lupa satunya adalah kejadian yang pasti terjadi."""
        self._dengan_aset("obj-b")
        _pasang(monkeypatch, PenyimpananPalsu({"obj-b/materi.pdf": (b"x", "application/pdf")}))
        berkas = tmp_path / "obj-b.json.gz"
        call_command("export_workspace", "obj-b", out=str(berkas))

        (tmp_path / "obj-b-assets.tar.gz").unlink()
        Workspace.all_objects.filter(slug="obj-b").delete()

        with pytest.raises(CommandError, match="tidak ada"):
            call_command("import_workspace", str(berkas), terapkan=True)

    def test_no_assets_melewatinya_dengan_sadar(self, monkeypatch, tmp_path):
        self._dengan_aset("obj-c")
        _pasang(monkeypatch, PenyimpananPalsu({"obj-c/materi.pdf": (b"x", "application/pdf")}))
        berkas = tmp_path / "obj-c.json.gz"
        call_command("export_workspace", "obj-c", out=str(berkas))
        (tmp_path / "obj-c-assets.tar.gz").unlink()
        Workspace.all_objects.filter(slug="obj-c").delete()

        call_command("import_workspace", str(berkas), terapkan=True, no_assets=True)

        assert Workspace.all_objects.filter(slug="obj-c").exists()

    def test_pulang_pergi_penuh_baris_DAN_objeknya(self, monkeypatch, tmp_path):
        ws_id = self._dengan_aset("obj-d").id
        _pasang(monkeypatch, PenyimpananPalsu({"obj-d/materi.pdf": (b"isi asli", "application/pdf")}))
        berkas = tmp_path / "obj-d.json.gz"
        call_command("export_workspace", "obj-d", out=str(berkas))

        Workspace.all_objects.filter(pk=ws_id).delete()
        tujuan = _pasang(monkeypatch, PenyimpananPalsu())

        call_command("import_workspace", str(berkas), terapkan=True)

        assert Workspace.all_objects.filter(pk=ws_id).exists()
        assert tujuan.terunggah["obj-d/materi.pdf"] == (b"isi asli", "application/pdf")
