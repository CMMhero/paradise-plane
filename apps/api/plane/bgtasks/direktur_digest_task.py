# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: ringkasan tugas selesai untuk direktur
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu email per hari untuk direktur: tugas yang SELESAI, dikelompokkan per divisi.

Pengganti email per-kejadian. Direktur tidak butuh tiap aksi staf (lihat
`notification_task`, yang tidak lagi mengirim email ke direktur); mereka butuh
gambaran hasil. Tanpa opt-in, karena itu satu-satunya email rutin direktur.
Jadwal: Senin-Jumat 08.30 Jakarta. Senin mencakup Jumat sore sampai Minggu.

ponytail: tanpa tabel pencatat "sudah terkirim"; jalankan manual dua kali = dua email.
"""

import logging
from collections import defaultdict
from datetime import timedelta

from celery import shared_task
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils import timezone
from django.utils.html import escape

from plane.bgtasks.deadline_reminder_email import PRODUK
from plane.db.models import Issue, JabatanOrganisasi, TINGKAT_DIREKTUR
from plane.license.utils.instance_value import get_email_configuration
from plane.utils.exception_logger import log_exception

logger = logging.getLogger("plane")

BATAS_BARIS = 8  # per divisi; sisanya "+N lainnya"


def jendela_jam(hari_ini):
    """Senin menutup akhir pekan; hari lain cukup 24 jam."""
    return 72 if hari_ini.weekday() == 0 else 24


def susun_email(penerima, per_divisi, hari_ini):
    """(subjek, teks, html) dari {nama_divisi: [Issue]}. Murni, tanpa I/O."""
    total = sum(len(v) for v in per_divisi.values())
    subjek = f"[Ringkasan direktur] {total} tugas selesai di {len(per_divisi)} divisi"
    sapaan = penerima.display_name or penerima.first_name or ""
    teks, html = [f"Halo {sapaan},".strip(), "", f"Tugas selesai, {hari_ini:%d %B %Y}.", ""], []
    for divisi, tugas in sorted(per_divisi.items()):
        teks.append(f"{divisi} ({len(tugas)})")
        html.append(f'<h3 style="margin:18px 0 6px;font-size:14px">{escape(divisi)} ({len(tugas)})</h3><ul>')
        for i in tugas[:BATAS_BARIS]:
            kode = f"{i.project.identifier}-{i.sequence_id}"
            teks.append(f"  {kode}  {i.name}")
            html.append(f"<li><strong>{escape(kode)}</strong> {escape(i.name)}</li>")
        if len(tugas) > BATAS_BARIS:
            teks.append(f"  ... +{len(tugas) - BATAS_BARIS} lainnya")
            html.append(f"<li>+{len(tugas) - BATAS_BARIS} lainnya</li>")
        teks.append("")
        html.append("</ul>")
    teks.append(f"Email otomatis dari {PRODUK}. Tidak perlu dibalas.")
    body = (
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#1f2937;max-width:600px">'
        f"<p>Halo {escape(sapaan)},</p><p>Tugas selesai, <strong>{hari_ini:%d %B %Y}</strong>.</p>"
        + "".join(html)
        + f'<p style="color:#9ca3af;font-size:11px">Email otomatis dari {PRODUK}. Tidak perlu dibalas.</p></div>'
    )
    return subjek, "\n".join(teks), body


def _selesai_per_workspace(sejak):
    peta = defaultdict(lambda: defaultdict(list))
    qs = Issue.issue_objects.filter(completed_at__gte=sejak).select_related("project")
    for i in qs:
        peta[i.workspace_id][i.project.name].append(i)
    return peta


@shared_task
def kirim_ringkasan_direktur():
    """Dijalankan sekali sehari. Lihat beat_schedule di plane/celery.py."""
    sekarang = timezone.now()
    hari_ini = timezone.localtime(sekarang).date()
    selesai = _selesai_per_workspace(sekarang - timedelta(hours=jendela_jam(hari_ini)))

    host, user, pwd, port, use_tls, use_ssl, efrom = get_email_configuration()
    koneksi = get_connection(
        host=host,
        port=int(port),
        username=user,
        password=pwd,
        use_tls=str(use_tls) == "1",
        use_ssl=str(use_ssl) == "1",
        timeout=30,
    )

    terkirim = gagal = 0
    direktur = JabatanOrganisasi.objects.filter(
        tingkat__gte=TINGKAT_DIREKTUR, member__is_active=True, member__is_bot=False
    ).select_related("member")
    for jabatan in direktur:
        per_divisi = selesai.get(jabatan.workspace_id)
        if not per_divisi:
            continue
        try:
            subjek, teks, html = susun_email(jabatan.member, per_divisi, hari_ini)
            pesan = EmailMultiAlternatives(
                subject=subjek, body=teks, from_email=efrom, to=[jabatan.member.email], connection=koneksi
            )
            pesan.attach_alternative(html, "text/html")
            pesan.send(fail_silently=False)
            terkirim += 1
        except Exception as e:  # noqa: BLE001
            gagal += 1
            log_exception(e)

    logger.info("Ringkasan direktur %s: %s terkirim, %s gagal", hari_ini, terkirim, gagal)
    return {"terkirim": terkirim, "gagal": gagal}
