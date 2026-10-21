# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji Materi Wiki
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Materi Wiki: berkasnya sendiri, bukan halaman yang diketik.

Dua invarian dijaga di sini.

SATU, cara sebuah berkas ditampilkan ditentukan tipenya, dan keputusan itu harus
jujur. Menjanjikan pratinjau untuk berkas yang tidak bisa dibuka peramban
menghasilkan bingkai kosong yang tidak pernah memuat, dan itu lebih buruk
daripada tombol unduh. Word, Excel, dan PowerPoint karena itu ditandai
"konversi", bukan "pdf", karena keduanya beda nasib.

DUA, aturan hapus materi harus sama persis dengan aturan hapus halaman, cuma
sumbernya beda: pemilik materi adalah `created_by` pada berkasnya. Kalau
keduanya boleh berbeda, cepat atau lambat mereka akan berbeda.

Murni, tanpa database.
"""

from types import SimpleNamespace

import pytest

from plane.utils import wiki_access
from plane.app.views.page import wiki_material

pytestmark = pytest.mark.unit

SAYA = "user-saya"
ORANG_LAIN = "user-lain"


# --- bagaimana sebuah berkas ditampilkan -------------------------------------


@pytest.mark.parametrize(
    "mime,harap",
    [
        ("application/pdf", "pdf"),
        ("image/png", "image"),
        ("image/svg+xml", "image"),
        ("video/mp4", "video"),
        ("audio/mpeg", "audio"),
        ("text/plain", "text"),
        ("text/csv", "text"),
        # Ketiganya tidak bisa dibuka peramban mana pun, jadi harus lewat
        # konversi, bukan langsung diakui sebagai pratinjau.
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "konversi"),
        ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "konversi"),
        ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "konversi"),
        ("application/vnd.ms-powerpoint", "konversi"),
        ("application/vnd.oasis.opendocument.text", "konversi"),
        # Lolos prefix video/ tapi tidak ada peramban yang memutarnya.
        ("video/x-matroska", "none"),
        ("application/zip", "none"),
        ("application/octet-stream", "none"),
        ("", "none"),
    ],
)
def test_jenis_pratinjau_sesuai_tipe_berkas(mime, harap):
    assert wiki_material._jenis_pratinjau(mime) == harap


def test_matroska_diperiksa_sebelum_prefix_video():
    # Urutan cabangnya penting: kalau `video/` diperiksa duluan, mkv akan
    # mendapat pemutar yang tidak akan pernah bisa memutarnya.
    assert wiki_material._jenis_pratinjau("video/x-matroska") != "video"


# --- siapa boleh mengubah dan menghapus materi -------------------------------


def _aset(created_by=SAYA, page_id="topik"):
    return SimpleNamespace(created_by_id=created_by, page_id=page_id)


def _pengguna(uid=SAYA):
    return SimpleNamespace(id=uid, is_anonymous=False)


def _pasang(monkeypatch, *, super_admin=False, kepala_divisi=False, halaman=object()):
    monkeypatch.setattr(wiki_access, "is_super_admin", lambda u: super_admin)
    monkeypatch.setattr(wiki_access, "is_division_lead", lambda u, p: kepala_divisi)

    class _Qs:
        def first(self):
            return halaman

    class _PageFake:
        objects = SimpleNamespace(filter=lambda **kw: _Qs())

    import plane.db.models as models

    monkeypatch.setattr(models, "Page", _PageFake)


def test_pengunggah_boleh_mengelola_materinya_sendiri(monkeypatch):
    _pasang(monkeypatch)
    assert wiki_access.can_manage_wiki_material(_pengguna(), _aset(created_by=SAYA)) is True


def test_rekan_sedivisi_tidak_boleh_mengelola_materi_orang_lain(monkeypatch):
    _pasang(monkeypatch, super_admin=False, kepala_divisi=False)
    assert wiki_access.can_manage_wiki_material(_pengguna(), _aset(created_by=ORANG_LAIN)) is False


def test_kepala_divisi_boleh_mengelola_materi_orang_lain(monkeypatch):
    _pasang(monkeypatch, kepala_divisi=True)
    assert wiki_access.can_manage_wiki_material(_pengguna(), _aset(created_by=ORANG_LAIN)) is True


def test_super_admin_boleh_mengelola_materi_siapa_pun(monkeypatch):
    _pasang(monkeypatch, super_admin=True)
    assert wiki_access.can_manage_wiki_material(_pengguna(), _aset(created_by=ORANG_LAIN)) is True


def test_materi_tanpa_halaman_hanya_boleh_disentuh_pengunggah_atau_super_admin(monkeypatch):
    # Keadaan yang seharusnya tidak pernah terjadi. Kalau terjadi, jawabannya
    # harus menutup, bukan membuka: tanpa halaman tidak ada folder yang bisa
    # dijadikan dasar penilaian kepala divisi.
    _pasang(monkeypatch, kepala_divisi=True)
    assert wiki_access.can_manage_wiki_material(_pengguna(), _aset(created_by=ORANG_LAIN, page_id=None)) is False


def test_pengguna_anonim_ditolak(monkeypatch):
    _pasang(monkeypatch, super_admin=True, kepala_divisi=True)
    assert wiki_access.can_manage_wiki_material(None, _aset(created_by=ORANG_LAIN)) is False
    assert (
        wiki_access.can_manage_wiki_material(SimpleNamespace(id=None, is_anonymous=True), _aset())
        is False
    )
