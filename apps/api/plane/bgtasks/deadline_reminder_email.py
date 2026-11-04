# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: email pengingat tenggat
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Penyusun dan pengirim satu email pengingat tenggat, berikut lampiran .ics."""

import os
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.conf import settings
from django.utils import timezone

from plane.utils.email_merek import (
    KANTOR,
    MEREK,
    WARNA,
    alamat_gabungan,
    bahasa_penerima,
    bungkus,
    buat_pesan,
    catatan_kecil,
    daftar_orang,
    gabung_nama,
    judul_html,
    kartu,
    sapaan_html,
    tanggal,
    tombol,
    url_preferensi,
)

# Nama lama tetap diekspor: ringkasan, laporan direktur, dan penugasan mengimpornya.
PRODUK = MEREK
__all__ = ["KANTOR", "PRODUK"]

# Pengingat lokal yang ikut tertanam di berkas .ics. Hanya yang SEBELUM tenggat:
# standar iCalendar tidak bisa membunyikan alarm sesudah acara lewat, dan
# memaksakannya justru membuat sebagian aplikasi kalender menolak berkasnya.
# Titik overdue tetap diingatkan, tapi lewat email ini sendiri.
ALARM_HARI = [7, 5, 3, 1]

# Titik nol penomoran revisi acara. Sengaja bukan epoch Unix: sebagian klien
# kalender menyimpan SEQUENCE sebagai integer 32-bit, dan detik Unix menembus
# batas itu pada 2038. Dihitung dari sini, angkanya tetap kecil.
EPOCH_SEQUENCE = datetime(2026, 1, 1, tzinfo=dt_timezone.utc)

BULAN = ("Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
         "November", "Desember")  # fmt: skip


def tanggal_id(nilai, pendek: bool = False) -> str:
    """`2 November 2026` / `2 Nov 2026`. strftime ikut locale server (Inggris), email ini berbahasa Indonesia."""
    if not nilai:
        return ""
    bulan = BULAN[nilai.month - 1]
    return f"{nilai.day} {bulan[:3] if pendek else bulan} {nilai.year}"


def _base_url() -> str:
    """Alamat aplikasi untuk tautan balik.

    Diambil dari environment, bukan ditebak: instance ini dijangkau lewat IP di
    LAN kantor sekarang, dan akan berganti jadi nama domain begitu HTTPS hidup.
    """
    return (settings.APP_BASE_URL or os.environ.get("WEB_URL") or "").rstrip("/")


def _esc(teks: str) -> str:
    """Escape teks untuk iCalendar (RFC 5545 pasal 3.3.11)."""
    return (
        str(teks or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _lipat(baris: str) -> str:
    """Lipat baris panjang jadi maksimal 75 oktet, sambungannya diawali spasi.

    Wajib menurut RFC 5545. Tanpa ini, judul work item yang panjang membuat
    sebagian aplikasi kalender menolak seluruh berkasnya.
    """
    data = baris.encode("utf-8")
    if len(data) <= 75:
        return baris
    potongan, sisa = [], data
    while len(sisa) > 75:
        # Mundur sampai batas karakter utuh, jangan memotong di tengah UTF-8.
        potong = 75
        while potong > 0 and (sisa[potong] & 0xC0) == 0x80:
            potong -= 1
        potongan.append(sisa[:potong].decode("utf-8"))
        sisa = sisa[potong:]
    potongan.append(sisa.decode("utf-8"))
    return "\r\n ".join(potongan)


def _sequence(issue) -> int:
    """Nomor revisi acara, wajib naik tiap kali work item-nya berubah.

    UID yang sama membuat kiriman berikutnya menimpa acara lama, tapi hanya
    kalau ia terbaca sebagai versi yang lebih baru. Tanpa SEQUENCE sebagian
    klien kalender diam-diam mempertahankan tanggal yang lama, jadi tenggat
    yang digeser di aplikasi tidak pernah sampai ke kalender orang.

    `updated_at` naik sendiri tiap kali work item disunting, jadi delapan
    pengingat untuk tenggat yang tidak berubah tetap bernomor sama. Itu memang
    yang diinginkan: tidak ada perubahan, tidak ada yang perlu ditimpa.
    """
    diubah = getattr(issue, "updated_at", None) or EPOCH_SEQUENCE
    return max(0, int((diubah - EPOCH_SEQUENCE).total_seconds()))


def bangun_ics(issue, judul: str, deskripsi: str, url: str) -> str:
    """Susun satu VEVENT sepanjang hari untuk tanggal tenggat.

    Acara sepanjang hari karena `target_date` di sistem ini bertipe tanggal,
    bukan tanggal-jam. `DTEND` pada acara sepanjang hari bersifat eksklusif,
    jadi diisi tanggal berikutnya.
    """
    mulai = issue.target_date
    selesai = mulai + timedelta(days=1)
    stamp = timezone.now().strftime("%Y%m%dT%H%M%SZ")

    baris = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Paradise//Paradise Task Tracker//ID",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:workitem-{issue.id}@paradise-task-tracker",
        f"SEQUENCE:{_sequence(issue)}",
        f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{mulai.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{selesai.strftime('%Y%m%d')}",
        f"SUMMARY:{_esc(judul)}",
        f"DESCRIPTION:{_esc(deskripsi)}",
        "TRANSP:TRANSPARENT",
    ]
    if url:
        baris.append(f"URL:{_esc(url)}")

    for hari in ALARM_HARI:
        baris += [
            "BEGIN:VALARM",
            f"TRIGGER:-P{hari}D",
            "ACTION:DISPLAY",
            f"DESCRIPTION:{_esc(judul)} - tinggal {hari} hari",
            "END:VALARM",
        ]

    baris += ["END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(_lipat(b) for b in baris) + "\r\n"


TEKS_PENGINGAT = {
    "id": {
        "awalan": "Pengingat",
        "awalan_lewat": "TERLAMBAT",
        "kalimat": "Tenggat tugas sudah dekat",
        "kalimat_lewat": "Tugas ini sudah lewat tenggat",
        "sapaan": "Halo {nama},",
        "project": "Project",
        "tenggat": "Tenggat",
        "status": "Status",
        "tombol": "Buka tugas",
        "buka": "Buka: {url}",
        "ics": "Berkas .ics terlampir. Buka sekali untuk memasukkan tenggat ini ke kalender Anda (Outlook, Google, atau ponsel) berikut pengingatnya.",
        "alasan": "Anda menerima email ini karena Anda penanggung jawab atau pemberi tugas ini.",
        "hari_ini": "jatuh tempo hari ini",
        "sisa": "tinggal {n} hari lagi",
        "lewat": "TERLAMBAT {n} hari",
    },
    "en": {
        "awalan": "Reminder",
        "awalan_lewat": "OVERDUE",
        "kalimat": "A work item deadline is coming up",
        "kalimat_lewat": "This work item is past its due date",
        "sapaan": "Hi {nama},",
        "project": "Project",
        "tenggat": "Due date",
        "status": "State",
        "tombol": "Open work item",
        "buka": "Open: {url}",
        "ics": "An .ics file is attached. Open it once to add this deadline and its reminders to your calendar (Outlook, Google, or phone).",
        "alasan": "You received this email because you are assigned to or created this work item.",
        "hari_ini": "due today",
        "sisa": "{n} days left",
        "lewat": "{n} days OVERDUE",
    },
}

# KEP-84: pengingat ke PENYETUJU untuk tugas yang sudah diajukan selesai tapi
# belum diputuskan, lalu lewat tenggatnya. Menimpa kalimat TEKS_PENGINGAT saja.
TEKS_PENYETUJU = {
    "id": {
        "awalan_lewat": "Menunggu persetujuan",
        "kalimat_lewat": "Tugas ini sudah diajukan selesai dan menunggu persetujuan Anda, sementara tenggatnya sudah lewat",
        "alasan": "Anda menerima email ini karena Anda dapat menyetujui tugas ini.",
    },
    "en": {
        "awalan_lewat": "Waiting for approval",
        "kalimat_lewat": "This work item was submitted as done and is waiting for your approval, and its due date has passed",
        "alasan": "You received this email because you can approve this work item.",
    },
}


def _teks(bahasa: str, penyetuju: bool = False) -> dict:
    dasar = TEKS_PENGINGAT.get(bahasa, TEKS_PENGINGAT["id"])
    if not penyetuju:
        return dasar
    return {**dasar, **TEKS_PENYETUJU.get(bahasa, TEKS_PENYETUJU["id"])}


def label_titik(titik: int, bahasa="id") -> str:
    """Keterangan satu titik pengingat: -3 = tinggal 3 hari, 0 = hari ini, 3 = terlambat 3 hari."""
    s = TEKS_PENGINGAT.get(bahasa, TEKS_PENGINGAT["id"])
    if titik == 0:
        return s["hari_ini"]
    return s["sisa"].format(n=-titik) if titik < 0 else s["lewat"].format(n=titik)


def susun_email_pengingat(
    issue, penerima, titik: int, label: str = "", tautan: str = "", bahasa="id", penyetuju: bool = False
):
    """(subjek, teks, html) satu pengingat. Murni: dipakai pengirim dan pratinjau.

    `label` kosong = dihitung dari `titik` dalam `bahasa`. `penyetuju=True` =
    versi untuk atasan yang belum memutuskan pengajuan selesai (KEP-84).
    """
    s = _teks(bahasa, penyetuju)
    label = label or label_titik(titik, bahasa)
    kode = f"{issue.project.identifier}-{issue.sequence_id}"
    overdue = titik > 0
    subjek = f"[{s['awalan_lewat'] if overdue else s['awalan']}] {kode} {issue.name} ({label})"
    status = issue.state.name if issue.state else "-"
    kalimat = s["kalimat_lewat"] if overdue else s["kalimat"]
    tenggat = tanggal(issue.target_date, bahasa)
    # `penerima` boleh daftar: pengingat bersama untuk semua orang di tugas ini.
    orang = daftar_orang(penerima)
    nama = gabung_nama([o.display_name or o.first_name or "" for o in orang], bahasa)
    sapaan = s["sapaan"].format(nama=nama).replace(" ,", ",")

    baris_teks = [
        sapaan,
        "",
        kalimat,
        "",
        f"  {kode}  {issue.name}",
        f"  {s['project']:<9}: {issue.project.name}",
        f"  {s['tenggat']:<9}: {tenggat} ({label})",
        f"  {s['status']:<9}: {status}",
    ]
    if tautan:
        baris_teks += ["", s["buka"].format(url=tautan)]
    baris_teks += ["", s["ics"]]

    warna = WARNA["bahaya"] if overdue else WARNA["peringatan"]
    isi = (
        judul_html(kalimat)
        + sapaan_html(sapaan)
        + kartu(
            kode,
            issue.name,
            tautan,
            [
                (s["project"], issue.project.name),
                (s["tenggat"], f"{tenggat} ({label})", warna),
                (s["status"], status),
            ],
        )
        + tombol(s["tombol"], tautan)
        + catatan_kecil(s["ics"])
    )
    html = bungkus(
        isi,
        bahasa=bahasa,
        judul=subjek,
        pratajuk=f"{kode} {issue.name}: {label}",
        alasan=s["alasan"],
        url_preferensi=url_preferensi(getattr(getattr(issue, "workspace", None), "slug", "")),
        email_penerima=alamat_gabungan(orang),
    )
    return subjek, "\n".join(baris_teks), html


def kirim_email_pengingat(issue, penerima, titik: int, label: str = "") -> None:
    """Kirim satu pengingat ke satu orang. Melempar kalau gagal, biar pemanggil yang mencatat."""
    from plane.utils.email_utas import utas_untuk

    _kirim(issue, [penerima], titik, label, utas_untuk(issue, penerima.id))


def kirim_email_pengingat_bersama(
    issue, penerima, titik: int, label: str = "", penyetuju: bool = False
) -> list[tuple[list, Exception | None]]:
    """Satu email bersama (To: a; b; c) per kelompok penerima pengingat yang sama.

    Isinya sama untuk semua orang di satu tugas dan satu titik, jadi semuanya
    melihat siapa lagi yang diingatkan. Dipecah hanya per bahasa dan posisi di
    utas. Mengembalikan [(kelompok, galat)]: galat None = terkirim. Tidak
    melempar, supaya kelompok yang gagal tidak menahan kelompok lain.
    """
    from plane.utils.email_utas import utas_bersama

    hasil = []
    for kelompok, utas in utas_bersama(issue, list(penerima), bahasa_penerima):
        try:
            _kirim(issue, kelompok, titik, label, utas, penyetuju=penyetuju)
            hasil.append((kelompok, None))
        except Exception as e:  # noqa: BLE001
            hasil.append((kelompok, e))
    return hasil


def _kirim(issue, kelompok, titik: int, label: str, utas, penyetuju: bool = False) -> None:
    """`label` dari pemanggil lama diabaikan untuk penerima berbahasa Inggris:
    teksnya dihitung ulang dari `titik` dalam bahasa penerima.
    """
    bahasa = bahasa_penerima(kelompok[0])
    kode = f"{issue.project.identifier}-{issue.sequence_id}"
    url = _base_url()
    tautan = f"{url}/{issue.workspace.slug}/projects/{issue.project_id}/issues/{issue.id}" if url else ""
    subjek, teks, html = susun_email_pengingat(
        issue, kelompok, titik, label if bahasa == "id" else "", tautan, bahasa=bahasa, penyetuju=penyetuju
    )

    ics = bangun_ics(
        issue=issue,
        judul=f"{kode} {issue.name}",
        deskripsi=f"Project {issue.project.name}. Tenggat {tanggal_id(issue.target_date)}." + (f" {tautan}" if tautan else ""),
        url=tautan,
    )
    # `text/calendar` dengan method=PUBLISH: dibaca sebagai berkas yang bisa
    # ditambahkan, bukan sebagai undangan rapat yang menuntut balasan.
    buat_pesan(
        ke=[o.email for o in kelompok],
        subjek=utas[0] if utas else subjek,
        html=html,
        teks=teks,
        lampiran=[(f"{kode}.ics", ics, "text/calendar; method=PUBLISH")],
        header=utas[1] if utas else None,
    ).send(fail_silently=False)
