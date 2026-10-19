# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: email pemberitahuan pesan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Penyusun dan pengirim satu email rangkuman pesan yang belum dibaca."""

import os
from html import escape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

from plane.license.utils.instance_value import get_email_configuration

PRODUK = "Paradise Task Tracker"
KANTOR = "PT Paradise Perkasa"

# Panjang cuplikan isi pesan di dalam email. Cukup untuk tahu ini soal apa,
# pendek supaya email tidak jadi tempat membaca seluruh percakapan. Membacanya
# di aplikasi juga yang menandainya terbaca.
PANJANG_CUPLIKAN = 120


def _base_url() -> str:
    """Alamat aplikasi untuk tautan balik. Diambil dari environment."""
    return (settings.APP_BASE_URL or os.environ.get("WEB_URL") or "").rstrip("/")


def _cuplik(teks: str) -> str:
    satu_baris = " ".join((teks or "").split())
    if len(satu_baris) <= PANJANG_CUPLIKAN:
        return satu_baris
    return satu_baris[: PANJANG_CUPLIKAN - 1] + "…"


def kirim_email_pesan(penerima, slug: str, ringkasan: list) -> None:
    """Kirim satu email berisi seluruh pesan belum dibaca milik satu orang.

    `ringkasan` berisi tuple (pengirim, jumlah, isi_terakhir), satu per lawan
    bicara. Melempar kalau gagal, biar pemanggil yang mencatat.
    """
    host, user, pwd, port, use_tls, use_ssl, efrom = get_email_configuration()

    total = sum(jumlah for _, jumlah, _ in ringkasan)
    if len(ringkasan) == 1:
        pengirim = ringkasan[0][0]
        nama = pengirim.display_name or pengirim.first_name or pengirim.email
        subjek = f"[Obrolan] {total} pesan baru dari {nama}"
    else:
        subjek = f"[Obrolan] {total} pesan baru dari {len(ringkasan)} orang"

    url = _base_url()

    baris_teks = [
        f"Halo {penerima.display_name or penerima.first_name or ''},".strip(),
        "",
        "Ada pesan yang belum Anda baca di Obrolan:",
        "",
    ]
    baris_html = []
    for pengirim, jumlah, isi_terakhir in ringkasan:
        nama = pengirim.display_name or pengirim.first_name or pengirim.email
        tautan = f"{url}/{slug}/chat?dengan={pengirim.id}" if url else ""
        baris_teks += [
            f"  {nama} ({jumlah} pesan)",
            f"    {_cuplik(isi_terakhir)}",
        ]
        if tautan:
            baris_teks.append(f"    Buka: {tautan}")
        baris_teks.append("")
        tombol = (
            f'<div style="margin-top:6px"><a href="{escape(tautan)}" '
            f'style="color:#1f2937">Buka percakapan</a></div>'
            if tautan
            else ""
        )
        # Isi pesan orang lain masuk ke HTML, jadi WAJIB di-escape. Tanpa ini
        # siapa pun bisa menyuntikkan markup ke kotak masuk rekannya hanya
        # dengan mengetiknya di obrolan.
        baris_html.append(
            f"""
  <tr>
    <td style="padding:8px 0;border-bottom:1px solid #e5e7eb">
      <div><strong>{escape(nama)}</strong>
        <span style="color:#6b7280">&middot; {jumlah} pesan</span></div>
      <div style="color:#4b5563;margin-top:2px">{escape(_cuplik(isi_terakhir))}</div>
      {tombol}
    </td>
  </tr>"""
        )

    baris_teks += [
        "Pesan ditandai terbaca saat Anda membukanya di aplikasi.",
        "",
        f"Email otomatis dari {PRODUK}. Tidak perlu dibalas.",
    ]

    html = f"""
<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#1f2937;max-width:560px">
  <p>Halo {escape(penerima.display_name or "")},</p>
  <p>Ada pesan yang belum Anda baca di Obrolan.</p>
  <table style="border-collapse:collapse;width:100%;margin:16px 0">{"".join(baris_html)}
  </table>
  <p style="color:#6b7280;font-size:12px">
    Pesan ditandai terbaca saat Anda membukanya di aplikasi.
  </p>
  <p style="color:#9ca3af;font-size:11px;margin-top:24px">
    Email otomatis dari {PRODUK}, sistem internal {KANTOR}. Tidak perlu dibalas.<br>
    Paradise Task Tracker
  </p>
</div>
""".strip()

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
    pesan.send(fail_silently=False)
