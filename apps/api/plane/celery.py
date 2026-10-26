# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import os
import logging
from datetime import timedelta

# Third party imports
from celery import Celery
from pythonjsonlogger.json import JsonFormatter
from celery.signals import after_setup_logger, after_setup_task_logger
from celery.schedules import crontab, schedule

# Module imports
from plane.settings.redis import redis_instance

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plane.settings.production")

ri = redis_instance()

# Configurable metrics push interval (in minutes)
# Default: 360 (6 hours), set to 5 for development/testing
def _get_metrics_push_interval_minutes() -> int:
    raw = os.environ.get("METRICS_PUSH_INTERVAL_MINUTES", "360")
    try:
        value = int(raw)
        # Cap at 10,000,000 minutes to prevent timedelta(minutes=...) OverflowError
        # on arbitrarily large inputs while still allowing multi-year intervals.
        return value if 0 < value <= 10_000_000 else 360
    except (ValueError, OverflowError):
        return 360

METRICS_PUSH_INTERVAL_MINUTES = _get_metrics_push_interval_minutes()

app = Celery("plane")

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.beat_schedule = {
    # Sapuan tagihan lewat tempo. Harian sudah cukup: jatuh tempo dan tenggang
    # dihitung dalam hari, jadi menjalankannya lebih sering tidak mengubah hasil.
    # Hanya berarti di deployment pemilik; di instance pelanggan tabelnya tidak
    # ada dan task-nya berhenti sendiri.
    "sapu-tagihan-lewat-tempo": {
        "task": "plane.bgtasks.billing_task.sapu_tagihan_lewat_tempo",
        "schedule": crontab(hour=4, minute=0),
    },
    # Denyut ke bidang kendali. Mati sendiri kalau CONTROL_PLANE_URL tidak
    # disetel, jadi aman berjalan di kolam gratis maupun mesin pengembang.
    # Tiap jam, bukan harian: pelanggan yang baru menaikkan tingkatan tidak
    # pantas menunggu sampai besok untuk bisa memakai yang sudah dibayarnya.
    "denyut-bidang-kendali": {
        "task": "plane.bgtasks.control_plane_heartbeat.denyut_bidang_kendali",
        "schedule": crontab(minute=0),
    },
    # Rem 3 kolam gratis. Harian sudah cukup: ambangnya puluhan hari, jadi
    # menjalankannya lebih sering hanya menambah sapuan tanpa mengubah hasil.
    # 03:00 dipilih supaya tidak menabrak jam kerja mana pun.
    "sapu-workspace-tidur": {
        "task": "plane.bgtasks.dormancy_task.sapu_workspace_tidur",
        "schedule": crontab(hour=3, minute=0),
    },
    # Intra day recurring jobs
    "check-every-five-minutes-to-send-email-notifications": {
        "task": "plane.bgtasks.email_notification_task.stack_email_notification",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
    # Paradise: buat work item berulang dari template
    "create-recurring-issues": {
        "task": "plane.bgtasks.recurring_issue_task.create_recurring_issues",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    # Paradise: buang riwayat login >3 bulan, peringatkan sebelum dibuang.
    # 17:00 UTC = 00:00 WIB, jam yang sama dengan backup harian.
    "bersihkan-login-activity": {
        "task": "plane.bgtasks.login_activity_retention.bersihkan_login_activity",
        "schedule": crontab(hour=17, minute=0),
    },
    # Paradise: pengingat tenggat 8 titik, H-7 sampai H+7.
    # 01:00 UTC = 08:00 WIB, saat orang baru membuka email. Sengaja BUKAN tengah
    # malam: pengingat yang tiba saat semua orang tidur akan tenggelam di bawah
    # email semalaman sebelum sempat dibaca.
    "pengingat-tenggat": {
        "task": "plane.bgtasks.deadline_reminder_task.kirim_pengingat_tenggat",
        "schedule": crontab(hour=1, minute=0),
    },
    # Paradise: satu email ringkasan harian per orang yang MENYALAKANNYA
    # (hari ini, 7 hari ke depan, terlambat). Senin-Jumat 08.30 Jakarta.
    # Celery berjalan di UTC (CELERY_TIMEZONE = TIME_ZONE = "UTC"), jadi 08.30 WIB
    # = 01.30 UTC. Tanggalnya sama di kedua zona, jadi day_of_week tetap benar.
    "ringkasan-harian": {
        "task": "plane.bgtasks.daily_digest_task.kirim_ringkasan_harian",
        "schedule": crontab(hour=1, minute=30, day_of_week="mon-fri"),
    },
    # Paradise: dorong tenggat ke Google Calendar tiap
    # orang yang menyambungkan akunnya.
    #
    # Tiap 15 menit, bukan harian: ini menyamakan keadaan, bukan mengirim
    # pemberitahuan. Orang yang menggeser tenggat pagi ini berharap kalendernya
    # ikut bergeser hari ini juga, bukan besok pagi. Putarannya murah karena
    # work item yang tidak berubah dilewati tanpa memanggil API Google.
    "sinkron-google-calendar": {
        "task": "plane.bgtasks.google_calendar_sync.sinkron_google_calendar",
        "schedule": crontab(minute="*/15"),
    },
    # Paradise: email untuk pesan Obrolan yang tidak
    # dibaca-baca. Tiap 5 menit, tapi yang mengatur banjirnya bukan jadwal ini
    # melainkan dua rem di dalam tugasnya: pesan baru diberitahukan setelah diam
    # 10 menit, dan satu orang tidak dikirimi email lagi sebelum lewat 1 jam.
    "email-obrolan": {
        "task": "plane.bgtasks.chat_notification_task.kirim_pemberitahuan_pesan",
        "schedule": crontab(minute="*/5"),
    },
    "push-instance-metrics": {
        "task": "plane.license.bgtasks.telemetry_metrics.push_instance_metrics",
        "schedule": schedule(run_every=timedelta(minutes=METRICS_PUSH_INTERVAL_MINUTES)),
    },
    # Occurs once every day
    "check-every-day-to-delete-hard-delete": {
        "task": "plane.bgtasks.deletion_task.hard_delete",
        "schedule": crontab(hour=0, minute=0),  # UTC 00:00
    },
    "check-every-day-to-archive-and-close": {
        "task": "plane.bgtasks.issue_automation_task.archive_and_close_old_issues",
        "schedule": crontab(hour=1, minute=0),  # UTC 01:00
    },
    "check-every-day-to-delete_exporter_history": {
        "task": "plane.bgtasks.exporter_expired_task.delete_old_s3_link",
        "schedule": crontab(hour=1, minute=30),  # UTC 01:30
    },
    "check-every-day-to-delete-file-asset": {
        "task": "plane.bgtasks.file_asset_task.delete_unuploaded_file_asset",
        "schedule": crontab(hour=2, minute=0),  # UTC 02:00
    },
    "check-every-day-to-delete-api-logs": {
        "task": "plane.bgtasks.cleanup_task.delete_api_logs",
        "schedule": crontab(hour=2, minute=30),  # UTC 02:30
    },
    "check-every-day-to-delete-email-notification-logs": {
        "task": "plane.bgtasks.cleanup_task.delete_email_notification_logs",
        "schedule": crontab(hour=2, minute=45),  # UTC 02:45
    },
    "check-every-day-to-delete-page-versions": {
        "task": "plane.bgtasks.cleanup_task.delete_page_versions",
        "schedule": crontab(hour=3, minute=0),  # UTC 03:00
    },
    "check-every-day-to-delete-issue-description-versions": {
        "task": "plane.bgtasks.cleanup_task.delete_issue_description_versions",
        "schedule": crontab(hour=3, minute=15),  # UTC 03:15
    },
    "check-every-day-to-delete-webhook-logs": {
        "task": "plane.bgtasks.cleanup_task.delete_webhook_logs",
        "schedule": crontab(hour=3, minute=30),  # UTC 03:30
    },
    "check-every-day-to-delete-exporter-history": {
        "task": "plane.bgtasks.exporter_expired_task.delete_old_s3_link",
        "schedule": crontab(hour=3, minute=45),  # UTC 03:45
    },
}


# Setup logging
@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    formatter = JsonFormatter('"%(levelname)s %(asctime)s %(module)s %(name)s %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(fmt=formatter)
    logger.addHandler(handler)


@after_setup_task_logger.connect
def setup_task_loggers(logger, *args, **kwargs):
    formatter = JsonFormatter('"%(levelname)s %(asctime)s %(module)s %(name)s %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(fmt=formatter)
    logger.addHandler(handler)


# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

app.conf.beat_scheduler = "django_celery_beat.schedulers.DatabaseScheduler"
