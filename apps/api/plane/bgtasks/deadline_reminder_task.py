# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pengingat tenggat
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Pengingat tenggat work item, lewat email dan (sejak 2026-11-02) inbox di aplikasi.

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
from datetime import timedelta

from django.utils import timezone

from plane.db.models import Issue, Notification, PengingatTenggat, SEMUA_TITIK
from plane.utils.exception_logger import log_exception
from plane.utils.preferensi_email import boleh_email, penyaring
from plane.utils.saklar_instance import ENABLE_DEADLINE_REMINDER, saklar_aktif

from .deadline_reminder_email import kirim_email_pengingat
from celery import shared_task

logger = logging.getLogger("plane")

# Baris inbox tenggat (tulis_inbox_tenggat). `field` dibaca kartu inbox di apps/web.
SENDER_TENGGAT = "in_app:deadline"
FIELD_TENGGAT = "deadline"
# H-1, hari H, lalu terlambat H+1, H+3, H+7. Lebih jarang daripada email.
TITIK_INBOX = (-1, 0, 1, 3, 7)

# Tugas yang sudah selesai atau dibatalkan tidak perlu diingatkan lagi,
# termasuk yang sudah lewat tenggat.
GRUP_SELESAI = ["completed", "cancelled"]

# Saklar pengaman, MATI secara bawaan. Fitur ini mengirim email massal ke
# seluruh karyawan, jadi menyalakannya harus tindakan sadar, bukan efek samping
# dari sebuah deploy. Diatur Super Admin di God Mode > Fitur & otomasi, berlaku
# di putaran berikutnya tanpa membuat ulang container.
#
# Saklar ini hanya menjaga tugas terjadwal. `kirim_email_pengingat()` tetap bisa
# dipanggil langsung untuk mengirim contoh ke satu alamat saat pengujian.
def _aktif() -> bool:
    return saklar_aktif(ENABLE_DEADLINE_REMINDER)


def _label_titik(titik: int) -> str:
    if titik == 0:
        return "jatuh tempo hari ini"
    if titik < 0:
        return f"tinggal {-titik} hari lagi"
    return f"TERLAMBAT {titik} hari"


def _orang_tugas(issue):
    """Penanggung jawab + pembuat, aktif dan bukan bot. Himpunan: diri sendiri dihitung sekali."""
    orang = {a for a in issue.assignees.filter(is_active=True, is_bot=False)}
    if issue.created_by and issue.created_by.is_active and not issue.created_by.is_bot:
        orang.add(issue.created_by)
    return orang


def _baris_inbox(issue, penerima_id, titik, tenggat):
    data_issue = {
        "id": str(issue.id),
        "name": issue.name,
        "identifier": issue.project.identifier,
        "sequence_id": issue.sequence_id,
        "state_name": issue.state.name if issue.state else "",
        "state_group": issue.state.group if issue.state else "",
    }
    return Notification(
        workspace_id=issue.workspace_id,
        project_id=issue.project_id,
        sender=_sender_inbox(titik, tenggat),
        triggered_by=None,
        receiver_id=penerima_id,
        entity_identifier=issue.id,
        entity_name="issue",
        title="",
        data={
            "issue": data_issue,
            "issue_activity": {
                "id": None,
                # Dibaca kartu inbox (apps/web notification-card/content.tsx):
                # new_value = selisih hari terhadap tenggat, negatif = belum lewat.
                "verb": "overdue" if titik > 0 else "due",
                "field": FIELD_TENGGAT,
                "actor": None,
                "new_value": str(titik),
                "old_value": "",
                "new_identifier": None,
                "old_identifier": None,
            },
        },
    )


def _sender_inbox(titik, tenggat) -> str:
    # Tanggal tenggat ikut di sender: kalau tenggat digeser, titik yang sama untuk
    # tenggat baru adalah kabar baru, bukan duplikat.
    return f"{SENDER_TENGGAT}:{titik}:{tenggat.isoformat()}"


def tulis_inbox_tenggat(hari_ini):
    """Baris inbox "jatuh tempo" dan "terlambat" untuk yang saklar `inbox_deadline`-nya hidup.

    Keputusan user 2026-11-02: kabar terlambat juga harus terlihat di inbox, bukan
    cuma lewat email. Tidak mengirim email apa pun, jadi TIDAK ikut rem
    ENABLE_DEADLINE_REMINDER. Titiknya lebih jarang daripada email (`TITIK_INBOX`):
    inbox yang terisi delapan baris per tugas berhenti dibaca.
    """
    ditulis = 0
    for titik in TITIK_INBOX:
        tenggat = hari_ini - timedelta(days=titik)
        antrian = list(
            Issue.issue_objects.filter(target_date=tenggat)
            .exclude(state__group__in=GRUP_SELESAI)
            .exclude(project__archived_at__isnull=False)
            .select_related("project", "workspace", "state", "created_by")
            .prefetch_related("assignees")
        )
        if not antrian:
            continue
        orang = {issue.id: {o.id for o in _orang_tugas(issue)} for issue in antrian}
        boleh_inbox = penyaring(set().union(*orang.values()), "inbox_deadline")
        sender = _sender_inbox(titik, tenggat)
        sudah = set(
            Notification.objects.filter(
                sender=sender, entity_identifier__in=[i.id for i in antrian]
            ).values_list("entity_identifier", "receiver_id")
        )
        baru = [
            _baris_inbox(issue, uid, titik, tenggat)
            for issue in antrian
            for uid in orang[issue.id] & boleh_inbox
            if (issue.id, uid) not in sudah
        ]
        Notification.objects.bulk_create(baru, batch_size=100)
        ditulis += len(baru)
    return ditulis


def _penerima(issue):
    """Siapa yang diingatkan: yang dikerjai tugasnya, dan yang memberi tugas.

    Keputusan user 2026-08-11. Kalau seseorang memberi tugas ke dirinya sendiri,
    ia tetap menerima satu email, bukan dua, karena dikumpulkan sebagai himpunan.

    Bot dan akun nonaktif dibuang: mengirim ke akun mati hanya menghasilkan
    bounce yang mengotori reputasi pengirim.

    Lalu disaring saklar `deadline_reminder` yang berlaku (keputusan user
    2026-10-30): hidup untuk staf, mati untuk pimpinan kecuali dinyalakan sendiri.
    """
    return {o for o in _orang_tugas(issue) if boleh_email(o.id, "deadline_reminder")}


@shared_task
def kirim_pengingat_tenggat():
    """Dijalankan sekali sehari. Lihat beat_schedule di plane/celery.py.

    Menghitung ulang dari `target_date` yang berlaku HARI INI, bukan dari
    jadwal yang disimpan di depan. Jadi kalau tenggat digeser, pengingatnya
    ikut bergeser sendiri tanpa perlu ada yang membatalkan jadwal lama.
    """
    hari_ini = timezone.localtime(timezone.now()).date()
    try:
        inbox = tulis_inbox_tenggat(hari_ini)
        logger.info("Inbox tenggat %s: %s baris", hari_ini, inbox)
    except Exception as e:  # noqa: BLE001
        # Inbox gagal tidak boleh menahan email pengingat.
        log_exception(e)

    if not _aktif():
        logger.info("Pengingat tenggat dilewati: ENABLE_DEADLINE_REMINDER mati di God Mode")
        return {"aktif": False}

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
