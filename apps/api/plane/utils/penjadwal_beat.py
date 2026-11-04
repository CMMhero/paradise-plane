# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: penjadwal beat yang membuang entri basi
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""`DatabaseScheduler` yang membersihkan entri basi sebelum mulai (vault BUG-12).

`django_celery_beat.DatabaseScheduler` menyalin `beat_schedule` di plane/celery.py
ke tabel PeriodicTask tiap kali beat menyala, tapi TIDAK PERNAH menghapus baris
yang namanya sudah tidak ada di kode. Entri yang dihapus atau diganti nama tetap
berdetak selamanya: `create-recurring-issues` memicu "unregistered task" tiap 15
menit, dan crontab UTC lama pengingat/ringkasan (sebelum KEP-83) akan mengirim
email ganda di samping penjadwal kantor yang baru.

Yang dihapus, hanya kalau namanya TIDAK ada di `beat_schedule` kode:

1. nama di `JADWAL_PENSIUN` (entri yang memang pernah kita hapus dari kode), dan
2. baris yang task-nya tidak terdaftar di worker (tidak akan pernah bisa jalan).

Baris lain yang dibuat kode atau orang di luar `beat_schedule` (mis. lewat Django
admin) dengan task yang terdaftar DIBIARKAN. Dihapus, bukan dinonaktifkan:
`update_or_create` milik django_celery_beat tidak menyalakan ulang baris yang
mati, jadi entri nonaktif yang kelak dipakai lagi oleh kode akan diam selamanya.

Sebelum crontab ringkasan lama dihapus, `last_run_at`-nya dibaca: yang sudah jalan
pada tanggal kantor hari ini ditandai selesai di penjadwal kantor
(`jadwal_kantor.tandai_sudah_dikirim`), supaya hari deploy tidak mengirim ringkasan
kedua. Yang belum jalan hari itu dibiarkan, jadi penjadwal kantor mengirimnya.
"""

import logging

from django.db import DatabaseError, transaction
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, PeriodicTasks
from django_celery_beat.schedulers import DatabaseScheduler

logger = logging.getLogger("plane")

# Entri beat yang pernah ada di plane/celery.py lalu dihapus. Tambahkan nama di
# sini setiap kali sebuah entri dihapus atau diganti nama.
JADWAL_PENSIUN = frozenset(
    {
        "create-recurring-issues",  # 4059f6e083
        # KEP-83: diganti satu detak `jadwal-kantor` (plane/bgtasks/jadwal_kantor.py).
        "pengingat-tenggat",
        "ringkasan-harian",
        "ringkasan-sore",
        "ringkasan-direktur",
    }
)
# Crontab ringkasan lama -> slot penjadwal kantor yang menggantikannya. Pengingat
# tenggat SENGAJA tidak ada: task-nya mencatat per penerima (PengingatTenggat,
# Notification), jadi jalan kedua di hari deploy hanya mengirim yang belum.
CRONTAB_LAMA_KE_SLOT = {
    "ringkasan-harian": "ringkasan-pagi",
    "ringkasan-sore": "ringkasan-sore",
    "ringkasan-direktur": "ringkasan-direktur",
}
# Dipasang django_celery_beat sendiri (`install_default_entries`), bukan oleh kode kita.
BAWAAN_CELERY = frozenset({"celery.backend_cleanup"})


def entri_basi(baris, nama_kode, task_terdaftar) -> list:
    """Nama entri yang harus dibuang. Murni, supaya bisa diuji tanpa database.

    `baris`: [(nama, task)] dari PeriodicTask. `task_terdaftar`: None = registry tidak
    bisa dimuat, jadi hanya `JADWAL_PENSIUN` yang dibuang (jangan menebak).
    """
    basi = []
    for nama, task in baris:
        if nama in nama_kode or nama in BAWAAN_CELERY:
            continue
        if nama in JADWAL_PENSIUN or (task_terdaftar is not None and task not in task_terdaftar):
            basi.append(nama)
    return sorted(basi)


def _task_terdaftar(app):
    try:
        app.loader.import_default_modules()
        return set(app.tasks)
    except Exception:  # noqa: BLE001
        logger.exception("Registry task tidak bisa dimuat; hanya entri JADWAL_PENSIUN yang dibersihkan")
        return None


def slot_sudah_jalan_hari_ini(jalan_terakhir, hari_ini, zona) -> list:
    """Slot kantor yang crontab lamanya sudah jalan pada `hari_ini` (tanggal kantor). Murni.

    `jalan_terakhir`: {nama entri lama: last_run_at (aware) atau None}.
    """
    hasil = []
    for nama, waktu in jalan_terakhir.items():
        slot = CRONTAB_LAMA_KE_SLOT.get(nama)
        if slot and waktu is not None and waktu.astimezone(zona).date() == hari_ini:
            hasil.append(slot)
    return sorted(hasil)


def _tandai_crontab_lama(basi) -> None:
    """Penanda selesai untuk ringkasan yang crontab lamanya sudah mengirim hari ini.

    Galat di sini tidak menahan penghapusan: crontab lama yang dibiarkan hidup
    mengirim ganda TIAP hari, sedangkan penanda yang gagal paling buruk membuat
    satu ringkasan ganda di hari deploy.
    """
    from plane.bgtasks.jadwal_kantor import tandai_sudah_dikirim
    from plane.utils.setelan_instance import zona_kantor

    lama = [n for n in basi if n in CRONTAB_LAMA_KE_SLOT]
    if not lama:
        return
    try:
        # Savepoint: galat di sini tidak boleh meracuni transaksi pemanggil.
        with transaction.atomic():
            jalan_terakhir = dict(PeriodicTask.objects.filter(name__in=lama).values_list("name", "last_run_at"))
            zona = zona_kantor()
            hari_ini = timezone.now().astimezone(zona).date()
            slot = slot_sudah_jalan_hari_ini(jalan_terakhir, hari_ini, zona)
            tandai_sudah_dikirim(hari_ini, slot, "crontab lama sudah jalan hari ini (last_run_at)")
    except DatabaseError:
        logger.exception("Gagal menandai ringkasan yang sudah dikirim crontab lama")


def bersihkan_jadwal_basi(app) -> list:
    """Hapus entri basi dari PeriodicTask. Tidak pernah melempar: beat harus tetap menyala."""
    try:
        baris = list(PeriodicTask.objects.values_list("name", "task"))
        basi = entri_basi(baris, set(app.conf.beat_schedule), _task_terdaftar(app))
        if basi:
            _tandai_crontab_lama(basi)
            PeriodicTask.objects.filter(name__in=basi).delete()
            PeriodicTasks.update_changed()
            logger.warning("Entri beat basi dihapus: %s", ", ".join(basi))
        return basi
    except DatabaseError:
        logger.exception("Gagal membersihkan entri beat basi")
        return []


class PenjadwalDatabase(DatabaseScheduler):
    """DatabaseScheduler + `bersihkan_jadwal_basi` sebelum jadwal dibaca pertama kali."""

    def setup_schedule(self):
        bersihkan_jadwal_basi(self.app)
        super().setup_schedule()
