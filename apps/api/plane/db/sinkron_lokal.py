# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: migrasi + changelog otomatis di dev lokal
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Dev lokal: migrasi dan changelog diterapkan sendiri, tanpa perintah.

Tanpa ini, migrasi yang ditulis di tengah sesi tidak pernah diterapkan sampai
seseorang ingat menjalankan `migrate` atau `up migrator`, dan `api` macet di
"Waiting for database migrations" begitu ia dibuat ulang. Changelog juga cuma
terbit saat container start, jadi versi yang dinaikkan di tengah sesi tidak
pernah muncul di kanal Changelog lokal.

Cara kerja: saat `runserver` memulai proses anaknya (sinyal
`autoreload_started`), sinkron dijalankan sekali, lalu satu thread daemon
memeriksa sidik berkas tiap POLL_DETIK: nama + mtime semua `migrations/*.py`,
`release_notes/*.json`, dan `package.json`. Berubah = sinkron lagi.

Kenapa thread sendiri, bukan `reloader.watch_dir`: StatReloader Django sengaja
MENGABAIKAN berkas yang baru pertama terlihat ("first seen"), jadi migrasi
BARU tidak pernah memicu muat ulang. Terbukti 5 Nov 2026 dengan berkas uji.

Hanya jalan di bawah `runserver` (gunicorn tidak pernah mengirim sinyal itu)
dan hanya kalau `DEBUG` menyala, jadi produksi tidak tersentuh. Produksi diurus
`paradise/bin/deploy.sh`.
"""

import logging
import threading
import time
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.utils.autoreload import autoreload_started

logger = logging.getLogger("plane.api")

AKAR_API = Path(__file__).resolve().parents[2]
POLL_DETIK = 2.0
# Berkas yang sedang ditulis editor/agen: tunggu sebentar sesudah perubahan
# terakhir supaya migrasi setengah jadi tidak ikut diterapkan.
TENANG_DETIK = 1.5


def berkas_diawasi() -> list[Path]:
    hasil = [AKAR_API / "package.json"]
    for app in apps.get_app_configs():
        hasil += sorted((Path(app.path) / "migrations").glob("*.py"))
    hasil += sorted((AKAR_API / "plane" / "release_notes").glob("*.json"))
    return hasil


def sidik() -> tuple:
    hasil = []
    for berkas in berkas_diawasi():
        try:
            hasil.append((str(berkas), berkas.stat().st_mtime_ns))
        except OSError:
            continue
    return tuple(hasil)


def sinkronkan() -> None:
    """Migrasi lalu changelog. Galat dicatat, server tetap jalan."""
    try:
        call_command("migrate", interactive=False, verbosity=0)
        logger.info("sinkron lokal: migrasi lengkap")
    except Exception:  # noqa: BLE001
        logger.exception("sinkron lokal: migrate gagal, perbaiki migrasinya lalu simpan ulang")
        return
    try:
        call_command("terbitkan_changelog")
    except Exception:  # noqa: BLE001
        logger.exception("sinkron lokal: terbitkan_changelog gagal")
    finally:
        connection.close()


def awasi(awal: tuple) -> None:
    terakhir = awal
    while True:
        time.sleep(POLL_DETIK)
        kini = sidik()
        if kini == terakhir:
            continue
        time.sleep(TENANG_DETIK)
        kini = sidik()
        terakhir = kini
        # Modul migrasi yang sudah diimpor proses ini tetap versi lama; migrasi
        # yang DIUBAH (bukan baru) baru terbaca sesudah runserver memuat ulang.
        sinkronkan()


def saat_reloader_mulai(sender, **kwargs) -> None:
    if not settings.DEBUG:
        return
    awal = sidik()
    sinkronkan()
    threading.Thread(target=awasi, args=(awal,), name="paradise-sinkron-lokal", daemon=True).start()


def pasang() -> None:
    autoreload_started.connect(saat_reloader_mulai, dispatch_uid="paradise_sinkron_lokal")
