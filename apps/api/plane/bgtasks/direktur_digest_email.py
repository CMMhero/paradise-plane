# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: isi laporan harian direktur
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Merender laporan direktur. Murni, tanpa I/O (data dari `direktur_digest_task`).

Keputusan user 2026-11-02: direktur hanya menerima email penting dan ikhtisar
dari manager/supervisor, BUKAN rincian staf. Karena itu laporan ini hanya berisi
ANGKA per divisi (dengan nama manager) dan per departemen (dengan nama
supervisor). Tidak ada judul tugas dan tidak ada nama staf: rincian per tugas
sudah ada di ringkasan harian manager dan supervisor masing-masing.
"""

from dataclasses import dataclass, field

from django.utils.html import escape

from plane.bgtasks.deadline_reminder_email import KANTOR, PRODUK, tanggal_id

MERAH, JINGGA, HIJAU, GELAP, ABU = "#b91c1c", "#b45309", "#15803d", "#1f2937", "#6b7280"
# Terlambat lebih dari ini = macet, bukan sekadar telat sehari.
HARI_MACET = 7
# "Perlu perhatian" cukup beberapa unit teratas, bukan daftar kedua.
BATAS_PERHATIAN = 3



@dataclass
class Angka:
    selesai: int = 0
    lewat: int = 0
    macet: int = 0  # bagian dari `lewat` yang terlambat > HARI_MACET hari
    hari: int = 0
    depan: int = 0

    def tambah(self, lain: "Angka") -> None:
        self.selesai += lain.selesai
        self.lewat += lain.lewat
        self.macet += lain.macet
        self.hari += lain.hari
        self.depan += lain.depan

    def __bool__(self):
        return bool(self.selesai or self.lewat or self.hari or self.depan)


@dataclass
class Unit:
    """Satu departemen (atau project, kalau struktur belum diisi)."""

    nama: str
    pimpinan: list = field(default_factory=list)  # nama supervisor
    angka: Angka = field(default_factory=Angka)


@dataclass
class DivisiLaporan:
    nama: str
    pimpinan: list = field(default_factory=list)  # nama manager
    unit: list = field(default_factory=list)  # [Unit]

    @property
    def angka(self) -> Angka:
        total = Angka()
        for u in self.unit:
            total.tambah(u.angka)
        return total


@dataclass
class Laporan:
    divisi: list  # [DivisiLaporan]
    jendela: str  # "24 jam terakhir" / "Jumat sore s.d. Minggu"

    @property
    def angka(self) -> Angka:
        total = Angka()
        for d in self.divisi:
            total.tambah(d.angka)
        return total

    def __bool__(self):
        return bool(self.angka)

    def perlu_perhatian(self):
        """[(divisi, unit)] dengan terlambat, yang paling macet di atas."""
        calon = [(d, u) for d in self.divisi for u in d.unit if u.angka.lewat]
        calon.sort(key=lambda du: (-du[1].angka.macet, -du[1].angka.lewat, du[0].nama, du[1].nama))
        return calon[:BATAS_PERHATIAN]


def _orang(nama, peran) -> str:
    return f"{peran} {', '.join(nama)}" if nama else f"{peran} belum diisi"


def _ket_unit(divisi, unit) -> str:
    a = unit.angka
    macet = f", {a.macet} di antaranya lebih dari {HARI_MACET} hari" if a.macet else ""
    return f"{unit.nama} ({divisi.nama}, {_orang(unit.pimpinan, 'spv')}): {a.lewat} terlambat{macet}"


# ---------------------------------------------------------------- teks


def _teks(penerima, laporan, hari_ini, tautan):
    a = laporan.angka
    sapaan = getattr(penerima, "display_name", "") or getattr(penerima, "first_name", "") or ""
    baris = [
        f"Halo {sapaan},".strip(),
        "",
        f"Laporan direktur, {tanggal_id(hari_ini, pendek=True)}.",
        "",
        f"  Selesai ({laporan.jendela}) : {a.selesai}",
        f"  Terlambat                    : {a.lewat} ({a.macet} lebih dari {HARI_MACET} hari)",
        f"  Jatuh tempo hari ini         : {a.hari}",
        f"  Jatuh tempo 7 hari ke depan  : {a.depan}",
        "",
    ]
    perhatian = laporan.perlu_perhatian()
    if perhatian:
        baris += ["PERLU PERHATIAN"] + [f"  - {_ket_unit(d, u)}" for d, u in perhatian] + [""]
    baris += ["PER DIVISI (selesai / terlambat / hari ini / 7 hari)", ""]
    for d in laporan.divisi:
        x = d.angka
        baris.append(f"{d.nama} - {_orang(d.pimpinan, 'Manager')}: {x.selesai} / {x.lewat} / {x.hari} / {x.depan}")
        for u in d.unit:
            y = u.angka
            baris.append(f"    {u.nama} - {_orang(u.pimpinan, 'spv')}: {y.selesai} / {y.lewat} / {y.hari} / {y.depan}")
        baris.append("")
    baris.append("Rincian per tugas ada di ringkasan harian manager dan supervisor masing-masing.")
    if tautan:
        baris += ["", f"Buka: {tautan}"]
    baris += ["", f"Email otomatis dari {PRODUK}. Tidak perlu dibalas."]
    return "\n".join(baris)


# ---------------------------------------------------------------- html


def _ubin(label, nilai, warna, catatan=""):
    kecil = f'<div style="color:{ABU};font-size:11px">{escape(catatan)}</div>' if catatan else ""
    return (
        f'<td style="padding:10px 12px;border:1px solid #e5e7eb;border-radius:6px;width:25%;vertical-align:top">'
        f'<div style="color:{ABU};font-size:12px">{escape(label)}</div>'
        f'<div style="font-size:24px;font-weight:bold;color:{warna}">{nilai}</div>{kecil}</td>'
    )


def _sel(nilai, warna=GELAP, tebal=False):
    gaya = f"padding:5px 8px;text-align:right;color:{warna if nilai else '#d1d5db'}"
    return f'<td style="{gaya}{";font-weight:bold" if tebal else ""}">{nilai}</td>'


def _baris_angka(a, tebal=False):
    return (
        _sel(a.selesai, HIJAU, tebal) + _sel(a.lewat, MERAH, tebal) + _sel(a.hari, JINGGA, tebal) + _sel(a.depan, GELAP, tebal)
    )


def _html(penerima, laporan, hari_ini, tautan):
    a = laporan.angka
    sapaan = getattr(penerima, "display_name", "") or getattr(penerima, "first_name", "") or ""
    ubin = (
        '<table style="border-collapse:separate;border-spacing:6px;width:100%;margin:8px -6px"><tr>'
        + _ubin("Selesai", a.selesai, HIJAU, laporan.jendela)
        + _ubin("Terlambat", a.lewat, MERAH, f"{a.macet} lebih dari {HARI_MACET} hari" if a.macet else "")
        + _ubin("Jatuh tempo hari ini", a.hari, JINGGA)
        + _ubin("7 hari ke depan", a.depan, GELAP)
        + "</tr></table>"
    )
    perhatian = laporan.perlu_perhatian()
    blok_perhatian = (
        f'<div style="background:#fef2f2;border-left:3px solid {MERAH};padding:8px 12px;margin:16px 0;font-size:13px">'
        f'<strong style="color:{MERAH}">Perlu perhatian</strong><ul style="margin:6px 0 0;padding-left:18px">'
        + "".join(f"<li>{escape(_ket_unit(d, u))}</li>" for d, u in perhatian)
        + "</ul></div>"
        if perhatian
        else ""
    )
    th = f"padding:5px 8px;text-align:right;color:{ABU};font-weight:normal;font-size:12px"
    kepala = (
        f'<tr><th style="padding:5px 8px 5px 0;text-align:left;color:{ABU};font-weight:normal;font-size:12px">'
        f'Divisi / departemen</th><th style="{th}">Selesai</th><th style="{th}">Terlambat</th>'
        f'<th style="{th}">Hari ini</th><th style="{th}">7 hari</th></tr>'
    )
    isi = ""
    for d in laporan.divisi:
        isi += (
            f'<tr style="background:#f3f4f6"><td style="padding:6px 8px 6px 4px"><strong>{escape(d.nama)}</strong>'
            f'<br><span style="color:{ABU};font-size:11px">{escape(_orang(d.pimpinan, "Manager"))}</span></td>'
            f"{_baris_angka(d.angka, tebal=True)}</tr>"
        )
        for u in d.unit:
            isi += (
                f'<tr><td style="padding:5px 8px 5px 18px">{escape(u.nama)}'
                f'<br><span style="color:{ABU};font-size:11px">{escape(_orang(u.pimpinan, "spv"))}</span></td>'
                f"{_baris_angka(u.angka)}</tr>"
            )
    tombol = (
        f'<p><a href="{escape(tautan)}" style="background:{GELAP};color:#fff;padding:8px 16px;border-radius:4px;'
        f'text-decoration:none;display:inline-block">Buka {PRODUK}</a></p>'
        if tautan
        else ""
    )
    return (
        f'<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:{GELAP};max-width:640px">'
        f"<p>Halo {escape(sapaan)},</p><p>Laporan direktur, <strong>{tanggal_id(hari_ini, pendek=True)}</strong></p>"
        + ubin
        + blok_perhatian
        + f'<h3 style="margin:20px 0 4px;font-size:15px;border-bottom:1px solid #e5e7eb;padding-bottom:4px">'
        f"Per divisi</h3>"
        f'<table style="border-collapse:collapse;font-size:13px;width:100%">{kepala}{isi}</table>'
        f'<p style="color:{ABU};font-size:12px;margin-top:12px">Rincian per tugas ada di ringkasan harian '
        f"manager dan supervisor masing-masing.</p>"
        + tombol
        + f'<p style="color:#9ca3af;font-size:11px;margin-top:24px">Email otomatis dari {PRODUK}, sistem internal '
        f"{KANTOR}. Tidak perlu dibalas.</p></div>"
    )


def susun_email(penerima, laporan, hari_ini, tautan=""):
    """(subjek, teks, html) untuk satu direktur."""
    a = laporan.angka
    subjek = f"[Laporan direktur] {tanggal_id(hari_ini, pendek=True)}: {a.lewat} terlambat, {a.hari} jatuh tempo hari ini, {a.selesai} selesai"
    return subjek, _teks(penerima, laporan, hari_ini, tautan), _html(penerima, laporan, hari_ini, tautan)
