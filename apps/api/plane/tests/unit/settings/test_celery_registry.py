# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: penjaga pendaftaran task
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tiap task di beat_schedule WAJIB benar-benar terdaftar di worker.

Ini menutup kegagalan yang bentuknya paling jahat: beat menjadwalkan dengan
benar, worker menerima pesannya, lalu MEMBUANGNYA dengan "Received unregistered
task" dan mencatatnya sebagai ERROR di tempat yang tidak dilihat siapa pun.
Tidak ada gejala di layar. Fiturnya cuma diam.

Terjadi 18 Agt 2026 pada `chat_notification_task`: saklarnya dinyalakan di
produksi, dikira beres, dan baru ketahuan sesudah dua putaran lewat tanpa satu
email pun terkirim. Komentar peringatan di atas CELERY_IMPORTS sudah ada sejak
sebelum itu dan tetap terlewat. Komentar tidak bisa menggagalkan build.

Terulang pada `notifikasi_retensi` (2.14.0 sampai 2.15.2), kali ini dengan uji
ini sudah ada: pemeriksaannya jalan di dalam proses pytest, dan berkas uji task
itu sendiri mengimpor modulnya saat dikumpulkan, jadi registry-nya sudah terisi.
Karena itu pemeriksaan sekarang jalan di proses Python baru.

Yang diperiksa adalah REGISTRY, bukan isi tuple CELERY_IMPORTS. Bedanya nyata:
`deletion_task` tidak pernah ada di tuple itu tapi tetap terdaftar karena
`plane/db/mixins.py` mengimpornya, dan tiap model mengimpor mixin itu. Uji yang
membaca tuple akan menuduhnya rusak padahal sehat. `import_default_modules()`
adalah persis yang dijalankan worker sungguhan saat menyala.
"""

# Python imports
import json
import subprocess
import sys
from pathlib import Path

# Persis langkah worker saat menyala: muat Django dan CELERY_IMPORTS, lalu lihat
# apa yang akhirnya ada di registry.
_SKRIP = """
import json
import django

django.setup()

from plane.celery import app

app.loader.import_default_modules()
dijadwalkan = {entri["task"] for entri in app.conf.beat_schedule.values()}
print(json.dumps(sorted(dijadwalkan - set(app.tasks))))
"""


def test_semua_task_terjadwal_benar_benar_terdaftar():
    hasil = subprocess.run(
        [sys.executable, "-c", _SKRIP],
        cwd=Path(__file__).resolve().parents[4],  # apps/api
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert hasil.returncode == 0, hasil.stderr
    hilang = json.loads(hasil.stdout.strip().splitlines()[-1])

    assert not hilang, (
        "Task ini dijadwalkan di beat tapi TIDAK terdaftar, jadi worker akan "
        "membuangnya diam-diam sebagai 'Received unregistered task'. Tambahkan "
        "modulnya ke CELERY_IMPORTS di plane/settings/common.py: " + ", ".join(hilang)
    )
