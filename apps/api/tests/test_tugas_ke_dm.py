# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji penugasan yang dikirim sebagai DM
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Isi pesan penugasan, dan siapa yang berhak menerimanya.

Dua hal yang dijaga berkas ini.

SATU, baris yang tidak terisi TIDAK ditulis. "Tenggat: -" dan "Label: -"
mengajari orang bahwa isi pesan ini tidak perlu dibaca, dan begitu pelajaran itu
diterima, tenggat yang sungguhan pun ikut terlewat.

DUA, yang dikirimi hanya penerima yang BARU ditambahkan. Payload permintaan
berisi seluruh daftar penerima setiap kali tugas disimpan, jadi saringan yang
salah akan mengirim ulang rincian yang sama kepada orang yang sudah memegang
tugas itu berminggu-minggu, tiap kali ada yang sekadar menggeser prioritasnya.

Murni, tanpa database.
"""

from datetime import date
from types import SimpleNamespace

import pytest

from plane.bgtasks.tugas_ke_dm_task import BATAS_DESKRIPSI, BATAS_JUDUL, penerima_baru, susun_pesan

pytestmark = pytest.mark.unit


def _aktivitas(field, new_identifier=None, old_identifier=None):
    return SimpleNamespace(field=field, new_identifier=new_identifier, old_identifier=old_identifier)


# --- isi pesannya ------------------------------------------------------------


def test_pesan_lengkap_memuat_semua_rincian():
    isi = susun_pesan(
        kode="IT-42",
        judul="Printer lantai 2 macet",
        nama_project="Divisi IT",
        prioritas="high",
        status="Todo",
        tenggat=date(2026, 8, 25),
        mulai=date(2026, 8, 21),
        label="hardware, mendesak",
        deskripsi="Printer tidak bisa mencetak sejak pagi.",
        tautan="https://contoh/ws/projects/p/issues/i",
    )
    assert "📋 Tugas baru untuk Anda" in isi
    assert "IT-42 · Printer lantai 2 macet" in isi
    assert "Project: Divisi IT" in isi
    assert "Prioritas: Tinggi" in isi
    assert "Status: Todo" in isi
    assert "Tenggat: 25 Agustus 2026" in isi
    assert "Mulai: 21 Agustus 2026" in isi
    assert "Label: hardware, mendesak" in isi
    assert "Deskripsi:" in isi
    assert isi.rstrip().endswith("https://contoh/ws/projects/p/issues/i")


def test_baris_yang_tidak_terisi_tidak_pernah_ditulis():
    # Ini yang paling gampang rusak: satu baris "Tenggat: -" saja sudah cukup
    # untuk mengajari orang bahwa isi pesan ini boleh dilewati.
    isi = susun_pesan(kode="IT-7", judul="Cek stok toner")
    assert "Tenggat" not in isi
    assert "Label" not in isi
    assert "Prioritas" not in isi
    assert "Deskripsi" not in isi
    # ": -" dan bukan sekadar "-": tanda pisah di kode tugas seperti IT-7 wajar.
    assert ": -" not in isi
    assert "IT-7 · Cek stok toner" in isi


def test_tugas_tanpa_kode_tetap_punya_judul():
    isi = susun_pesan(kode="", judul="Rapat mingguan")
    assert "Rapat mingguan" in isi
    assert "·" not in isi


def test_prioritas_diterjemahkan_dan_yang_asing_dibuang():
    assert "Prioritas: Mendesak" in susun_pesan(kode="A-1", judul="x", prioritas="urgent")
    assert "Prioritas: Belum diatur" in susun_pesan(kode="A-1", judul="x", prioritas="none")
    # Nilai yang tidak dikenal lebih baik hilang daripada muncul mentah sebagai
    # "Prioritas: p3" yang tidak berarti apa-apa bagi yang membacanya.
    assert "Prioritas" not in susun_pesan(kode="A-1", judul="x", prioritas="p3")


def test_deskripsi_panjang_dipotong_dan_barisnya_dirapikan():
    isi = susun_pesan(kode="A-1", judul="x", deskripsi="y" * 900)
    baris_deskripsi = isi.split("Deskripsi:\n")[1]
    assert len(baris_deskripsi) == BATAS_DESKRIPSI
    assert baris_deskripsi.endswith("…")


def test_judul_panjang_dipotong_dan_enternya_dibuang():
    # Ditemukan saat uji jalur penuh ke database, bukan dikarang: judul hasil
    # seed sepanjang 250 karakter berisi enter, dan seluruh rincian di bawahnya
    # terdorong keluar layar. Judul work item boleh sampai 255 karakter, jadi ini
    # bisa terjadi sungguhan begitu ada yang menempelkan paragraf ke kolom judul.
    isi = susun_pesan(kode="IT-9", judul="a" * 90 + "\nbaris kedua " + "b" * 200)
    baris_judul = isi.split("\n")[2]
    assert len(baris_judul) <= BATAS_JUDUL + len("IT-9 · ")
    assert baris_judul.endswith("…")
    # Enter di dalam judul tidak boleh memecah barisnya jadi dua.
    assert "\nbaris kedua" not in isi


def test_label_yang_kebanyakan_ikut_dipotong():
    isi = susun_pesan(kode="IT-9", judul="x", label=", ".join(f"label-{i}" for i in range(40)))
    baris_label = [b for b in isi.split("\n") if b.startswith("Label: ")][0]
    assert len(baris_label) <= BATAS_JUDUL + len("Label: ")


def test_deskripsi_berbaris_banyak_jadi_satu_paragraf():
    # Tanpa perapian, deskripsi bereniter membuat tautan di bawahnya terdorong
    # jauh ke luar layar ponsel.
    isi = susun_pesan(kode="A-1", judul="x", deskripsi="baris satu\n\n\nbaris dua")
    assert "baris satu baris dua" in isi


def test_tautan_kosong_tidak_meninggalkan_baris_kosong_di_ujung():
    # Kalau WEB_URL belum disetel, tautannya sengaja tidak dikarang.
    isi = susun_pesan(kode="A-1", judul="x", tautan="")
    assert isi == isi.rstrip()
    assert "http" not in isi


def test_tanggal_ditulis_panjang_bukan_angka_semua():
    # "08-09" terbaca sebagai dua tanggal berbeda tergantung siapa yang membaca.
    isi = susun_pesan(kode="A-1", judul="x", tenggat=date(2026, 1, 9))
    assert "Tenggat: 9 Januari 2026" in isi
    isi = susun_pesan(kode="A-1", judul="x", tenggat=date(2026, 12, 31))
    assert "Tenggat: 31 Desember 2026" in isi


# --- siapa yang dikirimi -----------------------------------------------------


def test_penerima_baru_diambil_dari_aktivitas_penugasan():
    assert penerima_baru([_aktivitas("assignees", new_identifier="u-1")]) == ["u-1"]


def test_penerima_yang_DILEPAS_tidak_ikut_dikirimi():
    # Pelepasan juga menghasilkan baris field="assignees", tapi id-nya ada di
    # old_identifier. Menyaring dengan field saja akan mengirimi orang yang baru
    # dicabut dari tugas sebuah pesan "Tugas baru untuk Anda".
    dilepas = _aktivitas("assignees", old_identifier="u-9")
    assert penerima_baru([dilepas]) == []


def test_perubahan_lain_tidak_memicu_pesan_apa_pun():
    lain = [
        _aktivitas("priority", new_identifier=None),
        _aktivitas("target_date", new_identifier=None),
        _aktivitas("state", new_identifier="s-1"),
        _aktivitas("labels", new_identifier="l-1"),
    ]
    assert penerima_baru(lain) == []


def test_beberapa_penerima_sekaligus():
    aktivitas = [
        _aktivitas("assignees", new_identifier="u-1"),
        _aktivitas("priority"),
        _aktivitas("assignees", new_identifier="u-2"),
        _aktivitas("assignees", old_identifier="u-3"),
    ]
    assert penerima_baru(aktivitas) == ["u-1", "u-2"]


def test_daftar_kosong_dan_None_tidak_meledak():
    assert penerima_baru([]) == []
    assert penerima_baru(None) == []
