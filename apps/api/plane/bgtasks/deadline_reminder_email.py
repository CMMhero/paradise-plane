# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: email pengingat tenggat
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Penyusun dan pengirim satu email pengingat tenggat, berikut lampiran .ics."""

import os
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils import timezone

from plane.license.utils.instance_value import get_email_configuration

PRODUK = "Paradise Task Tracker"
KANTOR = "PT Paradise Perkasa"

# Pengingat lokal yang ikut tertanam di berkas .ics. Hanya yang SEBELUM tenggat:
# standar iCalendar tidak bisa membunyikan alarm sesudah acara lewat, dan
# memaksakannya justru membuat sebagian aplikasi kalender menolak berkasnya.
# Titik overdue tetap diingatkan, tapi lewat email ini sendiri.
ALARM_HARI = [7, 5, 3, 1]

# Titik nol penomoran revisi acara. Sengaja bukan epoch Unix: sebagian klien
# kalender menyimpan SEQUENCE sebagai integer 32-bit, dan detik Unix menembus
# batas itu pada 2038. Dihitung dari sini, angkanya tetap kecil.
EPOCH_SEQUENCE = datetime(2026, 1, 1, tzinfo=dt_timezone.utc)


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


def kirim_email_pengingat(issue, penerima, titik: int, label: str) -> None:
    """Kirim satu pengingat. Melempar kalau gagal, biar pemanggil yang mencatat."""
    host, user, pwd, port, use_tls, use_ssl, efrom = get_email_configuration()

    kode = f"{issue.project.identifier}-{issue.sequence_id}"
    overdue = titik > 0
    awalan = "TERLAMBAT" if overdue else "Pengingat"
    subjek = f"[{awalan}] {kode} {issue.name} ({label})"

    url = _base_url()
    tautan = (
        f"{url}/{issue.workspace.slug}/projects/{issue.project_id}/issues/{issue.id}"
        if url
        else ""
    )

    baris_teks = [
        f"Halo {penerima.display_name or penerima.first_name or ''},".strip(),
        "",
        ("Work item ini SUDAH LEWAT TENGGAT." if overdue else "Pengingat tenggat work item."),
        "",
        f"  {kode}  {issue.name}",
        f"  Project : {issue.project.name}",
        f"  Tenggat : {issue.target_date:%d %B %Y} ({label})",
        f"  Status  : {issue.state.name if issue.state else '-'}",
    ]
    if tautan:
        baris_teks += ["", f"Buka: {tautan}"]
    baris_teks += [
        "",
        "Lampiran .ics terlampir. Buka sekali untuk memasukkan tenggat ini ke",
        "kalender Anda (Outlook, Google, atau ponsel) berikut pengingatnya.",
        "",
        f"Email otomatis dari {PRODUK}. Tidak perlu dibalas.",
    ]

    warna = "#b91c1c" if overdue else "#1f2937"
    html = f"""
<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#1f2937;max-width:560px">
  <p>Halo {penerima.display_name or ''},</p>
  <p style="color:{warna};font-weight:bold">
    {"Work item ini SUDAH LEWAT TENGGAT." if overdue else "Pengingat tenggat work item."}
  </p>
  <table style="border-collapse:collapse;margin:16px 0">
    <tr><td style="padding:4px 12px 4px 0;color:#6b7280">Work item</td><td style="padding:4px 0"><strong>{kode}</strong> {issue.name}</td></tr>
    <tr><td style="padding:4px 12px 4px 0;color:#6b7280">Project</td><td style="padding:4px 0">{issue.project.name}</td></tr>
    <tr><td style="padding:4px 12px 4px 0;color:#6b7280">Tenggat</td><td style="padding:4px 0;color:{warna}"><strong>{issue.target_date:%d %B %Y}</strong> ({label})</td></tr>
    <tr><td style="padding:4px 12px 4px 0;color:#6b7280">Status</td><td style="padding:4px 0">{issue.state.name if issue.state else '-'}</td></tr>
  </table>
  {f'<p><a href="{tautan}" style="background:#1f2937;color:#fff;padding:8px 16px;border-radius:4px;text-decoration:none;display:inline-block">Buka work item</a></p>' if tautan else ''}
  <p style="color:#6b7280;font-size:12px">
    Berkas <strong>.ics</strong> terlampir. Buka sekali untuk memasukkan tenggat ini ke
    kalender Anda (Outlook, Google, atau ponsel) berikut pengingatnya.
  </p>
  <p style="color:#9ca3af;font-size:11px;margin-top:24px">
    Email otomatis dari {PRODUK}, sistem internal {KANTOR}. Tidak perlu dibalas.<br>
    Paradise Task Tracker
  </p>
</div>
""".strip()

    ics = bangun_ics(
        issue=issue,
        judul=f"{kode} {issue.name}",
        deskripsi=f"Project {issue.project.name}. Tenggat {issue.target_date:%d %B %Y}." + (f" {tautan}" if tautan else ""),
        url=tautan,
    )

    koneksi = get_connection(
        host=host,
        port=int(port),
        username=user,
        password=pwd,
        use_tls=str(use_tls) == "1",
        use_ssl=str(use_ssl) == "1",
        timeout=30,
    )
    pesan = EmailMultiAlternatives(
        subject=subjek,
        body="\n".join(baris_teks),
        from_email=efrom,
        to=[penerima.email],
        connection=koneksi,
    )
    pesan.attach_alternative(html, "text/html")
    # `text/calendar` dengan method=PUBLISH: dibaca sebagai berkas yang bisa
    # ditambahkan, bukan sebagai undangan rapat yang menuntut balasan.
    pesan.attach(f"{kode}.ics", ics, "text/calendar; method=PUBLISH")
    pesan.send(fail_silently=False)
