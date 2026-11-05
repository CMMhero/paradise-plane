# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup

# Third party imports
from celery import shared_task
from django.core.mail import get_connection

# Django imports
from django.utils import timezone

# Module imports
from plane.db.models import EmailNotificationLog, Issue, User
from plane.license.utils.instance_value import email_aktif, get_email_configuration
from plane.settings.redis import redis_instance
from plane.utils.email_merek import avatar_untuk, bahasa_penerima, buat_pesan, render_email, url_preferensi
from plane.utils.email_pembaruan import susun_email_pembaruan
from plane.utils.email_utas import utas_untuk
from plane.utils.exception_logger import log_exception
from plane.utils.penerima_aktif import penerima_aktif


def remove_unwanted_characters(input_text):
    # Remove only control characters and potentially problematic characters for email subjects
    processed_text = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", input_text)
    return processed_text


# acquire and delete redis lock
def acquire_lock(lock_id, expire_time=300):
    redis_client = redis_instance()
    """Attempt to acquire a lock with a specified expiration time."""
    return redis_client.set(lock_id, "true", nx=True, ex=expire_time)


def release_lock(lock_id):
    """Release a lock."""
    redis_client = redis_instance()
    redis_client.delete(lock_id)


@shared_task
def stack_email_notification():
    # Kustomisasi Paradise: saklar God Mode ENABLE_EMAIL_BATCH. Menyala = semua
    # kabar satu penerima ditahan selama EMAIL_BATCH_DELAY_MINUTES lalu dikirim
    # sebagai SATU email (plane/bgtasks/email_antrean.py). Mati = jalur lama di bawah.
    from plane.utils.saklar_instance import ENABLE_EMAIL_BATCH, saklar_aktif

    if saklar_aktif(ENABLE_EMAIL_BATCH):
        from plane.bgtasks.email_antrean import sapu_antrean

        sapu_antrean()
        return

    # get all email notifications
    email_notifications = (
        EmailNotificationLog.objects.filter(processed_at__isnull=True).order_by("receiver", "created_at").values()
    )

    # Kustomisasi Paradise: baris persetujuan (`entity="approval"`) dikirim
    # lewat tugas khusus di bawah (templat dan bahasanya sendiri), satu email
    # per baris. Dikeluarkan dari digest umum supaya tidak terkirim ganda.
    for baris in [n for n in email_notifications if (n.get("entity") or "") == "approval"]:
        send_approval_email_notification.delay(email_log_id=str(baris.get("id")))
    email_notifications = [n for n in email_notifications if (n.get("entity") or "") != "approval"]

    # Create the below format for each of the issues
    # {"issue_id" : { "actor_id1": [ { data }, { data } ], "actor_id2": [ { data }, { data } ] }}

    # Convert to unique receivers list
    receivers = list(set([str(notification.get("receiver_id")) for notification in email_notifications]))
    processed_notifications = []
    # Loop through all the issues to create the emails
    for receiver_id in receivers:
        # Notification triggered for the receiver
        receiver_notifications = [
            notification for notification in email_notifications if str(notification.get("receiver_id")) == receiver_id
        ]
        # create payload for all issues
        payload = {}
        # Kustomisasi Paradise: id per work item. Dulu satu daftar untuk semua work
        # item penerima, jadi email work item pertama menandai baris work item lain
        # "terkirim" sebelum emailnya sendiri berangkat.
        ids_per_issue = {}
        for receiver_notification in receiver_notifications:
            payload.setdefault(receiver_notification.get("entity_identifier"), {}).setdefault(
                str(receiver_notification.get("triggered_by_id")), []
            ).append(receiver_notification.get("data"))
            # append processed notifications
            processed_notifications.append(receiver_notification.get("id"))
            ids_per_issue.setdefault(receiver_notification.get("entity_identifier"), []).append(
                str(receiver_notification.get("id"))
            )

        # Create emails for all the issues
        for issue_id, notification_data in payload.items():
            send_email_notification.delay(
                issue_id=str(issue_id),
                notification_data=notification_data,
                receiver_id=receiver_id,
                email_notification_ids=ids_per_issue.get(issue_id, []),
            )

    # Update the email notification log
    EmailNotificationLog.objects.filter(pk__in=processed_notifications).update(processed_at=timezone.now())


def create_payload(notification_data):
    # return format {"actor_id":  { "key": { "old_value": [], "new_value": [] } }}
    data = {}
    for actor_id, changes in notification_data.items():
        for change in changes:
            issue_activity = change.get("issue_activity")
            if issue_activity:  # Ensure issue_activity is not None
                field = issue_activity.get("field")
                old_value = str(issue_activity.get("old_value"))
                new_value = str(issue_activity.get("new_value"))

                # Append old_value if it's not empty and not already in the list
                if old_value:
                    (
                        data.setdefault(actor_id, {})
                        .setdefault(field, {})
                        .setdefault("old_value", [])
                        .append(old_value)
                        if old_value not in data.setdefault(actor_id, {}).setdefault(field, {}).get("old_value", [])
                        else None
                    )

                # Append new_value if it's not empty and not already in the list
                if new_value:
                    (
                        data.setdefault(actor_id, {})
                        .setdefault(field, {})
                        .setdefault("new_value", [])
                        .append(new_value)
                        if new_value not in data.setdefault(actor_id, {}).setdefault(field, {}).get("new_value", [])
                        else None
                    )

                if not data.get("actor_id", {}).get("activity_time", False):
                    data[actor_id]["activity_time"] = str(
                        datetime.fromisoformat(issue_activity.get("activity_time").rstrip("Z")).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    )

    return data


def _teks_sebutan(mention) -> str:
    """Teks pengganti satu mention-component di email.

    Kustomisasi Paradise (KEP-91): selain orang, editor kini bisa menyebut @all,
    #kanal, dan #work item. Versi lama memanggil `User.objects.get` untuk SEMUA
    mention, jadi satu sebutan non-orang menggagalkan seluruh email. Nama kanal
    privat tidak pernah ditulis: email bisa diteruskan ke siapa saja.
    """
    from plane.db.models import Ruang  # noqa: PLC0415
    from plane.utils.rujukan_obrolan import NAMA_PRIVAT, urai_uuid  # noqa: PLC0415

    jenis = mention.get("entity_name") or "user_mention"
    sah = urai_uuid([mention.get("entity_identifier")], 1)
    ident = sah[0] if sah else None

    if jenis == "everyone_mention":
        return "@all"
    if jenis == "channel_mention":
        ruang = Ruang.objects.filter(pk=ident).only("nama", "tipe").first() if ident else None
        if ruang is not None and ruang.tipe == Ruang.Tipe.KANAL and ruang.nama:
            return f"#{ruang.nama}"
        return f"#{NAMA_PRIVAT}"
    if jenis == "issue_mention":
        issue = Issue.objects.filter(pk=ident).select_related("project").first() if ident else None
        return f"{issue.project.identifier}-{issue.sequence_id}" if issue is not None else "#work-item"
    user = User.objects.filter(pk=ident).only("display_name").first() if ident else None
    return f"@{user.display_name}" if user is not None else "@unknown"


def process_mention(mention_component):
    soup = BeautifulSoup(mention_component, "html.parser")
    mentions = soup.find_all("mention-component")
    for mention in mentions:
        mention.replace_with(_teks_sebutan(mention))
    return str(soup)


def process_html_content(content):
    if content is None:
        return None
    processed_content_list = []
    for html_content in content:
        processed_content = process_mention(html_content)
        processed_content_list.append(processed_content)
    return processed_content_list


def aktor_dari_data(notification_data) -> list:
    """{actor_id: [data baris log]} -> blok aktor untuk `susun_email_pembaruan`.

    Kustomisasi Paradise: satu blok per aktor (perubahan + komentar), foto profil
    disisipkan CID lewat `konteks_pembaruan`. Dulu `avatar_url` ditempel ke
    `base_api` apa adanya: orang tanpa foto jadi `http://hostNone` (gambar pecah),
    yang punya foto jadi URL MinIO LAN.
    """
    aktor = []
    for actor_id, changes in create_payload(notification_data=notification_data).items():
        actor = User.objects.filter(pk=actor_id).select_related("avatar_asset").first()
        comment = changes.pop("comment", False)
        mention = changes.pop("mention", False)
        komentar = []
        if comment:
            komentar += [k for k in comment.get("new_value") or [] if k]
        if mention:
            komentar += [k for k in process_html_content(mention.get("new_value")) or [] if k]
        activity_time = changes.pop("activity_time")
        waktu = datetime.strptime(activity_time, "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
        aktor.append({"user": actor, "waktu": waktu, "changes": changes, "komentar": komentar})
    return aktor


@shared_task
def send_email_notification(issue_id, notification_data, receiver_id, email_notification_ids):
    # Convert UUIDs to a sorted, concatenated string
    sorted_ids = sorted(email_notification_ids)
    ids_str = "_".join(str(id) for id in sorted_ids)
    lock_id = f"send_email_notif_{issue_id}_{receiver_id}_{ids_str}"

    # acquire the lock for sending emails
    try:
        if acquire_lock(lock_id=lock_id):
            # get the redis instance
            ri = redis_instance()
            base_api = ri.get(str(issue_id)).decode() if ri.get(str(issue_id)) else None

            # Skip if base api is not present
            if not base_api:
                return

            receiver = User.objects.get(pk=receiver_id)
            issue = Issue.objects.get(pk=issue_id)
            if not penerima_aktif(receiver):
                # ENABLE_EMAIL_ACTIVE_ONLY: inbox sudah ditulis, email dilewati.
                release_lock(lock_id=lock_id)
                return

            subject, html_content, text_content, gambar = susun_email_pembaruan(
                issue, aktor_dari_data(notification_data), base_api, bahasa_penerima(receiver), receiver.email
            )
            utas = utas_untuk(issue, receiver.id)
            if utas:
                subject = utas[0]

            try:
                buat_pesan(
                    ke=receiver.email,
                    subjek=subject,
                    html=html_content,
                    teks=text_content,
                    gambar=gambar,
                    header=utas[1] if utas else None,
                ).send()
                logging.getLogger("plane.worker").info("Email Sent Successfully")

                # Update the logs
                EmailNotificationLog.objects.filter(pk__in=email_notification_ids).update(sent_at=timezone.now())

                # release the lock
                release_lock(lock_id=lock_id)
                return
            except Exception as e:
                log_exception(e)
                # release the lock
                release_lock(lock_id=lock_id)
                return
        else:
            logging.getLogger("plane.worker").info("Duplicate email received skipping")
            return
    except (Issue.DoesNotExist, User.DoesNotExist):
        release_lock(lock_id=lock_id)
        return
    except Exception as e:
        log_exception(e)
        release_lock(lock_id=lock_id)
        return


# ---------------------------------------------------------------------------
# Kustomisasi Paradise: email persetujuan (satu email per baris antrean).
#
# Bahasa mengikuti preferensi penerima (`User.language`), bukan bahasa
# pengirim: manajer berbahasa Inggris dan staf berbahasa Indonesia menerima
# teks masing-masing. String ada di bawah (id/en), bukan di templat, supaya
# templatnya satu dan logikanya tidak bercabang di HTML.
# ---------------------------------------------------------------------------

# Dua penerima, dua peran, jangan sampai tertukar (laporan user 3 Nov 2026:
# "approved work or needing my approval?"). Pengajuan pergi ke ATASAN dan
# meminta tindakan; keputusan pergi ke STAF dan cuma memberi kabar. Karena itu
# subjek pengajuan diawali "Perlu persetujuanmu" dan subjek keputusan diawali
# "Pekerjaanmu ...", supaya peran penerima terbaca dari kotak masuk tanpa membuka
# email. Yang diajukan selalu "tandai selesai" (KEP-55): staf menggeser ke Done,
# status tidak pindah sampai atasan menyetujui, ditolak = kembali ke In Progress.
_STRINGS_APPROVAL_ID = {
    "subject_diajukan": "Perlu persetujuanmu: {aktor} menandai {label} {judul} selesai",
    "subject_disetujui": "Pekerjaanmu disetujui: {label} {judul}",
    "subject_ditolak": "Pekerjaanmu ditolak: {label} {judul}",
    "heading_diajukan": "Menunggu persetujuanmu",
    "heading_disetujui": "Pekerjaanmu disetujui",
    "heading_ditolak": "Pekerjaanmu dikembalikan",
    "intro_diajukan": (
        "{aktor} menggeser tugas ini ke Done dan meminta kamu memeriksanya. Statusnya belum pindah "
        "sampai kamu memutuskan. Setujui untuk menandainya selesai, atau tolak dengan alasan untuk "
        "mengembalikannya ke In Progress."
    ),
    "intro_disetujui": (
        "{aktor} menyetujui pekerjaanmu. Tugas ini sekarang berstatus Done. Tidak ada yang perlu kamu lakukan."
    ),
    "intro_ditolak": (
        "{aktor} menolak pekerjaanmu dan mengembalikan tugas ini ke In Progress. Baca alasannya di bawah, "
        "perbaiki, lalu geser lagi ke Done untuk mengajukan ulang."
    ),
    "alasan_label": "Alasan penolakan",
    "cta_diajukan": "Periksa dan putuskan",
    "cta_diputuskan": "Buka tugas",
    "kaki_diajukan": "Kamu menerima email ini karena kamu atasan yang boleh menyetujui tugas di project ini.",
    "kaki_diputuskan": "Kamu menerima email ini karena kamu yang mengajukan tugas ini untuk disetujui.",
    "kaki_atur": "Atur email persetujuan di Profil → Notifikasi.",
}

_STRINGS_APPROVAL_EN = {
    "subject_diajukan": "Needs your approval: {aktor} marked {label} {judul} as done",
    "subject_disetujui": "Your work was approved: {label} {judul}",
    "subject_ditolak": "Your work was rejected: {label} {judul}",
    "heading_diajukan": "Waiting for your approval",
    "heading_disetujui": "Your work was approved",
    "heading_ditolak": "Your work was sent back",
    "intro_diajukan": (
        "{aktor} moved this work item to Done and asked you to review it. Its status won't change "
        "until you decide. Approve to mark it done, or reject with a reason to send it back to In Progress."
    ),
    "intro_disetujui": "{aktor} approved your work. This work item is now Done. Nothing else to do.",
    "intro_ditolak": (
        "{aktor} rejected your work and moved this work item back to In Progress. Read the reason below, "
        "fix it, then move it to Done again to resubmit."
    ),
    "alasan_label": "Rejection reason",
    "cta_diajukan": "Review and decide",
    "cta_diputuskan": "Open work item",
    "kaki_diajukan": "You received this email because you can approve work items in this project.",
    "kaki_diputuskan": "You received this email because you asked for approval on this work item.",
    "kaki_atur": "Manage approval emails in Profile → Notifications.",
}


def konteks_persetujuan(s, verb, nama_aktor, label, judul, alasan, url_tugas, url_antrean) -> dict:
    """Konteks templat `approval.html`. Murni: dipakai pengirim dan pratinjau."""
    kunci = "diajukan" if verb == "submitted" else ("disetujui" if verb == "approved" else "ditolak")
    diajukan = kunci == "diajukan"
    return {
        "s": s,
        "heading": s[f"heading_{kunci}"],
        "intro": s[f"intro_{kunci}"].format(aktor=nama_aktor),
        "subject": s[f"subject_{kunci}"].format(aktor=nama_aktor, label=label, judul=judul),
        "label": label,
        "judul": judul,
        "alasan": alasan,
        "tampilkan_alasan": kunci == "ditolak",
        "cta_label": s["cta_diajukan"] if diajukan else s["cta_diputuskan"],
        "cta_url": url_antrean if diajukan else url_tugas,
        "url_tugas": url_tugas,
        "kaki": f"{s['kaki_diajukan' if diajukan else 'kaki_diputuskan']} {s['kaki_atur']}",
    }


def render_approval(context, bahasa, aktor=None, email_penerima="", slug="", gambar=None):
    """(html, teks) `approval.html` di tata letak bersama; foto aktor masuk ke `gambar`."""
    avatar, _ = avatar_untuk(aktor, gambar=gambar) if aktor is not None else (None, None)
    preferensi = url_preferensi(slug)
    kaki = context["kaki"]
    if preferensi:
        # Footer bersama sudah memuat tautan "Atur notifikasi"; kalimat penunjuk
        # menu yang sama di atasnya cuma mengulang.
        kaki = kaki.replace(f" {context['s']['kaki_atur']}", "")
    return render_email(
        "emails/notifications/approval.html",
        {
            **context,
            "kaki": kaki,
            "aktor_avatar": avatar,
            # `judul` dipakai base.html untuk <title>; judul tugas untuk kartu
            # dipisah, dulu kartu ikut menampilkan seluruh subjek email.
            "judul_tugas": context["judul"],
            "judul": context["subject"],
            "pratajuk": context["intro"],
            "url_preferensi": preferensi,
            "email_penerima": email_penerima,
        },
        bahasa,
    )


def susun_email_persetujuan(baris) -> dict | None:
    """{issue, subject, html, teks, gambar} untuk satu baris log persetujuan; None kalau work item hilang."""
    import os

    from django.conf import settings

    receiver = baris.receiver
    aktor = baris.triggered_by
    data = baris.data or {}
    info = data.get("issue", {})
    aktivitas = data.get("issue_activity", {})
    issue = Issue.objects.select_related("project", "project__workspace").filter(pk=info.get("id")).first()
    if issue is None:
        return None

    bahasa = bahasa_penerima(receiver)
    s = _STRINGS_APPROVAL_ID if bahasa == "id" else _STRINGS_APPROVAL_EN
    label = f"{issue.project.identifier}-{issue.sequence_id}"
    verb = str(aktivitas.get("verb") or "submitted")
    nama_aktor = getattr(aktor, "display_name", None) or getattr(aktor, "email", None) or "?"
    dasar = (settings.APP_BASE_URL or os.environ.get("WEB_URL") or "").rstrip("/")
    slug = issue.project.workspace.slug
    url_tugas = f"{dasar}/{slug}/projects/{issue.project.id}/issues/{issue.id}"
    url_antrean = f"{dasar}/{slug}/projects/{issue.project.id}/persetujuan"
    context = konteks_persetujuan(
        s, verb, nama_aktor, label, issue.name, str(aktivitas.get("issue_comment") or ""), url_tugas, url_antrean
    )
    gambar = []
    html_content, text_content = render_approval(context, bahasa, aktor, receiver.email, slug, gambar)
    return {"issue": issue, "subject": context["subject"], "html": html_content, "teks": text_content, "gambar": gambar}


@shared_task
def send_approval_email_notification(email_log_id):
    """Kirim satu email persetujuan untuk satu baris `EmailNotificationLog`."""
    lock_id = f"send_approval_email_{email_log_id}"
    try:
        if not acquire_lock(lock_id=lock_id):
            logging.getLogger("plane.worker").info("Duplicate approval email skipping")
            return
        try:
            baris = (
                EmailNotificationLog.objects.select_related("receiver", "triggered_by")
                .filter(pk=email_log_id, processed_at__isnull=True)
                .first()
            )
            if baris is None:
                return
            receiver = baris.receiver
            pesan = susun_email_persetujuan(baris)
            if pesan is None or not penerima_aktif(receiver):
                # Work item hilang, atau ENABLE_EMAIL_ACTIVE_ONLY menahan email
                # orang yang lama tak aktif (inbox sudah ditulis).
                EmailNotificationLog.objects.filter(pk=baris.pk).update(processed_at=timezone.now())
                return
            issue = pesan["issue"]
            subject = pesan["subject"]
            html_content, text_content, gambar = pesan["html"], pesan["teks"], pesan["gambar"]

            (
                EMAIL_HOST,
                EMAIL_HOST_USER,
                EMAIL_HOST_PASSWORD,
                EMAIL_PORT,
                EMAIL_USE_TLS,
                EMAIL_USE_SSL,
                EMAIL_FROM,
            ) = get_email_configuration()
            if not email_aktif(EMAIL_HOST):
                # Tanpa SMTP, menahan baris berarti mengulanginya tiap 5 menit
                # selamanya. Tandai selesai supaya antrean tidak macet; email
                # memang tidak bisa dikirim tanpa pengirim yang dikonfigurasi.
                EmailNotificationLog.objects.filter(pk=baris.pk).update(processed_at=timezone.now())
                logging.getLogger("plane.worker").warning("Approval email skipped: SMTP not configured")
                return
            connection = get_connection(
                host=EMAIL_HOST,
                port=int(EMAIL_PORT),
                username=EMAIL_HOST_USER,
                password=EMAIL_HOST_PASSWORD,
                use_tls=str(EMAIL_USE_TLS) == "1",
                use_ssl=str(EMAIL_USE_SSL) == "1",
            )
            utas = utas_untuk(issue, receiver.id, dari=EMAIL_FROM or "")
            if utas:
                subject = utas[0]
            buat_pesan(
                ke=receiver.email,
                subjek=remove_unwanted_characters(subject),
                html=html_content,
                teks=text_content,
                koneksi=connection,
                dari=EMAIL_FROM,
                gambar=gambar,
                header=utas[1] if utas else None,
            ).send()
            logging.getLogger("plane.worker").info("Approval email sent successfully")
            EmailNotificationLog.objects.filter(pk=baris.pk).update(
                processed_at=timezone.now(), sent_at=timezone.now()
            )
        finally:
            release_lock(lock_id=lock_id)
    except Exception as e:
        log_exception(e)
        try:
            release_lock(lock_id=lock_id)
        except Exception:  # noqa: BLE001
            pass
