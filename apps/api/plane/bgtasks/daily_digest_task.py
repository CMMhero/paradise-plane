# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: ringkasan tugas harian lewat email
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu email ringkasan per orang per hari: jatuh tempo hari ini, jatuh tempo
7 hari ke depan, dan yang sudah terlambat.

Beda dengan `deadline_reminder_task` (satu email per tugas di delapan titik),
ini satu email berisi semuanya, jadi orang yang punya banyak tugas tidak
kebanjiran. Yang dihitung hanya tugas yang DI-ASSIGN ke penerima, bukan yang
ia buat: ringkasan ini daftar kerja, bukan daftar pantauan.

OPT-IN per orang (keputusan user 2026-10-26): hanya yang menyalakan
`UserNotificationPreference.daily_digest` di Profil -> Notifikasi yang dikirimi,
dan bawaannya MATI. Karena persetujuannya sudah per orang, saklar global
`ENABLE_DEADLINE_REMINDER` (untuk pengingat tenggat massal) tidak dipakai di sini.
Jadwal: Senin-Jumat 08.30 Jakarta (lihat beat_schedule di plane/celery.py).

ponytail: tidak ada tabel pencatat "sudah terkirim hari ini". Beat memicu sekali
sehari; kalau task dijalankan manual dua kali, orang menerima dua email. Tambah
tabel kalau itu mulai terjadi.
"""

import logging
from collections import defaultdict
from datetime import timedelta

from celery import shared_task
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils import timezone
from django.utils.html import escape

from plane.bgtasks.deadline_reminder_email import KANTOR, PRODUK, _base_url
from plane.bgtasks.deadline_reminder_task import GRUP_SELESAI
from plane.db.models import IssueAssignee, UserNotificationPreference
from plane.license.utils.instance_value import get_email_configuration
from plane.utils.exception_logger import log_exception

logger = logging.getLogger("plane")

HARI_KE_DEPAN = 7
# Batas baris per bagian. Orang dengan 80 tugas terlambat butuh tahu angkanya,
# bukan 80 baris di email; sisanya diringkas jadi "+N lainnya".
BATAS_BARIS = 15


def kelompokkan(tugas_per_orang, hari_ini):
    """Pecah tugas satu orang jadi (hari_ini, tujuh_hari, terlambat), terurut tenggat."""
    batas = hari_ini + timedelta(days=HARI_KE_DEPAN)
    hari, depan, lewat = [], [], []
    for issue in sorted(tugas_per_orang, key=lambda i: i.target_date):
        if issue.target_date < hari_ini:
            lewat.append(issue)
        elif issue.target_date == hari_ini:
            hari.append(issue)
        elif issue.target_date <= batas:
            depan.append(issue)
    return hari, depan, lewat


def _tautan(issue):
    url = _base_url()
    return f"{url}/{issue.workspace.slug}/projects/{issue.project_id}/issues/{issue.id}" if url else ""


def _baris_teks(issue, hari_ini):
    selisih = (issue.target_date - hari_ini).days
    if selisih < 0:
        ket = f"terlambat {-selisih} hari"
    elif selisih == 0:
        ket = "hari ini"
    else:
        ket = f"{selisih} hari lagi"
    return f"  {issue.project.identifier}-{issue.sequence_id}  {issue.name}  ({issue.target_date:%d %b %Y}, {ket})"


def _bagian_teks(judul, daftar, hari_ini):
    if not daftar:
        return []
    baris = [f"{judul} ({len(daftar)})"] + [_baris_teks(i, hari_ini) for i in daftar[:BATAS_BARIS]]
    if len(daftar) > BATAS_BARIS:
        baris.append(f"  ... +{len(daftar) - BATAS_BARIS} lainnya")
    return baris + [""]


def _bagian_html(judul, daftar, hari_ini, warna):
    if not daftar:
        return ""
    baris = []
    for issue in daftar[:BATAS_BARIS]:
        selisih = (issue.target_date - hari_ini).days
        ket = f"terlambat {-selisih} hari" if selisih < 0 else ("hari ini" if selisih == 0 else f"{selisih} hari lagi")
        nama = f"<strong>{escape(issue.project.identifier)}-{issue.sequence_id}</strong> {escape(issue.name)}"
        tautan = _tautan(issue)
        if tautan:
            nama = f'<a href="{escape(tautan)}" style="color:#1f2937;text-decoration:none">{nama}</a>'
        baris.append(
            f'<tr><td style="padding:4px 12px 4px 0">{nama}</td>'
            f'<td style="padding:4px 0;color:{warna};white-space:nowrap">{issue.target_date:%d %b %Y} ({ket})</td></tr>'
        )
    sisa = (
        f'<tr><td colspan="2" style="padding:4px 0;color:#6b7280">+{len(daftar) - BATAS_BARIS} lainnya</td></tr>'
        if len(daftar) > BATAS_BARIS
        else ""
    )
    return (
        f'<h3 style="margin:20px 0 6px;color:{warna};font-size:14px">{judul} ({len(daftar)})</h3>'
        f'<table style="border-collapse:collapse;font-size:13px">{"".join(baris)}{sisa}</table>'
    )


def susun_email(penerima, hari, depan, lewat, hari_ini):
    """Kembalikan (subjek, teks, html). Murni, tanpa I/O, supaya mudah diuji."""
    subjek = f"[Ringkasan harian] {len(hari)} hari ini, {len(depan)} 7 hari ke depan, {len(lewat)} terlambat"
    sapaan = penerima.display_name or penerima.first_name or ""
    teks = (
        [f"Halo {sapaan},".strip(), "", f"Ringkasan tugas Anda, {hari_ini:%d %B %Y}.", ""]
        + _bagian_teks("TERLAMBAT", lewat, hari_ini)
        + _bagian_teks("JATUH TEMPO HARI INI", hari, hari_ini)
        + _bagian_teks(f"JATUH TEMPO {HARI_KE_DEPAN} HARI KE DEPAN", depan, hari_ini)
        + [f"Email otomatis dari {PRODUK}. Tidak perlu dibalas."]
    )
    html = (
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#1f2937;max-width:600px">'
        f"<p>Halo {escape(sapaan)},</p><p>Ringkasan tugas Anda, <strong>{hari_ini:%d %B %Y}</strong>.</p>"
        + _bagian_html("Terlambat", lewat, hari_ini, "#b91c1c")
        + _bagian_html("Jatuh tempo hari ini", hari, hari_ini, "#b45309")
        + _bagian_html(f"Jatuh tempo {HARI_KE_DEPAN} hari ke depan", depan, hari_ini, "#1f2937")
        + f'<p style="color:#9ca3af;font-size:11px;margin-top:24px">Email otomatis dari {PRODUK}, '
        f"sistem internal {KANTOR}. Tidak perlu dibalas.</p></div>"
    )
    return subjek, "\n".join(teks), html


def _tugas_per_orang(hari_ini):
    """{User: [Issue]} untuk tugas terbuka yang tenggatnya sudah dekat atau lewat."""
    baris = (
        IssueAssignee.objects.filter(
            issue__target_date__lte=hari_ini + timedelta(days=HARI_KE_DEPAN),
            issue__deleted_at__isnull=True,
            issue__archived_at__isnull=True,
            issue__is_draft=False,
            issue__project__archived_at__isnull=True,
            assignee__is_active=True,
            assignee__is_bot=False,
            # Subquery, bukan join ke tabel preferensi: join menggandakan baris
            # (dan tugas di email) kalau satu orang punya beberapa baris preferensi.
            assignee_id__in=UserNotificationPreference.objects.filter(daily_digest=True).values("user_id"),
        )
        .exclude(issue__state__group__in=GRUP_SELESAI)
        .select_related("issue__project", "issue__workspace", "assignee")
    )
    peta = defaultdict(list)
    for r in baris:
        peta[r.assignee].append(r.issue)
    return peta


@shared_task
def kirim_ringkasan_harian():
    """Dijalankan sekali sehari. Lihat beat_schedule di plane/celery.py."""
    hari_ini = timezone.localtime(timezone.now()).date()
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

    terkirim = kosong = gagal = 0
    for orang, tugas in _tugas_per_orang(hari_ini).items():
        hari, depan, lewat = kelompokkan(tugas, hari_ini)
        if not (hari or depan or lewat):
            kosong += 1
            continue
        try:
            subjek, teks, html = susun_email(orang, hari, depan, lewat, hari_ini)
            pesan = EmailMultiAlternatives(
                subject=subjek, body=teks, from_email=efrom, to=[orang.email], connection=koneksi
            )
            pesan.attach_alternative(html, "text/html")
            pesan.send(fail_silently=False)
            terkirim += 1
        except Exception as e:  # noqa: BLE001
            # Satu alamat rusak tidak boleh menahan ringkasan orang lain.
            gagal += 1
            log_exception(e)

    logger.info("Ringkasan harian %s: %s terkirim, %s kosong, %s gagal", hari_ini, terkirim, kosong, gagal)
    return {"terkirim": terkirim, "kosong": kosong, "gagal": gagal}
