# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: isi email ringkasan harian
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Merender ringkasan harian. Murni, tanpa I/O: semua data datang dari
`daily_digest_task`, jadi bentuk email bisa diuji tanpa database.

Satu email punya sampai tiga bagian, tergantung jabatan penerima:

1. **Tugas Anda**: yang di-assign ke penerima. Semua jabatan.
2. **Tugas yang Anda berikan**: yang ia buat untuk orang lain. Semua jabatan;
   kosong = tidak tampil.
3. **Tim** (supervisor: departemennya, manager: divisinya; direktur tidak, lihat
   `direktur_digest_email`). Per project: hitungan terlambat / hari ini / 7 hari, lalu daftar
   yang terlambat dan jatuh tempo hari ini beserta penanggung jawabnya. Yang 7 hari
   ke depan cukup angkanya: untuk pimpinan, yang perlu ditindak hari ini yang
   dirinci, bukan seluruh antrean.

Ada dua edisi (keputusan user 2026-11-02), masing-masing dengan saklarnya sendiri:

- **Pagi** (08.30 WIB, `daily_digest`): untuk memulai hari. Jendela depan 7 hari.
- **Sore** (17.30 WIB, `daily_digest_sore`): untuk menutup hari. Bagian "hari ini"
  memuat yang SELESAI hari ini dan yang tenggatnya hari ini tapi BELUM selesai;
  jendela depan menyempit ke hari kerja berikutnya (besok, atau sampai Senin
  kalau hari ini Jumat). Bagian yang dimuat ikut saklar SAKLAR_RINGKASAN yang sama.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from django.utils.html import escape

from plane.bgtasks.deadline_reminder_email import KANTOR, PRODUK, _base_url, tanggal_id

HARI_KE_DEPAN = 7
# Orang dengan 80 tugas terlambat butuh tahu angkanya, bukan 80 baris.
BATAS_BARIS = 15
# Per project di bagian tim. Direktur bisa melihat 30+ project sekaligus.
BATAS_BARIS_TIM = 5

MERAH, JINGGA, GELAP, ABU, HIJAU = "#b91c1c", "#b45309", "#1f2937", "#6b7280", "#15803d"

NAMA_HARI = ("Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu")


def hari_ke_hari_kerja_berikutnya(hari_ini) -> int:
    """Jarak ke hari kerja berikutnya: 1, kecuali Jumat (3) dan Sabtu (2). Untuk edisi sore."""
    return {4: 3, 5: 2}.get(hari_ini.weekday(), 1)


@dataclass
class Kelompok:
    """Tugas dalam jendela ringkasan, dipisah menurut tenggat."""

    hari: list = field(default_factory=list)
    depan: list = field(default_factory=list)
    lewat: list = field(default_factory=list)
    # Hanya edisi sore: tugas yang pindah ke grup "completed" hari ini.
    selesai: list = field(default_factory=list)

    def __bool__(self):
        return bool(self.hari or self.depan or self.lewat or self.selesai)


@dataclass
class GrupTim:
    nama: str
    tugas: Kelompok


@dataclass
class Ringkasan:
    """Isi email satu penerima di satu workspace."""

    peran: str
    cakupan: str = ""
    sendiri: Kelompok = field(default_factory=Kelompok)
    diberikan: Kelompok = field(default_factory=Kelompok)
    tim: list = field(default_factory=list)  # [GrupTim], hanya pimpinan
    judul_tim: str = "Tim Anda"
    # {issue_id: [nama penanggung jawab]} untuk bagian "diberikan" dan tim.
    penanggung: dict = field(default_factory=dict)
    # Saklar SAKLAR_RINGKASAN orangnya (kunci hilang = hidup). Dipakai subjek dan teks kosong.
    bagian: dict = field(default_factory=dict)
    # Edisi sore (`daily_digest_sore`): judul, subjek, dan jendela depan berbeda.
    sore: bool = False
    # Lebar jendela "depan" dalam hari. Pagi 7; sore sampai hari kerja berikutnya.
    hari_ke_depan: int = HARI_KE_DEPAN

    def __bool__(self):
        return bool(self.sendiri or self.diberikan or any(g.tugas for g in self.tim))


def kelompokkan(tugas, hari_ini, hari_ke_depan=HARI_KE_DEPAN):
    """Pecah tugas jadi Kelompok(hari, depan, lewat), terurut tenggat. Di luar jendela dibuang."""
    batas = hari_ini + timedelta(days=hari_ke_depan)
    hasil = Kelompok()
    for issue in sorted(tugas, key=lambda i: (i.target_date, i.sequence_id)):
        if issue.target_date < hari_ini:
            hasil.lewat.append(issue)
        elif issue.target_date == hari_ini:
            hasil.hari.append(issue)
        elif issue.target_date <= batas:
            hasil.depan.append(issue)
    return hasil


@dataclass(frozen=True)
class Label:
    """Judul bagian yang berbeda antara edisi pagi dan sore."""

    hari: str
    depan: str
    depan_pendek: str


def label_untuk(ringkasan, hari_ini) -> Label:
    if not ringkasan.sore:
        return Label("Jatuh tempo hari ini", f"Jatuh tempo {HARI_KE_DEPAN} hari ke depan", f"{HARI_KE_DEPAN} hari")
    if ringkasan.hari_ke_depan == 1:
        return Label("Belum selesai, tenggat hari ini", "Jatuh tempo besok", "Besok")
    hari = NAMA_HARI[(hari_ini + timedelta(days=ringkasan.hari_ke_depan)).weekday()]
    return Label("Belum selesai, tenggat hari ini", f"Jatuh tempo sampai {hari}", f"s.d. {hari}")


def _awal_kecil(teks):
    """Huruf pertama saja: "s.d. Senin" tetap menyebut Senin dengan huruf besar."""
    return teks[:1].lower() + teks[1:]


def _ket(issue, hari_ini):
    if getattr(getattr(issue, "state", None), "group", None) == "completed":
        return "selesai"
    if not issue.target_date:
        return "tanpa tenggat"
    selisih = (issue.target_date - hari_ini).days
    if selisih < 0:
        return f"terlambat {-selisih} hari"
    return "hari ini" if selisih == 0 else f"{selisih} hari lagi"


def _kode(issue):
    return f"{issue.project.identifier}-{issue.sequence_id}"


def _tautan(issue):
    url = _base_url()
    return f"{url}/{issue.workspace.slug}/projects/{issue.project_id}/issues/{issue.id}" if url else ""


def _nama_penanggung(issue, ringkasan):
    if ringkasan is None:
        return None
    nama = ringkasan.penanggung.get(issue.id)
    return ", ".join(nama) if nama else "belum ada penanggung jawab"


# ---------------------------------------------------------------- teks


def _baris_teks(issue, hari_ini, siapa=None):
    tambahan = f" [{siapa}]" if siapa else ""
    return f"  {_kode(issue)}  {issue.name}  ({tanggal_id(issue.target_date, pendek=True)}, {_ket(issue, hari_ini)}){tambahan}"


def _daftar_teks(judul, daftar, hari_ini, batas=BATAS_BARIS, ringkasan=None):
    if not daftar:
        return []
    baris = [f"{judul} ({len(daftar)})"]
    baris += [_baris_teks(i, hari_ini, _nama_penanggung(i, ringkasan)) for i in daftar[:batas]]
    if len(daftar) > batas:
        baris.append(f"  ... +{len(daftar) - batas} lainnya")
    return baris + [""]


def _kelompok_teks(kelompok, hari_ini, label, ringkasan=None):
    return (
        _daftar_teks("SELESAI HARI INI", kelompok.selesai, hari_ini, ringkasan=ringkasan)
        + _daftar_teks("TERLAMBAT", kelompok.lewat, hari_ini, ringkasan=ringkasan)
        + _daftar_teks(label.hari.upper(), kelompok.hari, hari_ini, ringkasan=ringkasan)
        + _daftar_teks(label.depan.upper(), kelompok.depan, hari_ini, ringkasan=ringkasan)
    )


def _tim_teks(ringkasan, hari_ini, label):
    grup = [g for g in ringkasan.tim if g.tugas]
    if not grup:
        return []
    baris = [f"== {ringkasan.judul_tim.upper()} ==", ""]
    for g in grup:
        t = g.tugas
        selesai = f"{len(t.selesai)} selesai hari ini, " if ringkasan.sore else ""
        depan = _awal_kecil(label.depan_pendek) if ringkasan.sore else f"{HARI_KE_DEPAN} hari ke depan"
        baris.append(f"{g.nama}: {selesai}{len(t.lewat)} terlambat, {len(t.hari)} hari ini, {len(t.depan)} {depan}")
        perlu = t.lewat + t.hari
        baris += [_baris_teks(i, hari_ini, _nama_penanggung(i, ringkasan)) for i in perlu[:BATAS_BARIS_TIM]]
        if len(perlu) > BATAS_BARIS_TIM:
            baris.append(f"  ... +{len(perlu) - BATAS_BARIS_TIM} lainnya")
        baris.append("")
    return baris


# ---------------------------------------------------------------- html


def _baris_html(issue, hari_ini, warna, siapa=None):
    nama = f"<strong>{escape(_kode(issue))}</strong> {escape(issue.name)}"
    tautan = _tautan(issue)
    if tautan:
        nama = f'<a href="{escape(tautan)}" style="color:{GELAP};text-decoration:none">{nama}</a>'
    if siapa:
        nama += f'<br><span style="color:{ABU};font-size:12px">{escape(siapa)}</span>'
    return (
        f'<tr><td style="padding:4px 12px 4px 0;vertical-align:top">{nama}</td>'
        f'<td style="padding:4px 0;color:{warna};white-space:nowrap;vertical-align:top">'
        f"{tanggal_id(issue.target_date, pendek=True)} ({_ket(issue, hari_ini)})</td></tr>"
    )


def _tabel_html(daftar, hari_ini, warna, batas, ringkasan=None):
    baris = [_baris_html(i, hari_ini, warna, _nama_penanggung(i, ringkasan)) for i in daftar[:batas]]
    if len(daftar) > batas:
        baris.append(f'<tr><td colspan="2" style="padding:4px 0;color:{ABU}">+{len(daftar) - batas} lainnya</td></tr>')
    return f'<table style="border-collapse:collapse;font-size:13px;width:100%">{"".join(baris)}</table>'


def _daftar_html(judul, daftar, hari_ini, warna, ringkasan=None):
    if not daftar:
        return ""
    return f'<h4 style="margin:14px 0 4px;color:{warna};font-size:13px">{judul} ({len(daftar)})</h4>' + _tabel_html(
        daftar, hari_ini, warna, BATAS_BARIS, ringkasan
    )


def _kelompok_html(judul, kelompok, hari_ini, label, ringkasan=None):
    if not kelompok:
        return ""
    return (
        f'<h3 style="margin:24px 0 4px;font-size:15px;border-bottom:1px solid #e5e7eb;padding-bottom:4px">{judul}</h3>'
        + _daftar_html("Selesai hari ini", kelompok.selesai, hari_ini, HIJAU, ringkasan)
        + _daftar_html("Terlambat", kelompok.lewat, hari_ini, MERAH, ringkasan)
        + _daftar_html(escape(label.hari), kelompok.hari, hari_ini, JINGGA, ringkasan)
        + _daftar_html(escape(label.depan), kelompok.depan, hari_ini, GELAP, ringkasan)
    )


def _tim_html(ringkasan, hari_ini, label):
    grup = [g for g in ringkasan.tim if g.tugas]
    if not grup:
        return ""
    sel = "padding:4px 8px;text-align:right"

    def kolom_selesai(g):
        return f'<td style="{sel};color:{HIJAU}">{len(g.tugas.selesai)}</td>' if ringkasan.sore else ""

    rekap = "".join(
        f'<tr><td style="padding:4px 8px 4px 0">{escape(g.nama)}</td>'
        + kolom_selesai(g)
        + f'<td style="{sel};color:{MERAH}">{len(g.tugas.lewat)}</td>'
        f'<td style="{sel};color:{JINGGA}">{len(g.tugas.hari)}</td>'
        f'<td style="{sel}">{len(g.tugas.depan)}</td></tr>'
        for g in grup
    )
    kepala = (
        f'<tr style="color:{ABU};font-size:12px"><th style="text-align:left;padding:4px 8px 4px 0">Project</th>'
        + (f'<th style="{sel}">Selesai</th>' if ringkasan.sore else "")
        + f'<th style="{sel}">Terlambat</th><th style="{sel}">Hari ini</th>'
        f'<th style="{sel}">{escape(label.depan_pendek)}</th></tr>'
    )
    rinci = ""
    for g in grup:
        perlu = g.tugas.lewat + g.tugas.hari
        if perlu:
            rinci += f'<h4 style="margin:14px 0 4px;font-size:13px">{escape(g.nama)}</h4>' + _tabel_html(
                perlu, hari_ini, MERAH, BATAS_BARIS_TIM, ringkasan
            )
    return (
        f'<h3 style="margin:24px 0 4px;font-size:15px;border-bottom:1px solid #e5e7eb;padding-bottom:4px">'
        f"{escape(ringkasan.judul_tim)}</h3>"
        f'<table style="border-collapse:collapse;font-size:13px">{kepala}{rekap}</table>{rinci}'
    )


# ---------------------------------------------------------------- email


def susun_email(penerima, ringkasan, hari_ini):
    """(subjek, teks, html) untuk satu penerima."""
    s = ringkasan.sendiri
    label = label_untuk(ringkasan, hari_ini)

    def nyala(kunci):
        return ringkasan.bagian.get(kunci, True)

    if ringkasan.sore:
        potong = [
            f"{len(s.selesai)} selesai hari ini" if nyala("digest_hari_ini") else "",
            f"{len(s.hari)} belum selesai (tenggat hari ini)" if nyala("digest_hari_ini") else "",
            f"{len(s.depan)} {_awal_kecil(label.depan_pendek)}" if nyala("digest_depan") else "",
            f"{len(s.lewat)} terlambat" if nyala("digest_terlambat") else "",
        ]
        awalan = "[Ringkasan sore] "
    else:
        potong = [
            f"{len(s.hari)} hari ini" if nyala("digest_hari_ini") else "",
            f"{len(s.depan)} 7 hari ke depan" if nyala("digest_depan") else "",
            f"{len(s.lewat)} terlambat" if nyala("digest_terlambat") else "",
        ]
        awalan = "[Ringkasan pagi] "
    subjek = awalan + (", ".join(p for p in potong if p) or "tugas Anda")
    if ringkasan.tim:
        tim_lewat = sum(len(g.tugas.lewat) for g in ringkasan.tim)
        subjek += f" · tim: {tim_lewat} terlambat"
    sapaan = penerima.display_name or penerima.first_name or ""
    peran = ringkasan.peran + (f" · {ringkasan.cakupan}" if ringkasan.cakupan else "")
    if not all(nyala(k) for k in ("digest_terlambat", "digest_hari_ini", "digest_depan")):
        kosong = "Tidak ada tugas Anda di bagian yang Anda pilih."
    elif ringkasan.sore:
        kosong = f"Tidak ada tugas Anda yang selesai hari ini, terlambat, atau {_awal_kecil(label.depan)}."
    else:
        kosong = "Tidak ada tugas Anda yang jatuh tempo dalam 7 hari ke depan."
    judul = "Ringkasan akhir hari" if ringkasan.sore else "Ringkasan tugas"

    teks = [f"Halo {sapaan},".strip(), "", f"{judul}, {tanggal_id(hari_ini)} ({peran}).", ""]
    teks += ["== TUGAS ANDA ==", ""] + (_kelompok_teks(s, hari_ini, label) or [kosong, ""])
    if ringkasan.diberikan:
        teks += ["== TUGAS YANG ANDA BERIKAN ==", ""] + _kelompok_teks(ringkasan.diberikan, hari_ini, label, ringkasan)
    teks += _tim_teks(ringkasan, hari_ini, label)
    teks.append(f"Email otomatis dari {PRODUK}. Atur di Profil > Notifikasi. Tidak perlu dibalas.")

    html = (
        f'<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:{GELAP};max-width:640px">'
        f"<p>Halo {escape(sapaan)},</p>"
        f"<p>{judul}, <strong>{tanggal_id(hari_ini)}</strong>"
        f'<br><span style="color:{ABU};font-size:12px">{escape(peran)}</span></p>'
        + (
            _kelompok_html("Tugas Anda", s, hari_ini, label)
            or f'<h3 style="font-size:15px">Tugas Anda</h3><p>{escape(kosong)}</p>'
        )
        + _kelompok_html("Tugas yang Anda berikan", ringkasan.diberikan, hari_ini, label, ringkasan)
        + _tim_html(ringkasan, hari_ini, label)
        + f'<p style="color:#9ca3af;font-size:11px;margin-top:24px">Email otomatis dari {PRODUK}, '
        f"sistem internal {KANTOR}. Atur di Profil &gt; Notifikasi. Tidak perlu dibalas.</p></div>"
    )
    return subjek, "\n".join(teks), html
