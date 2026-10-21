# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji matriks hak Wiki
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Matriks hak Wiki: siapa boleh apa, atas materi siapa.

Aturan yang dijaga berkas ini datang dari pemilik instance, dan tiga barisnya
sengaja BERBEDA. Menyamakan salah satunya adalah cara paling gampang merusak
Wiki 83 orang tanpa satu pun galat muncul:

    baca             semua anggota project Wiki
    unggah baru      anggota aktif divisi pemilik folder teratas
    kelola yang ada  pengunggahnya, kepala divisi pemilik, atau Super Admin

Ditambah tiga penjaga struktur yang menutup lubang yang TIDAK tertutup oleh
aturan kepemilikan, karena ketiganya merusak materi orang lain lewat operasi
atas halaman milik sendiri: arsip beruntun, buka arsip yang memutus induk, dan
hapus folder yang melempar isinya ke tingkat teratas tanpa pemilik divisi.

Murni, tanpa database. Yang diuji percabangan keputusannya, dan justru di situ
bug-nya hidup; querinya sendiri sudah diuji oleh jalur integrasi.
"""

from types import SimpleNamespace

import pytest
from rest_framework.exceptions import PermissionDenied

from plane.app.permissions import page as izin

pytestmark = pytest.mark.unit

SAYA = "user-saya"
ORANG_LAIN = "user-lain"


def _halaman(id="p1", owner=SAYA, parent_id=None):
    return SimpleNamespace(id=id, owned_by_id=owner, parent_id=parent_id)


class _Qs:
    def __init__(self, hasil):
        self._hasil = hasil

    def first(self):
        return self._hasil[0] if self._hasil else None

    def exists(self):
        return bool(self._hasil)


class _PageFake:
    """Pengganti model Page: menjawab dari bentuk filternya, bukan dari database."""

    def __init__(self, per_id=None, induk_terarsip=False, punya_anak=False):
        self.per_id = per_id or {}
        self.induk_terarsip = induk_terarsip
        self.punya_anak = punya_anak
        self.objects = self

    def filter(self, **kw):
        if "archived_at__isnull" in kw:
            return _Qs([object()] if self.induk_terarsip else [])
        if "parent_id" in kw:
            return _Qs([object()] if self.punya_anak else [])
        return _Qs([self.per_id[kw["id"]]] if kw.get("id") in self.per_id else [])


def _pasang(
    monkeypatch,
    *,
    page_fake,
    boleh_unggah=True,
    boleh_kelola=True,
    keturunan_asing=False,
    super_admin=False,
    kepala_divisi=False,
):
    monkeypatch.setattr(izin, "Page", page_fake)
    monkeypatch.setattr(izin, "can_edit_wiki_page", lambda u, p: boleh_unggah)
    monkeypatch.setattr(izin, "can_manage_wiki_page", lambda u, p: boleh_kelola)
    monkeypatch.setattr(izin, "has_foreign_descendants", lambda p, u: keturunan_asing)
    monkeypatch.setattr(izin, "is_super_admin", lambda u: super_admin)
    monkeypatch.setattr(izin, "is_division_lead", lambda u, p: kepala_divisi)


def _tanya(method="PATCH", action=None, page_id="p1", data=None, role=izin.MEMBER):
    request = SimpleNamespace(user=SimpleNamespace(id=SAYA), method=method, data=data or {})
    view = SimpleNamespace(action=action)
    return izin.ProjectPagePermission()._has_wiki_governed_access(
        request, view, "ws", "proj", page_id, role
    )


# --- baca --------------------------------------------------------------------


def test_semua_anggota_boleh_membaca(monkeypatch):
    _pasang(monkeypatch, page_fake=_PageFake(), boleh_unggah=False, boleh_kelola=False)
    assert _tanya(method="GET", action="retrieve", role=izin.GUEST) is True


# --- unggah baru -------------------------------------------------------------


def test_anggota_divisi_boleh_menaruh_materi_baru_di_folder_divisinya(monkeypatch):
    _pasang(monkeypatch, page_fake=_PageFake({"folder": _halaman(id="folder")}), boleh_unggah=True)
    assert _tanya(method="POST", action="create", page_id=None, data={"parent": "folder"}) is True


def test_bukan_anggota_divisi_ditolak_menaruh_materi(monkeypatch):
    _pasang(monkeypatch, page_fake=_PageFake({"folder": _halaman(id="folder")}), boleh_unggah=False)
    assert _tanya(method="POST", action="create", page_id=None, data={"parent": "folder"}) is False


def test_folder_divisi_baru_hanya_boleh_dibuat_admin(monkeypatch):
    _pasang(monkeypatch, page_fake=_PageFake())
    assert _tanya(method="POST", action="create", page_id=None, data={}) is False
    assert _tanya(method="POST", action="create", page_id=None, data={}, role=izin.ADMIN) is True


# --- kelola materi yang sudah ada --------------------------------------------


def test_pengunggah_boleh_menyunting_materinya_sendiri(monkeypatch):
    _pasang(monkeypatch, page_fake=_PageFake({"p1": _halaman()}), boleh_kelola=True)
    assert _tanya(action="partial_update") is True


def test_rekan_sedivisi_ditolak_menyunting_materi_orang_lain(monkeypatch):
    # Inti aturannya: hak UNGGAH tetap ada, hak KELOLA tidak ikut.
    _pasang(
        monkeypatch,
        page_fake=_PageFake({"p1": _halaman(owner=ORANG_LAIN)}),
        boleh_unggah=True,
        boleh_kelola=False,
    )
    with pytest.raises(PermissionDenied):
        _tanya(action="partial_update")


def test_rekan_sedivisi_ditolak_mengunci_materi_orang_lain(monkeypatch):
    # Mengunci halaman membuat pemiliknya sendiri tidak bisa menyuntingnya lagi.
    _pasang(
        monkeypatch,
        page_fake=_PageFake({"p1": _halaman(owner=ORANG_LAIN)}),
        boleh_kelola=False,
    )
    with pytest.raises(PermissionDenied):
        _tanya(method="POST", action="lock")


def test_super_admin_boleh_menghapus_materi_siapa_pun(monkeypatch):
    _pasang(
        monkeypatch,
        page_fake=_PageFake({"p1": _halaman(owner=ORANG_LAIN)}),
        boleh_kelola=True,
        super_admin=True,
    )
    assert _tanya(method="DELETE", action="destroy") is True


# --- penjaga struktur --------------------------------------------------------


def test_arsip_folder_berisi_materi_orang_lain_ditolak_untuk_pemilik_biasa(monkeypatch):
    _pasang(
        monkeypatch,
        page_fake=_PageFake({"p1": _halaman()}),
        boleh_kelola=True,
        keturunan_asing=True,
    )
    with pytest.raises(PermissionDenied):
        _tanya(method="POST", action="archive")


def test_kepala_divisi_boleh_mengarsipkan_folder_berisi_materi_orang_lain(monkeypatch):
    _pasang(
        monkeypatch,
        page_fake=_PageFake({"p1": _halaman()}),
        boleh_kelola=True,
        keturunan_asing=True,
        kepala_divisi=True,
    )
    assert _tanya(method="POST", action="archive") is True


def test_arsip_folder_kosong_tetap_boleh(monkeypatch):
    _pasang(monkeypatch, page_fake=_PageFake({"p1": _halaman()}), keturunan_asing=False)
    assert _tanya(method="POST", action="archive") is True


def test_buka_arsip_ditolak_selama_folder_induknya_masih_terarsip(monkeypatch):
    # Kalau diloloskan, Plane memutus parent-nya dan materi itu kehilangan divisi
    # pemiliknya, sehingga tak seorang pun bisa mengeditnya lagi.
    _pasang(
        monkeypatch,
        page_fake=_PageFake({"p1": _halaman(parent_id="folder")}, induk_terarsip=True),
    )
    with pytest.raises(PermissionDenied):
        _tanya(method="DELETE", action="unarchive")


def test_buka_arsip_boleh_kalau_induknya_sudah_tidak_terarsip(monkeypatch):
    _pasang(
        monkeypatch,
        page_fake=_PageFake({"p1": _halaman(parent_id="folder")}, induk_terarsip=False),
    )
    assert _tanya(method="DELETE", action="unarchive") is True


def test_hapus_folder_yang_masih_berisi_materi_ditolak(monkeypatch):
    _pasang(monkeypatch, page_fake=_PageFake({"p1": _halaman()}, punya_anak=True))
    with pytest.raises(PermissionDenied):
        _tanya(method="DELETE", action="destroy")


def test_hapus_materi_sendiri_yang_tidak_punya_anak_boleh(monkeypatch):
    _pasang(monkeypatch, page_fake=_PageFake({"p1": _halaman()}, punya_anak=False))
    assert _tanya(method="DELETE", action="destroy") is True
