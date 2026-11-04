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

Bahasa (3 Nov 2026): `susun_email(..., bahasa="en")`; bawaan Indonesia.
"""

import re
from dataclasses import dataclass, field

from plane.bgtasks.daily_digest_email import HARI_KE_DEPAN, durasi_hari
from plane.utils.email_merek import (
    MEREK,
    WARNA,
    bungkus,
    catatan_kecil,
    judul_bagian,
    judul_html,
    kotak,
    sapaan_html,
    tabel_angka,
    tanggal,
    terjemah_data,
    tombol,
    ubin_angka,
    url_preferensi,
)

MERAH, JINGGA, HIJAU, GELAP, ABU = WARNA["bahaya"], WARNA["peringatan"], WARNA["sukses"], WARNA["teks"], WARNA["teks_3"]
# Terlambat lebih dari ini = macet, bukan sekadar telat sehari. Bawaan God Mode
# STUCK_AFTER_DAYS; nilai yang berlaku dibawa `Laporan.hari_macet`.
HARI_MACET = 7
# "Perlu perhatian" cukup beberapa unit teratas, bukan daftar kedua.
BATAS_PERHATIAN = 3

T = {
    "id": {
        "subjek": "[Laporan direktur] {tgl}: {lewat} terlambat, {hari} jatuh tempo hari ini, {selesai} selesai",
        "sapaan": "Halo {nama},",
        "judul": "Laporan direktur, {tgl}",
        "selesai": "Selesai",
        "terlambat": "Terlambat",
        "hari": "Jatuh tempo hari ini",
        "depan": "{d} ke depan",
        "depan_pendek": "{d}",
        "hari_pendek": "Hari ini",
        "macet": "{n} lebih dari {h} hari",
        "macet_unit": ", {n} di antaranya lebih dari {h} hari",
        "unit": "{unit} ({divisi}, {orang}): {lewat} terlambat{macet}",
        "belum_diisi": "{peran} belum diisi",
        "perhatian": "Perlu perhatian",
        "per_divisi": "Per divisi",
        "per_divisi_teks": "PER DIVISI (selesai / terlambat / hari ini / {d})",
        "kolom": "Divisi / departemen",
        "rincian": "Rincian per tugas ada di ringkasan harian manager dan supervisor masing-masing.",
        "tombol": "Buka {merek}",
        "buka": "Buka: {url}",
        "alasan": "Anda menerima laporan ini karena Anda direktur di workspace ini.",
        "baris_selesai": "  Selesai ({jendela}) : {n}",
        "baris_terlambat": "  Terlambat                    : {n} ({macet} lebih dari {h} hari)",
        "baris_hari": "  Jatuh tempo hari ini         : {n}",
        "baris_depan": "  Jatuh tempo {d} ke depan  : {n}",
    },
    "en": {
        "subjek": "[Director report] {tgl}: {lewat} overdue, {hari} due today, {selesai} done",
        "sapaan": "Hi {nama},",
        "judul": "Director report, {tgl}",
        "selesai": "Done",
        "terlambat": "Overdue",
        "hari": "Due today",
        "depan": "Next {d}",
        "depan_pendek": "{d}",
        "hari_pendek": "Today",
        "macet": "{n} more than {h} days",
        "macet_unit": ", {n} of them more than {h} days",
        "unit": "{unit} ({divisi}, {orang}): {lewat} overdue{macet}",
        "belum_diisi": "{peran} not set",
        "perhatian": "Needs attention",
        "per_divisi": "By division",
        "per_divisi_teks": "BY DIVISION (done / overdue / today / {d})",
        "kolom": "Division / department",
        "rincian": "Per-task details are in each manager's and supervisor's daily summary.",
        "tombol": "Open {merek}",
        "buka": "Open: {url}",
        "alasan": "You received this report because you are a director in this workspace.",
        "baris_selesai": "  Done ({jendela}) : {n}",
        "baris_terlambat": "  Overdue                : {n} ({macet} more than {h} days)",
        "baris_hari": "  Due today              : {n}",
        "baris_depan": "  Due in the next {d} : {n}",
    },
}


def _t(bahasa):
    return T.get(bahasa, T["id"])


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
    jendela: str  # "24 jam terakhir" / "Jumat s.d. Minggu" / "N hari terakhir"
    hari_macet: int = HARI_MACET  # God Mode STUCK_AFTER_DAYS
    hari_ke_depan: int = HARI_KE_DEPAN  # God Mode DIGEST_LOOKAHEAD_DAYS

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


def _orang(nama, peran, bahasa="id") -> str:
    return f"{peran} {', '.join(nama)}" if nama else _t(bahasa)["belum_diisi"].format(peran=peran)


def _jendela(teks, bahasa="id") -> str:
    """Label jendela "selesai". "N hari terakhir" (DIGEST_WEEKDAYS bukan Senin-Jumat) ikut diterjemahkan."""
    cocok = re.fullmatch(r"(\d+) hari terakhir", teks or "")
    if cocok and bahasa == "en":
        return f"last {cocok.group(1)} days"
    return terjemah_data(teks, bahasa)


def _ket_unit(divisi, unit, bahasa="id", h=HARI_MACET) -> str:
    s = _t(bahasa)
    a = unit.angka
    macet = s["macet_unit"].format(n=a.macet, h=h) if a.macet else ""
    return s["unit"].format(
        unit=unit.nama, divisi=divisi.nama, orang=_orang(unit.pimpinan, "spv", bahasa), lewat=a.lewat, macet=macet
    )


def _sapaan(penerima, s):
    nama = getattr(penerima, "display_name", "") or getattr(penerima, "first_name", "") or ""
    return s["sapaan"].format(nama=nama).replace(" ,", ",")


def _teks(penerima, laporan, hari_ini, tautan, bahasa="id"):
    s = _t(bahasa)
    a = laporan.angka
    baris = [
        _sapaan(penerima, s),
        "",
        s["judul"].format(tgl=tanggal(hari_ini, bahasa, pendek=True)) + ".",
        "",
        s["baris_selesai"].format(jendela=_jendela(laporan.jendela, bahasa), n=a.selesai),
        s["baris_terlambat"].format(n=a.lewat, macet=a.macet, h=laporan.hari_macet),
        s["baris_hari"].format(n=a.hari),
        s["baris_depan"].format(n=a.depan, d=durasi_hari(laporan.hari_ke_depan, bahasa)),
        "",
    ]
    perhatian = laporan.perlu_perhatian()
    if perhatian:
        butir = [f"  - {_ket_unit(d, u, bahasa, laporan.hari_macet)}" for d, u in perhatian]
        baris += [s["perhatian"].upper()] + butir + [""]
    baris += [s["per_divisi_teks"].format(d=durasi_hari(laporan.hari_ke_depan, bahasa)), ""]
    for d in laporan.divisi:
        x = d.angka
        baris.append(f"{d.nama} - {_orang(d.pimpinan, 'Manager', bahasa)}: {x.selesai} / {x.lewat} / {x.hari} / {x.depan}")
        for u in d.unit:
            y = u.angka
            baris.append(
                f"    {u.nama} - {_orang(u.pimpinan, 'spv', bahasa)}: {y.selesai} / {y.lewat} / {y.hari} / {y.depan}"
            )
        baris.append("")
    baris.append(s["rincian"])
    if tautan:
        baris += ["", s["buka"].format(url=tautan)]
    return "\n".join(baris)


def _angka(a):
    return [a.selesai, a.lewat, a.hari, a.depan]


def _html_isi(penerima, laporan, hari_ini, tautan, bahasa="id"):
    s = _t(bahasa)
    a = laporan.angka
    ubin = ubin_angka(
        [
            (s["selesai"], a.selesai, HIJAU, _jendela(laporan.jendela, bahasa)),
            (s["terlambat"], a.lewat, MERAH, s["macet"].format(n=a.macet, h=laporan.hari_macet) if a.macet else ""),
            (s["hari"], a.hari, JINGGA, ""),
            (s["depan"].format(d=durasi_hari(laporan.hari_ke_depan, bahasa)), a.depan, GELAP, ""),
        ]
    )
    perhatian = laporan.perlu_perhatian()
    # Butir, bukan teks bergaris baru: Outlook klasik merapatkan "- a\n- b" jadi satu baris.
    blok_perhatian = (
        kotak(
            judul=s["perhatian"],
            nada="bahaya",
            butir=[_ket_unit(d, u, bahasa, laporan.hari_macet) for d, u in perhatian],
        )
        if perhatian
        else ""
    )
    kolom = [
        (s["selesai"], HIJAU),
        (s["terlambat"], MERAH),
        (s["hari_pendek"], JINGGA),
        (s["depan_pendek"].format(d=durasi_hari(laporan.hari_ke_depan, bahasa)), GELAP),
    ]
    baris = []
    for d in laporan.divisi:
        manager = _orang(d.pimpinan, "Manager", bahasa)
        baris.append({"nama": d.nama, "sub": manager, "angka": _angka(d.angka), "grup": True})
        baris += [
            {"nama": u.nama, "sub": _orang(u.pimpinan, "spv", bahasa), "angka": _angka(u.angka), "menjorok": True}
            for u in d.unit
        ]
    return (
        judul_html(s["judul"].format(tgl=tanggal(hari_ini, bahasa, pendek=True)))
        + sapaan_html(_sapaan(penerima, s))
        + ubin
        + blok_perhatian
        + judul_bagian(s["per_divisi"])
        + tabel_angka(s["kolom"], kolom, baris)
        + catatan_kecil(s["rincian"])
        + tombol(s["tombol"].format(merek=MEREK), tautan)
    )


def susun_email(penerima, laporan, hari_ini, tautan="", bahasa="id"):
    """(subjek, teks, html) untuk satu direktur."""
    s = _t(bahasa)
    a = laporan.angka
    subjek = s["subjek"].format(
        tgl=tanggal(hari_ini, bahasa, pendek=True), lewat=a.lewat, hari=a.hari, selesai=a.selesai
    )
    slug = tautan.rstrip("/").rsplit("/", 1)[-1] if tautan else ""
    html = bungkus(
        _html_isi(penerima, laporan, hari_ini, tautan, bahasa),
        bahasa=bahasa,
        judul=subjek,
        pratajuk=subjek,
        alasan=s["alasan"],
        url_preferensi=url_preferensi(slug) if slug else "",
        email_penerima=getattr(penerima, "email", ""),
    )
    return subjek, _teks(penerima, laporan, hari_ini, tautan, bahasa), html
