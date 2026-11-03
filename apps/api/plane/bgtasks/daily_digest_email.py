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

Bahasa (3 Nov 2026): `susun_email(..., bahasa="en")` untuk penerima yang profilnya
berbahasa Inggris. Bawaan tetap Indonesia supaya pemanggil lama tidak berubah.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from plane.bgtasks.deadline_reminder_email import _base_url
from plane.utils.email_merek import (
    MEREK,
    RUANG,
    UKURAN,
    WARNA,
    bungkus,
    daftar_tugas,
    judul_bagian,
    judul_html,
    label_daftar,
    paragraf,
    sapaan_html,
    tabel_angka,
    tanggal,
    terjemah_data,
    tombol,
    url_preferensi,
)

HARI_KE_DEPAN = 7
# Orang dengan 80 tugas terlambat butuh tahu angkanya, bukan 80 baris.
BATAS_BARIS = 15
# Per project di bagian tim. Direktur bisa melihat 30+ project sekaligus.
BATAS_BARIS_TIM = 5

MERAH, JINGGA, GELAP, ABU, HIJAU = WARNA["bahaya"], WARNA["peringatan"], WARNA["teks"], WARNA["teks_3"], WARNA["sukses"]

NAMA_HARI = {
    "id": ("Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"),
    "en": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
}

T = {
    "id": {
        "hari_ini": "Jatuh tempo hari ini",
        "depan": "Jatuh tempo {n} hari ke depan",
        "depan_pendek": "{n} hari",
        "sore_hari": "Belum selesai, tenggat hari ini",
        "besok": "Jatuh tempo besok",
        "besok_pendek": "Besok",
        "sampai": "Jatuh tempo sampai {hari}",
        "sampai_pendek": "s.d. {hari}",
        "ket_selesai": "selesai",
        "ket_tanpa": "tanpa tenggat",
        "ket_lewat": "terlambat {n} hari",
        "ket_hari_ini": "hari ini",
        "ket_lagi": "{n} hari lagi",
        "tanpa_pj": "belum ada penanggung jawab",
        "lainnya": "+{n} lainnya",
        "selesai_hari_ini": "Selesai hari ini",
        "terlambat": "Terlambat",
        "n_selesai": "{n} selesai hari ini",
        "n_belum": "{n} belum selesai (tenggat hari ini)",
        "n_terlambat": "{n} terlambat",
        "n_hari_ini": "{n} hari ini",
        "n_depan_pagi": "{n} 7 hari ke depan",
        "awalan_sore": "[Ringkasan sore] ",
        "awalan_pagi": "[Ringkasan pagi] ",
        "subjek_kosong": "tugas Anda",
        "subjek_tim": " · tim: {n} terlambat",
        "kosong_pilihan": "Tidak ada tugas Anda di bagian yang Anda pilih.",
        "kosong_sore": "Tidak ada tugas Anda yang selesai hari ini, terlambat, atau {depan}.",
        "kosong_pagi": "Tidak ada tugas Anda yang jatuh tempo dalam 7 hari ke depan.",
        "judul_sore": "Ringkasan akhir hari",
        "judul_pagi": "Ringkasan tugas",
        "sapaan": "Halo {nama},",
        "tugas_anda": "Tugas Anda",
        "diberikan": "Tugas yang Anda berikan",
        "tim_baris": "{nama}: {selesai}{lewat} terlambat, {hari} hari ini, {depan} {label}",
        "tim_selesai": "{n} selesai hari ini, ",
        "depan_tim": "7 hari ke depan",
        "kolom_project": "Project",
        "kolom_selesai": "Selesai",
        "kolom_terlambat": "Terlambat",
        "kolom_hari": "Hari ini",
        "tombol": "Buka aplikasi",
        "alasan": "Anda menerima email ini karena ringkasan harian Anda menyala.",
        "kaki_teks": "Email otomatis dari {merek}. Atur di Profil > Notifikasi. Tidak perlu dibalas.",
    },
    "en": {
        "hari_ini": "Due today",
        "depan": "Due in the next {n} days",
        "depan_pendek": "{n} days",
        "sore_hari": "Not done, due today",
        "besok": "Due tomorrow",
        "besok_pendek": "Tomorrow",
        "sampai": "Due through {hari}",
        "sampai_pendek": "through {hari}",
        "ket_selesai": "done",
        "ket_tanpa": "no due date",
        "ket_lewat": "{n} days late",
        "ket_hari_ini": "today",
        "ket_lagi": "in {n} days",
        "tanpa_pj": "no assignee yet",
        "lainnya": "+{n} more",
        "selesai_hari_ini": "Done today",
        "terlambat": "Overdue",
        "n_selesai": "{n} done today",
        "n_belum": "{n} not done (due today)",
        "n_terlambat": "{n} overdue",
        "n_hari_ini": "{n} today",
        "n_depan_pagi": "{n} in the next 7 days",
        "awalan_sore": "[Evening summary] ",
        "awalan_pagi": "[Morning summary] ",
        "subjek_kosong": "your tasks",
        "subjek_tim": " · team: {n} overdue",
        "kosong_pilihan": "You have no tasks in the sections you chose.",
        "kosong_sore": "You have no tasks done today, overdue, or {depan}.",
        "kosong_pagi": "You have no tasks due in the next 7 days.",
        "judul_sore": "End-of-day summary",
        "judul_pagi": "Task summary",
        "sapaan": "Hi {nama},",
        "tugas_anda": "Your tasks",
        "diberikan": "Tasks you assigned",
        "tim_baris": "{nama}: {selesai}{lewat} overdue, {hari} today, {depan} {label}",
        "tim_selesai": "{n} done today, ",
        "depan_tim": "in the next 7 days",
        "kolom_project": "Project",
        "kolom_selesai": "Done",
        "kolom_terlambat": "Overdue",
        "kolom_hari": "Today",
        "tombol": "Open app",
        "alasan": "You received this email because your daily summary is turned on.",
        "kaki_teks": "Automated email from {merek}. Manage it in Profile > Notifications. No need to reply.",
    },
}


def _t(bahasa):
    return T.get(bahasa, T["id"])


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


def label_untuk(ringkasan, hari_ini, bahasa="id") -> Label:
    s = _t(bahasa)
    if not ringkasan.sore:
        return Label(s["hari_ini"], s["depan"].format(n=HARI_KE_DEPAN), s["depan_pendek"].format(n=HARI_KE_DEPAN))
    if ringkasan.hari_ke_depan == 1:
        return Label(s["sore_hari"], s["besok"], s["besok_pendek"])
    hari = NAMA_HARI.get(bahasa, NAMA_HARI["id"])[(hari_ini + timedelta(days=ringkasan.hari_ke_depan)).weekday()]
    return Label(s["sore_hari"], s["sampai"].format(hari=hari), s["sampai_pendek"].format(hari=hari))


def _awal_kecil(teks):
    """Huruf pertama saja: "s.d. Senin" tetap menyebut Senin dengan huruf besar."""
    return teks[:1].lower() + teks[1:]


def _ket(issue, hari_ini, bahasa="id"):
    s = _t(bahasa)
    if getattr(getattr(issue, "state", None), "group", None) == "completed":
        return s["ket_selesai"]
    if not issue.target_date:
        return s["ket_tanpa"]
    selisih = (issue.target_date - hari_ini).days
    if selisih < 0:
        return s["ket_lewat"].format(n=-selisih)
    return s["ket_hari_ini"] if selisih == 0 else s["ket_lagi"].format(n=selisih)


def _kode(issue):
    return f"{issue.project.identifier}-{issue.sequence_id}"


def _tautan(issue):
    url = _base_url()
    return f"{url}/{issue.workspace.slug}/projects/{issue.project_id}/issues/{issue.id}" if url else ""


def _nama_penanggung(issue, ringkasan, bahasa="id"):
    if ringkasan is None:
        return None
    nama = ringkasan.penanggung.get(issue.id)
    return ", ".join(nama) if nama else _t(bahasa)["tanpa_pj"]


# ---------------------------------------------------------------- teks


def _baris_teks(issue, hari_ini, siapa=None, bahasa="id"):
    tambahan = f" [{siapa}]" if siapa else ""
    tgl = tanggal(issue.target_date, bahasa, pendek=True)
    return f"  {_kode(issue)}  {issue.name}  ({tgl}, {_ket(issue, hari_ini, bahasa)}){tambahan}"


def _daftar_teks(judul, daftar, hari_ini, batas=BATAS_BARIS, ringkasan=None, bahasa="id"):
    if not daftar:
        return []
    baris = [f"{judul} ({len(daftar)})"]
    baris += [_baris_teks(i, hari_ini, _nama_penanggung(i, ringkasan, bahasa), bahasa) for i in daftar[:batas]]
    if len(daftar) > batas:
        baris.append("  ... " + _t(bahasa)["lainnya"].format(n=len(daftar) - batas))
    return baris + [""]


def _kelompok_teks(kelompok, hari_ini, label, ringkasan=None, bahasa="id"):
    s = _t(bahasa)
    return (
        _daftar_teks(s["selesai_hari_ini"].upper(), kelompok.selesai, hari_ini, ringkasan=ringkasan, bahasa=bahasa)
        + _daftar_teks(s["terlambat"].upper(), kelompok.lewat, hari_ini, ringkasan=ringkasan, bahasa=bahasa)
        + _daftar_teks(label.hari.upper(), kelompok.hari, hari_ini, ringkasan=ringkasan, bahasa=bahasa)
        + _daftar_teks(label.depan.upper(), kelompok.depan, hari_ini, ringkasan=ringkasan, bahasa=bahasa)
    )


def _tim_teks(ringkasan, hari_ini, label, bahasa="id"):
    s = _t(bahasa)
    grup = [g for g in ringkasan.tim if g.tugas]
    if not grup:
        return []
    baris = [f"== {terjemah_data(ringkasan.judul_tim, bahasa).upper()} ==", ""]
    for g in grup:
        t = g.tugas
        selesai = s["tim_selesai"].format(n=len(t.selesai)) if ringkasan.sore else ""
        depan = _awal_kecil(label.depan_pendek) if ringkasan.sore else s["depan_tim"]
        baris.append(
            s["tim_baris"].format(
                nama=g.nama, selesai=selesai, lewat=len(t.lewat), hari=len(t.hari), depan=len(t.depan), label=depan
            )
        )
        perlu = t.lewat + t.hari
        baris += [_baris_teks(i, hari_ini, _nama_penanggung(i, ringkasan, bahasa), bahasa) for i in perlu[:BATAS_BARIS_TIM]]
        if len(perlu) > BATAS_BARIS_TIM:
            baris.append("  ... " + s["lainnya"].format(n=len(perlu) - BATAS_BARIS_TIM))
        baris.append("")
    return baris


# ---------------------------------------------------------------- html

def _warna_ket(issue, hari_ini):
    """Warna status di kolom kanan: hijau selesai, merah terlambat, jingga hari ini."""
    if getattr(getattr(issue, "state", None), "group", None) == "completed":
        return HIJAU
    if not issue.target_date:
        return ABU
    selisih = (issue.target_date - hari_ini).days
    return MERAH if selisih < 0 else (JINGGA if selisih == 0 else ABU)


def _daftar_tugas_html(daftar, hari_ini, batas, ringkasan=None, bahasa="id"):
    """Satu daftar dua kolom (kiri tugas + penanggung jawab, kanan tanggal + status)."""
    baris = [
        {
            "kode": _kode(i),
            "judul": i.name,
            "url": _tautan(i),
            "meta": _nama_penanggung(i, ringkasan, bahasa) or "",
            "tanggal": tanggal(i.target_date, bahasa, pendek=True),
            "ket": _ket(i, hari_ini, bahasa),
            "warna": _warna_ket(i, hari_ini),
        }
        for i in daftar[:batas]
    ]
    lain = _t(bahasa)["lainnya"].format(n=len(daftar) - batas) if len(daftar) > batas else ""
    return daftar_tugas(baris, lain)


def _daftar_html(judul, daftar, hari_ini, warna, ringkasan=None, bahasa="id"):
    if not daftar:
        return ""
    return label_daftar(f"{judul} ({len(daftar)})", warna) + _daftar_tugas_html(
        daftar, hari_ini, BATAS_BARIS, ringkasan, bahasa
    )


def _kelompok_html(judul, kelompok, hari_ini, label, ringkasan=None, bahasa="id"):
    if not kelompok:
        return ""
    s = _t(bahasa)
    return (
        judul_bagian(judul)
        + _daftar_html(s["selesai_hari_ini"], kelompok.selesai, hari_ini, HIJAU, ringkasan, bahasa)
        + _daftar_html(s["terlambat"], kelompok.lewat, hari_ini, MERAH, ringkasan, bahasa)
        + _daftar_html(label.hari, kelompok.hari, hari_ini, JINGGA, ringkasan, bahasa)
        + _daftar_html(label.depan, kelompok.depan, hari_ini, GELAP, ringkasan, bahasa)
    )


def _tim_html(ringkasan, hari_ini, label, bahasa="id"):
    s = _t(bahasa)
    grup = [g for g in ringkasan.tim if g.tugas]
    if not grup:
        return ""
    kolom = ([(s["kolom_selesai"], HIJAU)] if ringkasan.sore else []) + [
        (s["kolom_terlambat"], MERAH),
        (s["kolom_hari"], JINGGA),
        (label.depan_pendek, GELAP),
    ]
    baris = [
        {
            "nama": g.nama,
            "angka": ([len(g.tugas.selesai)] if ringkasan.sore else [])
            + [len(g.tugas.lewat), len(g.tugas.hari), len(g.tugas.depan)],
        }
        for g in grup
    ]
    rinci = ""
    for g in grup:
        perlu = g.tugas.lewat + g.tugas.hari
        if perlu:
            rinci += label_daftar(g.nama, huruf_besar=False) + _daftar_tugas_html(
                perlu, hari_ini, BATAS_BARIS_TIM, ringkasan, bahasa
            )
    judul = judul_bagian(terjemah_data(ringkasan.judul_tim, bahasa))
    return judul + tabel_angka(s["kolom_project"], kolom, baris) + rinci


# ---------------------------------------------------------------- email


def _subjek(ringkasan, label, s, nyala):
    k = ringkasan.sendiri
    if ringkasan.sore:
        potong = [
            s["n_selesai"].format(n=len(k.selesai)) if nyala("digest_hari_ini") else "",
            s["n_belum"].format(n=len(k.hari)) if nyala("digest_hari_ini") else "",
            f"{len(k.depan)} {_awal_kecil(label.depan_pendek)}" if nyala("digest_depan") else "",
            s["n_terlambat"].format(n=len(k.lewat)) if nyala("digest_terlambat") else "",
        ]
        awalan = s["awalan_sore"]
    else:
        potong = [
            s["n_hari_ini"].format(n=len(k.hari)) if nyala("digest_hari_ini") else "",
            s["n_depan_pagi"].format(n=len(k.depan)) if nyala("digest_depan") else "",
            s["n_terlambat"].format(n=len(k.lewat)) if nyala("digest_terlambat") else "",
        ]
        awalan = s["awalan_pagi"]
    subjek = awalan + (", ".join(p for p in potong if p) or s["subjek_kosong"])
    if ringkasan.tim:
        subjek += s["subjek_tim"].format(n=sum(len(g.tugas.lewat) for g in ringkasan.tim))
    return subjek


def susun_email(penerima, ringkasan, hari_ini, bahasa="id"):
    """(subjek, teks, html) untuk satu penerima."""
    s = _t(bahasa)
    k = ringkasan.sendiri
    label = label_untuk(ringkasan, hari_ini, bahasa)

    def nyala(kunci):
        return ringkasan.bagian.get(kunci, True)

    subjek = _subjek(ringkasan, label, s, nyala)
    sapaan = s["sapaan"].format(nama=penerima.display_name or penerima.first_name or "").replace(" ,", ",")
    cakupan = terjemah_data(ringkasan.cakupan, bahasa)
    peran = terjemah_data(ringkasan.peran, bahasa) + (f" · {cakupan}" if cakupan else "")
    if not all(nyala(x) for x in ("digest_terlambat", "digest_hari_ini", "digest_depan")):
        kosong = s["kosong_pilihan"]
    elif ringkasan.sore:
        kosong = s["kosong_sore"].format(depan=_awal_kecil(label.depan))
    else:
        kosong = s["kosong_pagi"]
    judul = s["judul_sore"] if ringkasan.sore else s["judul_pagi"]
    tgl = tanggal(hari_ini, bahasa)

    teks = [sapaan, "", f"{judul}, {tgl} ({peran}).", ""]
    teks += [f"== {s['tugas_anda'].upper()} ==", ""] + (_kelompok_teks(k, hari_ini, label, bahasa=bahasa) or [kosong, ""])
    if ringkasan.diberikan:
        teks += [f"== {s['diberikan'].upper()} ==", ""] + _kelompok_teks(
            ringkasan.diberikan, hari_ini, label, ringkasan, bahasa
        )
    teks += _tim_teks(ringkasan, hari_ini, label, bahasa)
    teks.append(s["kaki_teks"].format(merek=MEREK))

    url = _base_url()
    slug = ""
    for kelompok in (k, ringkasan.diberikan, *[g.tugas for g in ringkasan.tim]):
        for daftar in (kelompok.lewat, kelompok.hari, kelompok.depan, kelompok.selesai):
            if daftar and not slug:
                slug = getattr(getattr(daftar[0], "workspace", None), "slug", "") or ""
    isi = (
        judul_html(f"{judul}, {tgl}")
        + sapaan_html(sapaan, peran)
        + (
            _kelompok_html(s["tugas_anda"], k, hari_ini, label, bahasa=bahasa)
            or judul_bagian(s["tugas_anda"]) + paragraf(kosong, WARNA["teks_2"], UKURAN["isi_2"], jarak=RUANG["blok"])
        )
        + _kelompok_html(s["diberikan"], ringkasan.diberikan, hari_ini, label, ringkasan, bahasa)
        + _tim_html(ringkasan, hari_ini, label, bahasa)
        + tombol(s["tombol"], f"{url}/{slug}/" if url and slug else url)
    )
    html = bungkus(
        isi,
        bahasa=bahasa,
        judul=subjek,
        pratajuk=subjek,
        alasan=s["alasan"],
        url_preferensi=url_preferensi(slug),
        email_penerima=getattr(penerima, "email", ""),
    )
    return subjek, "\n".join(teks), html
