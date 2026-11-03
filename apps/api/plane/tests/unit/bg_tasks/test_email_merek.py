# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tes tata letak email bersama
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Semua email dirender lewat tata letak bersama, dalam dua bahasa, tanpa galat.

Sumber contoh = `kirim_contoh_email`, yang memanggil fungsi `susun_*` yang sama
dengan pengirim sungguhan. Jadi tes ini gagal kalau ada email yang lupa
dipindah ke `base.html` atau ada placeholder terjemahan yang tak terisi.
"""

import re
from email import message_from_bytes
from types import SimpleNamespace as NS
from unittest import mock

import pytest
from django.core.management import CommandError, call_command

from plane.db.management.commands.kirim_contoh_email import PENERIMA_UJI, baca_eml
from plane.utils import email_merek
from plane.utils.email_merek import (
    LOGO_CID,
    MEREK,
    avatar_untuk,
    bahasa_dari_kode,
    bahasa_penerima,
    buat_pesan,
    inisial,
    tanggal,
)
from plane.utils.email_teks import KOLOM, PRIORITAS, TEKS

JUMLAH_CONTOH = 26
# Placeholder str.format yang tertinggal, mis. "{aktor}". Kurung kurawal CSS di <style>
# dibuang dulu sebelum diperiksa.
SISA_PLACEHOLDER = re.compile(r"\{[a-z_]+\}")


@pytest.fixture(scope="module")
def contoh(tmp_path_factory):
    folder = tmp_path_factory.mktemp("contoh-email")
    call_command("kirim_contoh_email", out=str(folder), stdout=open("/dev/null", "w"))  # noqa: SIM115
    return folder


@pytest.mark.unit
class TestSemuaEmailDirender:
    def test_semua_contoh_ada_dalam_dua_bahasa(self, contoh):
        html = sorted(p.name for p in contoh.glob("*.html") if p.name != "index.html")
        assert len(html) == JUMLAH_CONTOH * 2
        for bahasa in ("id", "en"):
            assert len([n for n in html if n.endswith(f"-{bahasa}.html")]) == JUMLAH_CONTOH

    @pytest.mark.parametrize("bahasa", ["id", "en"])
    def test_tiap_email_memakai_kerangka_bersama(self, contoh, bahasa):
        for berkas in contoh.glob(f"*-{bahasa}.html"):
            html = berkas.read_text(encoding="utf-8")
            nama = berkas.name
            assert f'<html lang="{bahasa}"' in html, nama
            assert MEREK in html, nama
            # Pratinjau mengganti cid: dengan data URI; logo harus ada sebagai gambar.
            assert "data:image/png;base64," in html, nama
            assert "cid:" not in html, nama
            assert 'width="600"' in html, nama
            tanpa_gaya = re.sub(r"<style.*?</style>", "", html, flags=re.S)
            assert not SISA_PLACEHOLDER.search(tanpa_gaya), (nama, SISA_PLACEHOLDER.search(tanpa_gaya).group())
            assert "None" not in tanpa_gaya, nama
            assert "—" not in tanpa_gaya, nama  # tanpa em dash

    @pytest.mark.parametrize("bahasa", ["id", "en"])
    def test_versi_teks_tidak_kosong(self, contoh, bahasa):
        for berkas in contoh.glob(f"*-{bahasa}.txt"):
            teks = berkas.read_text(encoding="utf-8").strip()
            assert len(teks) > 20, berkas.name
            assert "<td" not in teks and "<table" not in teks, berkas.name

    def test_bahasa_inggris_benar_benar_inggris(self, contoh):
        for nama in ("17-tugas-baru", "20-ringkasan-pagi-staf", "23-laporan-direktur", "18-pengingat-h3"):
            en = (contoh / f"{nama}-en.html").read_text(encoding="utf-8")
            assert "Anda" not in en and "Tenggat" not in en, nama

    def test_logo_dan_avatar_sisip_lampiran_di_luar_related(self, contoh):
        struktur = baca_eml(contoh / "17-tugas-baru-id.eml")
        assert LOGO_CID in struktur["cid"]
        assert any(c.startswith("avatar-") for c in struktur["cid"])  # foto pemberi tugas
        pesan = message_from_bytes((contoh / "17-tugas-baru-id.eml").read_bytes())
        assert pesan.get_content_type() == "multipart/mixed"
        anak = [b.get_content_type() for b in pesan.get_payload()]
        assert anak[0] == "multipart/related" and "text/calendar" in anak[1]

    def test_tanpa_lampiran_akarnya_related(self, contoh):
        pesan = message_from_bytes((contoh / "01-kode-masuk-id.eml").read_bytes())
        assert pesan.get_content_type() == "multipart/related"
        assert pesan["To"] == PENERIMA_UJI


@pytest.mark.unit
class TestPenerimaDikunci:
    def test_alamat_lain_ditolak(self, tmp_path):
        with pytest.raises(CommandError, match="hanya boleh"):
            call_command("kirim_contoh_email", out=str(tmp_path), ke="orang@lain.com", kirim=True)

    def test_huruf_besar_tetap_diterima(self, tmp_path):
        call_command(
            "kirim_contoh_email", out=str(tmp_path), ke=PENERIMA_UJI.upper(), hanya="^01", bahasa="id",
            stdout=open("/dev/null", "w"),  # noqa: SIM115
        )  # fmt: skip
        assert (tmp_path / "01-kode-masuk-id.html").exists()


@pytest.mark.unit
class TestAvatar:
    def _user(self, **lain):
        dasar = {"id": "u1", "display_name": "Budi Santoso", "first_name": "Budi", "last_name": "", "email": "b@x.id",
                 "avatar": "", "avatar_asset_id": None, "avatar_asset": None}  # fmt: skip
        return NS(**{**dasar, **lain})

    def test_tanpa_foto_jadi_inisial_bukan_url_none(self):
        av, gambar = avatar_untuk(self._user())
        assert av == {"nama": "Budi Santoso", "inisial": "BS", "src": ""} and gambar is None

    def test_foto_tersimpan_disisipkan_cid(self):
        user = self._user(avatar_asset_id="a1", avatar_asset=NS(size=10, asset=NS(name="k")))
        with mock.patch.object(email_merek, "_baca_avatar", return_value=(b"\x89PNG", "png")):
            daftar = []
            av, g = avatar_untuk(user, gambar=daftar)
            av2, g2 = avatar_untuk(user, gambar=daftar)
        assert av["src"] == f"cid:{g.cid}" and daftar == [g]
        assert av2["src"] == av["src"] and g2 is None  # foto yang sama tidak disisipkan dua kali

    def test_storage_gagal_jatuh_ke_inisial(self):
        user = self._user(avatar_asset_id="a1", avatar_asset=NS(size=10, asset=NS(name="k")))
        with mock.patch("plane.settings.storage.S3Storage", side_effect=RuntimeError("minio mati")):
            av, g = avatar_untuk(user)
        assert av["src"] == "" and g is None

    def test_foto_terlalu_besar_tidak_disisipkan(self):
        user = self._user(avatar_asset_id="a1", avatar_asset=NS(size=10_000_000, asset=NS(name="k")))
        av, _ = avatar_untuk(user)
        assert av["src"] == ""

    def test_foto_eksternal_https_dipakai_langsung(self):
        av, g = avatar_untuk(self._user(avatar="https://lh3.googleusercontent.com/a/x"))
        assert av["src"] == "https://lh3.googleusercontent.com/a/x" and g is None

    @pytest.mark.parametrize(
        "nama,hasil", [("Budi Santoso", "BS"), ("andi", "A"), ("", "?"), ("sari.dewi@x.id", "SD")]
    )
    def test_inisial(self, nama, hasil):
        assert inisial(nama) == hasil


@pytest.mark.unit
class TestBahasa:
    def test_kode_profil(self):
        assert bahasa_dari_kode("id") == "id"
        assert bahasa_dari_kode("id-ID") == "id"
        assert bahasa_dari_kode("en") == "en"
        assert bahasa_dari_kode("ja") == "en"

    def test_profil_menentukan_bahasa(self):
        assert bahasa_penerima(NS(profile=NS(language="id"))) == "id"
        assert bahasa_penerima(NS(profile=NS(language="en"))) == "en"

    def test_tanpa_profil_pakai_bawaan_god_mode(self):
        with mock.patch.object(email_merek, "bahasa_bawaan", return_value="id"):
            assert bahasa_penerima(NS(profile=None)) == "id"
        with mock.patch.object(email_merek, "bahasa_bawaan", return_value="en"):
            assert bahasa_penerima(NS()) == "en"

    def test_tanggal_tidak_ikut_locale_server(self):
        from datetime import date

        assert tanggal(date(2026, 10, 31), "id") == "31 Oktober 2026"
        assert tanggal(date(2026, 10, 31), "en", pendek=True) == "31 Oct 2026"
        assert tanggal("2026-08-05", "id", pendek=True) == "5 Agu 2026"

    def test_kamus_dua_bahasa_berkunci_sama(self):
        for grup, isi in TEKS.items():
            assert set(isi["id"]) == set(isi["en"]), grup
        assert set(KOLOM["id"]) == set(KOLOM["en"])
        assert set(PRIORITAS["id"]) == set(PRIORITAS["en"])


@pytest.mark.unit
class TestPesan:
    def test_logo_selalu_ikut(self):
        from django.core.mail import get_connection

        pesan = buat_pesan(
            ke="a@b.id", subjek="Halo\nbaris", html="<p>x</p>", teks="x",
            koneksi=get_connection("django.core.mail.backends.locmem.EmailBackend"), dari="n@b.id",
        )  # fmt: skip
        mime = message_from_bytes(pesan.message().as_bytes())
        assert mime.get_content_type() == "multipart/related"
        assert any(b.get("Content-ID") == f"<{LOGO_CID}>" for b in mime.walk())
        assert pesan.subject == "Halobaris"  # karakter kontrol dibuang
