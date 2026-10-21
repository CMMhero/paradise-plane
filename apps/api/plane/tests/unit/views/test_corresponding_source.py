# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Uji untuk endpoint tawaran kode sumber, ``/source/``.

AGPL-3.0 pasal 13 mewajibkan setiap pengguna yang mengakses perangkat lunak ini
lewat jaringan ditawari Corresponding Source versi yang sedang berjalan. Yang
diuji di sini bukan sekadar "berkasnya terkirim", melainkan dua perilaku yang
menentukan sah atau tidaknya tawaran itu:

1. Saat arsipnya TIDAK ADA, jawabannya harus 503 beserta penjelasan, bukan 404
   kosong. Deployment tanpa arsip berarti TIDAK patuh, dan 404 menyembunyikan
   fakta itu dari orang yang justru berhak menerimanya.
2. Endpoint ini tidak boleh menuntut autentikasi. Kewajibannya melekat pada
   semua pengguna yang berinteraksi lewat jaringan, termasuk yang belum masuk.
"""

import pytest

from django.test import RequestFactory

from plane.web import views as web_views


@pytest.fixture
def request_polos():
    """Permintaan GET tanpa pengguna sama sekali, meniru pengunjung anonim."""
    return RequestFactory().get("/source/")


def test_menjawab_503_dan_menjelaskan_saat_arsip_tidak_ada(request_polos, monkeypatch, tmp_path):
    monkeypatch.setattr(
        web_views, "CORRESPONDING_SOURCE_PATH", str(tmp_path / "tidak-ada.tar.gz")
    )

    response = web_views.corresponding_source(request_polos)

    assert response.status_code == 503, "arsip hilang berarti deployment tidak patuh, katakan apa adanya"
    isi = response.content.decode("utf-8")
    assert "AGPL-3.0" in isi, "pengguna harus diberi tahu lisensinya, bukan galat buntu"
    assert "administrator" in isi, "beri tahu ke siapa harus melapor supaya keadaannya bisa diperbaiki"


# `django_db` di sini BUKAN karena ujinya menyentuh database. Ia tidak.
#
# `response.close()` di akhir memancarkan sinyal `request_finished`, dan Django
# menyambungkan `close_old_connections` ke sinyal itu. Kalau ada uji lain yang
# sudah membuka koneksi lebih dulu di sesi yang sama, penutupan itu memanggil
# `get_autocommit()` lalu `ensure_connection()`, dan pytest-django memblokirnya
# dengan "Database access not allowed".
#
# Akibatnya uji ini LOLOS saat dijalankan sendirian dan GAGAL saat dijalankan
# bersama suite penuh, yaitu bentuk kegagalan yang paling membuang waktu orang.
# Jangan hapus tanda ini karena "ujinya tidak pakai database".
@pytest.mark.django_db
def test_mengirim_arsip_sebagai_lampiran_saat_tersedia(request_polos, monkeypatch, tmp_path):
    arsip = tmp_path / "corresponding-source.tar.gz"
    arsip.write_bytes(b"\x1f\x8b\x08\x00bukan-arsip-sungguhan")
    monkeypatch.setattr(web_views, "CORRESPONDING_SOURCE_PATH", str(arsip))

    response = web_views.corresponding_source(request_polos)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/gzip"
    assert "attachment" in response["Content-Disposition"], (
        "harus terunduh, bukan tampil sebagai teks kacau di peramban"
    )
    assert "corresponding-source.tar.gz" in response["Content-Disposition"]
    response.close()


def test_tidak_menuntut_autentikasi(request_polos, monkeypatch, tmp_path):
    """Tanpa `request.user` sama sekali, view tetap harus menjawab.

    Kalau suatu saat ada yang membungkus view ini dengan decorator login, uji ini
    yang akan gagal lebih dulu: RequestFactory sengaja tidak memasang `user`,
    jadi apa pun yang menyentuh `request.user.is_authenticated` akan meledak.
    """
    monkeypatch.setattr(
        web_views, "CORRESPONDING_SOURCE_PATH", str(tmp_path / "tidak-ada.tar.gz")
    )

    response = web_views.corresponding_source(request_polos)

    assert response.status_code == 503, "503 berarti view berjalan sampai selesai tanpa menuntut login"


def test_url_source_terdaftar_dan_menunjuk_view_ini():
    """Jaring pengaman: view sebagus apa pun tidak berguna kalau URL-nya lepas."""
    from plane.web.urls import urlpatterns

    cocok = [p for p in urlpatterns if getattr(p, "pattern", None) and str(p.pattern) == "source/"]

    assert len(cocok) == 1, "jalur source/ harus terdaftar tepat sekali di plane/web/urls.py"
    assert cocok[0].callback is web_views.corresponding_source
