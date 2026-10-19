# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kanal grup obrolan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kanal grup: yang diuji hanya bagian yang bisa diam-diam salah.

Bukan "apakah kanal tersimpan". Yang diuji: siapa boleh melihat apa. Kanal privat
yang bocor tidak melempar error di mana pun, ia sekadar muncul di layar orang
yang salah, dan tidak ada yang tahu sampai seseorang menyebutkan isinya.

Berlangganan adalah satu-satunya penanda hak baca di seluruh fitur ini. Karena
itu hampir semua uji di berkas ini berbentuk sama: buat keadaan, lalu pastikan
orang yang tidak berlangganan tidak mendapat apa-apa.
"""

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from plane.db.models import Langganan, PesanLangsung, Ruang, User, Workspace, WorkspaceMember


def _orang(nama):
    # `username` unik dan TIDAK boleh dikosongkan: dua User tanpa username
    # menabrak users_username_key, dan galatnya menunjuk ke baris kedua.
    return User.objects.create(
        id=uuid4(), username=nama, email=f"{nama}@paradise.test", display_name=nama, is_active=True
    )


@pytest.fixture
def kantor(db):
    """Satu workspace berisi tiga orang.

    Memakai ORM langsung, bukan plane.tests.factories: factory_boy adalah
    dependensi pengembangan dan tidak ada di image runtime, jadi uji yang
    mengimpornya gagal di container padahal isinya tidak salah apa-apa.
    """
    aku = _orang("kanal-aku")
    workspace = Workspace.objects.create(id=uuid4(), name="Kantor", slug="kanal-uji", owner=aku)
    budi = _orang("kanal-budi")
    citra = _orang("kanal-citra")
    for orang in (aku, budi, citra):
        WorkspaceMember.objects.create(workspace=workspace, member=orang, role=15, is_active=True)
    return workspace, aku, budi, citra


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _buat_kanal(client, slug, nama, tipe="kanal"):
    return client.post(f"/api/workspaces/{slug}/chat/ruang/", {"nama": nama, "tipe": tipe}, format="json")


# --------------------------------------------------------------------------
# Pembuatan
# --------------------------------------------------------------------------


def test_pembuat_kanal_langsung_jadi_anggota(kantor):
    """Kanal tanpa anggota tidak muncul di daftar percakapan siapa pun, termasuk
    yang membuatnya, dan dari luar itu terlihat seperti pembuatan yang gagal."""
    workspace, aku, _, _ = kantor
    r = _buat_kanal(_klien(aku), workspace.slug, "umum")

    assert r.status_code == 201
    ruang = Ruang.objects.get(id=r.data["id"])
    assert Langganan.objects.filter(ruang=ruang, user=aku).exists()


def test_nama_kanal_wajib_dan_dibatasi(kantor):
    workspace, aku, _, _ = kantor
    client = _klien(aku)

    assert _buat_kanal(client, workspace.slug, "   ").status_code == 400
    assert _buat_kanal(client, workspace.slug, "x" * 81).status_code == 400


def test_nama_kembar_ditolak_tanpa_peduli_besar_kecil_huruf(kantor):
    """"Umum" dan "umum" sama saja bagi yang membacanya, dan dua kanal bernama
    sama membuat orang menulis di tempat yang salah."""
    workspace, aku, budi, _ = kantor
    assert _buat_kanal(_klien(aku), workspace.slug, "Umum").status_code == 201
    assert _buat_kanal(_klien(budi), workspace.slug, "umum").status_code == 400


def test_dm_tidak_bisa_dibuat_lewat_endpoint_kanal(kantor):
    """DM lahir sendiri saat percakapan dibuka. Jalur kedua berarti ada cara
    membuat DM tanpa kunci_dm yang benar, dan ruang itu tidak akan pernah
    ditemukan lagi oleh siapa pun."""
    workspace, aku, _, _ = kantor
    assert _buat_kanal(_klien(aku), workspace.slug, "selundupan", tipe="dm").status_code == 400


# --------------------------------------------------------------------------
# Siapa melihat apa
# --------------------------------------------------------------------------


def test_kanal_publik_terlihat_semua_orang_privat_tidak(kantor):
    """Menampilkan NAMA kanal privat saja sudah membocorkan bahwa ada obrolan
    tertutup soal sesuatu."""
    workspace, aku, budi, _ = kantor
    _buat_kanal(_klien(aku), workspace.slug, "kabar-baik", tipe="kanal")
    _buat_kanal(_klien(aku), workspace.slug, "gaji", tipe="privat")

    terlihat = _klien(budi).get(f"/api/workspaces/{workspace.slug}/chat/ruang/")
    nama = [x["nama"] for x in terlihat.data]

    assert "kabar-baik" in nama
    assert "gaji" not in nama


def test_bukan_anggota_tidak_bisa_membaca_isi_kanal_publik(kantor):
    """Kanal publik pun tetap butuh berlangganan. Pengecualian "publik boleh
    dibaca tanpa gabung" berarti dua definisi hak baca yang harus dijaga
    sinkron selamanya, dan yang satu pasti ketinggalan."""
    workspace, aku, budi, _ = kantor
    ruang_id = _buat_kanal(_klien(aku), workspace.slug, "pengumuman").data["id"]

    r = _klien(budi).get(f"/api/workspaces/{workspace.slug}/chat/ruang/{ruang_id}/")
    assert r.status_code == 404


def test_bukan_anggota_tidak_bisa_menulis_ke_kanal(kantor):
    workspace, aku, budi, _ = kantor
    ruang_id = _buat_kanal(_klien(aku), workspace.slug, "rapat").data["id"]

    r = _klien(budi).post(
        f"/api/workspaces/{workspace.slug}/chat/ruang/{ruang_id}/", {"isi": "menyelinap"}, format="json"
    )
    assert r.status_code == 404


# --------------------------------------------------------------------------
# Gabung dan keluar
# --------------------------------------------------------------------------


def test_gabung_kanal_publik_lalu_bisa_membaca(kantor):
    workspace, aku, budi, _ = kantor
    slug = workspace.slug
    ruang_id = _buat_kanal(_klien(aku), slug, "harian").data["id"]
    _klien(aku).post(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/", {"isi": "selamat pagi"}, format="json")

    budi_client = _klien(budi)
    assert budi_client.post(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/gabung/").status_code == 201

    isi = budi_client.get(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/")
    assert isi.status_code == 200
    assert [p["isi"] for p in isi.data] == ["selamat pagi"]


def test_kanal_privat_tidak_bisa_dimasuki_sendiri(kantor):
    """Kalau bisa, satu id kanal privat yang bocor sekali cukup untuk membaca
    seluruh isinya."""
    workspace, aku, budi, _ = kantor
    ruang_id = _buat_kanal(_klien(aku), workspace.slug, "direksi", tipe="privat").data["id"]

    r = _klien(budi).post(f"/api/workspaces/{workspace.slug}/chat/ruang/{ruang_id}/gabung/")
    assert r.status_code == 403


def test_anggota_bisa_menambahkan_orang_ke_kanal_privat(kantor):
    workspace, aku, budi, citra = kantor
    slug = workspace.slug
    ruang_id = _buat_kanal(_klien(aku), slug, "hrd", tipe="privat").data["id"]

    r = _klien(aku).post(
        f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/anggota/", {"user": str(budi.id)}, format="json"
    )
    assert r.status_code == 201
    assert _klien(budi).get(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/").status_code == 200

    # Citra masih di luar, dan yang di luar tidak bisa mengundang siapa pun.
    r = _klien(citra).post(
        f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/anggota/", {"user": str(citra.id)}, format="json"
    )
    assert r.status_code == 404


def test_orang_luar_workspace_tidak_bisa_ditambahkan(kantor):
    """Diperiksa di server, bukan cuma di UI: tanpa ini id siapa pun yang ditebak
    bisa dimasukkan ke kanal, termasuk orang dari workspace lain di instance
    yang sama."""
    workspace, aku, _, _ = kantor
    luar = _orang("kanal-luar")
    ruang_id = _buat_kanal(_klien(aku), workspace.slug, "internal", tipe="privat").data["id"]

    r = _klien(aku).post(
        f"/api/workspaces/{workspace.slug}/chat/ruang/{ruang_id}/anggota/",
        {"user": str(luar.id)},
        format="json",
    )
    assert r.status_code == 404


def test_keluar_kanal_lalu_isinya_tidak_terbaca_lagi(kantor):
    workspace, aku, budi, _ = kantor
    slug = workspace.slug
    ruang_id = _buat_kanal(_klien(aku), slug, "proyek").data["id"]

    budi_client = _klien(budi)
    budi_client.post(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/gabung/")
    assert budi_client.delete(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/gabung/").status_code == 204
    assert budi_client.get(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/").status_code == 404


def test_dm_tidak_bisa_ditinggalkan(kantor):
    workspace, aku, budi, _ = kantor
    slug = workspace.slug
    _klien(aku).post(f"/api/workspaces/{slug}/chat/{budi.id}/", {"isi": "halo"}, format="json")
    ruang = Ruang.objects.get(tipe=Ruang.Tipe.DM)

    assert _klien(aku).delete(f"/api/workspaces/{slug}/chat/ruang/{ruang.id}/gabung/").status_code == 400


# --------------------------------------------------------------------------
# Pesan kanal dan hitungannya
# --------------------------------------------------------------------------


def test_pesan_kanal_tidak_punya_penerima_tunggal(kantor):
    """Penerimanya seluruh anggota, dan itu sudah tercatat di Langganan.
    Memaksakan satu penerima berarti memilih satu orang secara sewenang-wenang."""
    workspace, aku, _, _ = kantor
    slug = workspace.slug
    ruang_id = _buat_kanal(_klien(aku), slug, "acak").data["id"]

    r = _klien(aku).post(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/", {"isi": "hai semua"}, format="json")
    assert r.status_code == 201
    assert PesanLangsung.objects.get(id=r.data["id"]).penerima_id is None


def test_lencana_belum_dibaca_ikut_menghitung_kanal(kantor):
    workspace, aku, budi, _ = kantor
    slug = workspace.slug
    ruang_id = _buat_kanal(_klien(aku), slug, "tugas").data["id"]

    budi_client = _klien(budi)
    budi_client.post(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/gabung/")
    _klien(aku).post(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/", {"isi": "tolong dicek"}, format="json")

    assert budi_client.get(f"/api/workspaces/{slug}/chat/belum-dibaca/").data["jumlah"] == 1

    # Membuka ruangnya menurunkan angka itu seketika.
    budi_client.get(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/")
    assert budi_client.get(f"/api/workspaces/{slug}/chat/belum-dibaca/").data["jumlah"] == 0


def test_kirimannya_sendiri_tidak_dihitung_belum_dibaca(kantor):
    workspace, aku, _, _ = kantor
    slug = workspace.slug
    ruang_id = _buat_kanal(_klien(aku), slug, "catatan").data["id"]
    _klien(aku).post(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/", {"isi": "buat diri sendiri"}, format="json")

    assert _klien(aku).get(f"/api/workspaces/{slug}/chat/belum-dibaca/").data["jumlah"] == 0


def test_daftar_percakapan_memuat_kanal_dan_dm(kantor):
    workspace, aku, budi, _ = kantor
    slug = workspace.slug
    aku_client = _klien(aku)

    aku_client.post(f"/api/workspaces/{slug}/chat/{budi.id}/", {"isi": "halo budi"}, format="json")
    ruang_id = _buat_kanal(aku_client, slug, "kabar").data["id"]
    aku_client.post(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/", {"isi": "ada kabar"}, format="json")

    daftar = aku_client.get(f"/api/workspaces/{slug}/chat/").data
    tipe = {x["tipe"] for x in daftar}

    assert tipe == {"dm", "kanal"}
    # DM tetap membawa lawan_bicara supaya peramban lama tidak perlu tahu
    # apa pun tentang ruang untuk membuka percakapan.
    dm = next(x for x in daftar if x["tipe"] == "dm")
    assert dm["lawan_bicara"] == str(budi.id)


# --------------------------------------------------------------------------
# Pencarian
# --------------------------------------------------------------------------


def test_pencarian_menjangkau_kanal_yang_diikuti(kantor):
    workspace, aku, budi, _ = kantor
    slug = workspace.slug
    ruang_id = _buat_kanal(_klien(aku), slug, "arsip").data["id"]

    budi_client = _klien(budi)
    budi_client.post(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/gabung/")
    _klien(aku).post(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/", {"isi": "nomor faktur 991"}, format="json")

    hasil = budi_client.get(f"/api/workspaces/{slug}/chat/cari/?q=faktur").data
    assert len(hasil) == 1
    assert hasil[0]["ruang"] == ruang_id


def test_pencarian_tidak_menembus_kanal_yang_tidak_diikuti(kantor):
    """Kalau saringan ini lepas, satu kata cukup untuk membaca cuplikan kanal
    tertutup mana pun tanpa gejala apa pun di layar."""
    workspace, aku, budi, _ = kantor
    slug = workspace.slug
    ruang_id = _buat_kanal(_klien(aku), slug, "rahasia-direksi", tipe="privat").data["id"]
    _klien(aku).post(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/", {"isi": "bonus tahunan cair"}, format="json")

    assert _klien(budi).get(f"/api/workspaces/{slug}/chat/cari/?q=bonus").data == []


# --------------------------------------------------------------------------
# Jalur DM lewat id ruang
# --------------------------------------------------------------------------


def test_dm_bisa_dibuka_lewat_id_ruang_maupun_id_orang(kantor):
    """Dua pintu masuk, satu mesin. Kalau keduanya menyimpang, salah satunya
    akan menampilkan percakapan yang berbeda untuk orang yang sama."""
    workspace, aku, budi, _ = kantor
    slug = workspace.slug
    _klien(aku).post(f"/api/workspaces/{slug}/chat/{budi.id}/", {"isi": "lewat mana saja"}, format="json")
    ruang = Ruang.objects.get(tipe=Ruang.Tipe.DM)

    lewat_orang = _klien(aku).get(f"/api/workspaces/{slug}/chat/{budi.id}/").data
    lewat_ruang = _klien(aku).get(f"/api/workspaces/{slug}/chat/ruang/{ruang.id}/").data

    assert [p["id"] for p in lewat_orang] == [p["id"] for p in lewat_ruang]


def test_anonim_ditolak_di_semua_rute_kanal(kantor):
    workspace, aku, _, _ = kantor
    slug = workspace.slug
    ruang_id = _buat_kanal(_klien(aku), slug, "publik").data["id"]

    anon = APIClient()
    assert anon.get(f"/api/workspaces/{slug}/chat/ruang/").status_code in (401, 403)
    assert anon.get(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/").status_code in (401, 403)
    assert anon.post(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/gabung/").status_code in (401, 403)
    assert anon.get(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/anggota/").status_code in (401, 403)
