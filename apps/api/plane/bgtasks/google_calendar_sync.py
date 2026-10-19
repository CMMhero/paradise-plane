# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: sinkronisasi Google Calendar
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Dorong tenggat work item ke Google Calendar tiap pengguna yang menyambung.

KENAPA BERKALA, BUKAN LEWAT SIGNAL PADA SETIAP PENYIMPANAN
Work item bisa berubah dari belasan jalur: REST, bulk update, otomasi
recurring, impor, dan penghapusan berjenjang. Menempelkan signal pada tiap
jalur berarti satu jalur yang terlewat membuat kalender seseorang menyimpan
tanggal yang sudah tidak berlaku, dan itu tidak akan pernah ketahuan sampai
orangnya datang ke rapat pada hari yang salah.

Rekonsiliasi berkala menghitung ulang dari keadaan yang berlaku SAAT ITU, jadi
jalur mana pun yang mengubahnya akan tersusul dengan sendirinya. Ongkosnya
keterlambatan paling lama satu putaran, dan untuk tenggat harian itu tidak
berarti apa-apa.

Pola yang sama dipakai pengingat tenggat, dengan alasan yang sama.
"""

# Python imports
import logging
import os

# Django imports
from django.db.models import Q
from django.utils import timezone

# Third party imports
from celery import shared_task

# Module imports
from plane.db.models import AcaraKalender, Issue, KalenderGoogle
from plane.license.utils.encryption import decrypt_data
from plane.utils import google_calendar as gcal
from plane.utils.exception_logger import log_exception

logger = logging.getLogger("plane")

GRUP_SELESAI = ["completed", "cancelled"]


def _aktif() -> bool:
    """Saklar pengaman, MATI secara bawaan.

    Fitur ini menulis ke kalender pribadi orang. Menyalakannya harus tindakan
    sadar, bukan efek samping sebuah deploy. Nyalakan lewat
    `ENABLE_GOOGLE_CALENDAR_SYNC=1` di `apps/api/.env` lalu
    `docker compose up -d`; `restart` TIDAK cukup, env file hanya dibaca ulang
    saat container dibuat ulang.
    """
    return os.environ.get("ENABLE_GOOGLE_CALENDAR_SYNC", "0") == "1"


def _judul(issue):
    return f"{issue.project.identifier}-{issue.sequence_id} {issue.name}"


def _deskripsi(issue):
    status = issue.state.name if issue.state else "-"
    return f"Project {issue.project.name}\nStatus {status}"


def _url(issue):
    from django.conf import settings

    dasar = (settings.APP_BASE_URL or "").rstrip("/")
    if not dasar:
        return ""
    return f"{dasar}/{issue.workspace.slug}/projects/{issue.project_id}/issues/{issue.id}"


def _work_item_milik(user):
    """Work item yang layak muncul di kalender seseorang.

    DUA JALUR, dan keduanya disengaja:
      1. Ditugaskan kepada orang itu
      2. Berada di project yang ia PIMPIN (`project_lead`)

    Jalur kedua permintaan user 2026-08-12, dengan kalimatnya sendiri: "selama
    itu memang tugasnya di-assign untuk dia atau memang project itu punya dia".

    ⚠️ ONGKOSNYA DISADARI: pemimpin project menerima SELURUH work item bertenggat
    di project itu, termasuk yang sudah ditugaskan ke orang lain. Pada project
    besar, kalendernya bisa tertimbun sampai berhenti berguna sebagai kalender.
    Ini sudah disampaikan sebelum dikerjakan dan tetap dipilih.

    Kalau suatu saat terasa terlalu ramai, versi yang lebih tenang adalah
    membatasi jalur kedua ke work item yang BELUM ditugaskan ke siapa pun:
    tambahkan `Q(project__project_lead=user, assignees__isnull=True)`
    menggantikan jalur kedua di bawah. Pengawasannya tetap dapat, banjirnya
    tidak.

    `distinct()` wajib: work item yang ditugaskan ke pemimpin project-nya
    sendiri cocok di kedua jalur, dan tanpa ini ia terhitung dua kali.
    """
    return (
        Issue.issue_objects.filter(
            Q(assignees=user) | Q(project__project_lead=user),
            target_date__isnull=False,
        )
        .exclude(state__group__in=GRUP_SELESAI)
        .exclude(project__archived_at__isnull=False)
        .select_related("project", "workspace", "state")
        .distinct()
    )


def _sinkron_satu_orang(sambungan) -> dict:
    """Samakan kalender satu orang dengan keadaan work item-nya sekarang."""
    refresh_token = decrypt_data(sambungan.refresh_token)
    if not refresh_token:
        # decrypt_data menelan galat dan mengembalikan string kosong. Yang
        # paling mungkin: SECRET_KEY instance berubah sejak token disimpan,
        # persis yang terjadi pada password SMTP saat migrasi server 7 Agustus.
        raise RuntimeError(
            "refresh token tidak bisa didekripsi, kemungkinan SECRET_KEY berubah; "
            "pengguna harus menyambungkan ulang"
        )

    token = gcal.access_token(refresh_token)
    kal = sambungan.calendar_id
    dibuat = diubah = dihapus = 0

    seharusnya = {i.id: i for i in _work_item_milik(sambungan.user)}
    tercatat = {a.issue_id: a for a in AcaraKalender.objects.filter(user=sambungan.user)}

    # Buat yang belum ada, perbarui yang berubah.
    for issue_id, issue in seharusnya.items():
        judul = _judul(issue)
        acara = tercatat.get(issue_id)

        if acara is None:
            event_id = gcal.buat_acara(
                token, kal, judul, issue.target_date, _deskripsi(issue), _url(issue)
            )
            AcaraKalender.objects.create(
                user=sambungan.user,
                issue=issue,
                google_event_id=event_id,
                tenggat=issue.target_date,
                judul=judul,
            )
            dibuat += 1
            continue

        # Tidak berubah, tidak usah memanggil Google sama sekali. Tanpa
        # perbandingan ini, tiap putaran akan menembak API sebanyak jumlah work
        # item dikali jumlah orang, dan kuota harian habis tanpa guna.
        if acara.tenggat == issue.target_date and acara.judul == judul:
            continue

        gcal.ubah_acara(
            token, kal, acara.google_event_id, judul, issue.target_date,
            _deskripsi(issue), _url(issue),
        )
        acara.tenggat = issue.target_date
        acara.judul = judul
        acara.save(update_fields=["tenggat", "judul", "updated_at"])
        diubah += 1

    # Buang yang sudah tidak layak: selesai, dibatalkan, tenggatnya dicabut,
    # penugasannya dipindah, atau work item-nya dihapus.
    for issue_id, acara in tercatat.items():
        if issue_id in seharusnya:
            continue
        gcal.hapus_acara(token, kal, acara.google_event_id)
        acara.delete()
        dihapus += 1

    return {"dibuat": dibuat, "diubah": diubah, "dihapus": dihapus}


@shared_task
def sinkron_google_calendar():
    """Dijalankan berkala. Lihat beat_schedule di plane/celery.py."""
    if not _aktif():
        logger.info("Sinkron Google Calendar dilewati: ENABLE_GOOGLE_CALENDAR_SYNC belum diset ke 1")
        return {"aktif": False}

    total = {"orang": 0, "dibuat": 0, "diubah": 0, "dihapus": 0, "gagal": 0}

    for sambungan in KalenderGoogle.objects.select_related("user").filter(user__is_active=True):
        try:
            hasil = _sinkron_satu_orang(sambungan)
        except Exception as e:  # noqa: BLE001
            # Satu sambungan rusak tidak boleh menghentikan sisanya. Token yang
            # dicabut satu orang akan membuat 89 kalender lain berhenti terisi
            # kalau galatnya dibiarkan naik.
            total["gagal"] += 1
            log_exception(e)
            KalenderGoogle.objects.filter(pk=sambungan.pk).update(
                galat_terakhir=str(e)[:500], updated_at=timezone.now()
            )
            continue

        total["orang"] += 1
        for k in ("dibuat", "diubah", "dihapus"):
            total[k] += hasil[k]
        KalenderGoogle.objects.filter(pk=sambungan.pk).update(
            terakhir_sinkron=timezone.now(), galat_terakhir="", updated_at=timezone.now()
        )

    logger.info("Sinkron Google Calendar selesai: %s", total)
    return total
