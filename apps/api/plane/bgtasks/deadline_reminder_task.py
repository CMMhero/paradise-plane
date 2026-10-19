# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pengingat tenggat
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Pengingat tenggat work item, dikirim lewat email.

Delapan titik: H-7, H-5, H-3, H-1, hari H, lalu H+3, H+5, H+7 sebagai OVERDUE.

Tiap email membawa lampiran `.ics` supaya penerima bisa memasukkan tenggatnya ke
kalender apa pun dengan sekali klik: Outlook (yang dipakai kantor), Google, atau
ponsel. Ini sengaja dipilih daripada integrasi Google Calendar langsung, karena
integrasi itu terganjal dua hal di luar kendali kita: aplikasi belum HTTPS, dan
Google mewajibkan verifikasi untuk scope kalender pada akun non-Workspace.
Lampiran ICS tidak butuh keduanya dan melayani semua orang, bukan hanya pengguna
Gmail.
"""

import logging
import os
from datetime import timedelta

from django.utils import timezone

from plane.db.models import Issue, PengingatTenggat, SEMUA_TITIK, TITIK_OVERDUE
from plane.utils.exception_logger import log_exception

from .deadline_reminder_email import kirim_email_pengingat
from celery import shared_task

logger = logging.getLogger("plane")

# Tugas yang sudah selesai atau dibatalkan tidak perlu diingatkan lagi,
# termasuk yang sudah lewat tenggat.
GRUP_SELESAI = ["completed", "cancelled"]

# Saklar pengaman, MATI secara bawaan. Fitur ini mengirim email massal ke
# seluruh karyawan, jadi menyalakannya harus tindakan sadar, bukan efek samping
# dari sebuah deploy. Nyalakan lewat `ENABLE_DEADLINE_REMINDER=1` di
# `apps/api/.env` lalu `docker compose up -d` (restart saja TIDAK cukup, env
# file hanya dibaca ulang saat container dibuat ulang).
#
# Saklar ini hanya menjaga tugas terjadwal. `kirim_email_pengingat()` tetap bisa
# dipanggil langsung untuk mengirim contoh ke satu alamat saat pengujian.
def _aktif() -> bool:
    return os.environ.get("ENABLE_DEADLINE_REMINDER", "0") == "1"


def _label_titik(titik: int) -> str:
    if titik == 0:
        return "jatuh tempo hari ini"
    if titik < 0:
        return f"tinggal {-titik} hari lagi"
    return f"TERLAMBAT {titik} hari"


def _penerima(issue):
    """Siapa yang diingatkan: yang dikerjai tugasnya, dan yang memberi tugas.

    Keputusan user 2026-08-11. Kalau seseorang memberi tugas ke dirinya sendiri,
    ia tetap menerima satu email, bukan dua, karena dikumpulkan sebagai himpunan.

    Bot dan akun nonaktif dibuang: mengirim ke akun mati hanya menghasilkan
    bounce yang mengotori reputasi pengirim.
    """
    orang = {a for a in issue.assignees.filter(is_active=True, is_bot=False)}
    if issue.created_by and issue.created_by.is_active and not issue.created_by.is_bot:
        orang.add(issue.created_by)
    return orang


@shared_task
def kirim_pengingat_tenggat():
    """Dijalankan sekali sehari. Lihat beat_schedule di plane/celery.py.

    Menghitung ulang dari `target_date` yang berlaku HARI INI, bukan dari
    jadwal yang disimpan di depan. Jadi kalau tenggat digeser, pengingatnya
    ikut bergeser sendiri tanpa perlu ada yang membatalkan jadwal lama.
    """
    if not _aktif():
        logger.info("Pengingat tenggat dilewati: ENABLE_DEADLINE_REMINDER belum diset ke 1")
        return {"aktif": False}

    hari_ini = timezone.localtime(timezone.now()).date()
    terkirim = dilewati = gagal = 0

    for titik in SEMUA_TITIK:
        # titik -7 berarti "7 hari sebelum tenggat", jadi tenggatnya hari_ini + 7.
        tenggat = hari_ini - timedelta(days=titik)

        antrian = (
            Issue.issue_objects.filter(target_date=tenggat)
            .exclude(state__group__in=GRUP_SELESAI)
            .exclude(project__archived_at__isnull=False)
            .select_related("project", "workspace", "state", "created_by")
            .prefetch_related("assignees")
        )

        for issue in antrian:
            for orang in _penerima(issue):
                sudah = PengingatTenggat.objects.filter(
                    issue=issue, penerima=orang, titik=titik, tenggat=tenggat
                ).exists()
                if sudah:
                    dilewati += 1
                    continue

                try:
                    kirim_email_pengingat(issue=issue, penerima=orang, titik=titik, label=_label_titik(titik))
                except Exception as e:  # noqa: BLE001
                    # Satu email gagal tidak boleh menghentikan sisa antrian:
                    # satu alamat rusak akan membuat 88 orang lain tak
                    # diingatkan hari itu.
                    gagal += 1
                    log_exception(e)
                    continue

                # Dicatat SESUDAH terkirim. Kalau dicatat lebih dulu lalu
                # pengiriman gagal, pengingat itu hilang selamanya karena
                # dianggap sudah dikirim.
                PengingatTenggat.objects.create(
                    workspace_id=issue.workspace_id,
                    project_id=issue.project_id,
                    issue=issue,
                    penerima=orang,
                    titik=titik,
                    tenggat=tenggat,
                )
                terkirim += 1

    logger.info(
        "Pengingat tenggat %s: %s terkirim, %s dilewati (sudah pernah), %s gagal",
        hari_ini,
        terkirim,
        dilewati,
        gagal,
    )
    return {"terkirim": terkirim, "dilewati": dilewati, "gagal": gagal}
