# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: jadwal kantor (KEP-83)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Penjadwal pengingat tenggat dan ringkasan email menurut jam kantor di God Mode.

Dulu tiap pekerjaan punya crontab UTC tetap di plane/celery.py (01:00, 01:30,
10:30 UTC). Sejak KEP-83 jam, hari, dan zona waktunya diatur Super Admin, jadi
crontab tetap tidak cukup: beat hanya mendetakkan `jalankan_jadwal_kantor` tiap
5 menit, dan task itu yang memutuskan slot mana yang jatuh tempo.

Aturan satu slot:

- jatuh tempo kalau jam kantor sekarang (OFFICE_TIMEZONE) >= jam slot, pada hari
  yang diizinkan (DIGEST_WEEKDAYS untuk ringkasan; pengingat tenggat tiap hari);
- paling banyak sekali per tanggal kantor. Penandanya baris `JadwalTerlaksana`
  dengan kunci unik (slot, tanggal) di database, jadi detak ganda, dua worker,
  atau worker yang dimulai ulang tidak membuat kiriman ganda;
- setelan dibaca ulang tiap detak, jadi perubahan di God Mode berlaku hari itu
  juga tanpa restart. Jam dimundurkan sesudah slot jalan: tidak dikirim ulang.
  Jam dimajukan sebelum slot jalan: jalan di jam baru. Jam dimundurkan ke
  sebelum sekarang dan slot belum jalan: jalan di detak berikutnya (susulan).

Hari deploy: ringkasan yang crontab lamanya SUDAH jalan hari itu tidak dikirim
ulang. Buktinya `PeriodicTask.last_run_at` milik entri crontab lama, dibaca oleh
`plane.utils.penjadwal_beat.bersihkan_jadwal_basi` sesaat sebelum entri itu
dihapus, lalu ditulis sebagai penanda lewat `tandai_sudah_dikirim`. Slot yang
crontab lamanya belum jalan (deploy sebelum jamnya, atau server mati pagi itu)
tetap dikirim. Pengingat tenggat tidak pernah dilewati: task-nya mencatat per
penerima (PengingatTenggat untuk email, Notification untuk inbox), jadi jalan
kedua di hari yang sama hanya mengirim yang belum.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime

from celery import shared_task
from django.db import IntegrityError, transaction
from django.utils import timezone
from kombu.utils.imports import symbol_by_name

from plane.db.models import JadwalTerlaksana
from plane.utils.exception_logger import log_exception
from plane.utils.setelan_instance import (
    DEADLINE_REMINDER_TIME,
    DIGEST_EVENING_TIME,
    DIGEST_MORNING_TIME,
    DIGEST_WEEKDAYS,
    DIRECTOR_DIGEST_TIME,
    setelan_hari_kerja,
    setelan_jam,
    zona_kantor,
)

logger = logging.getLogger("plane")

@dataclass(frozen=True)
class Slot:
    nama: str
    # Kunci God Mode berjenis time, ditafsirkan dalam OFFICE_TIMEZONE.
    kunci_jam: str
    # Path task Celery yang menerima `tanggal` (ISO, tanggal kantor).
    task: str
    # Kunci weekday_set yang membatasi hari kirim. None = tiap hari.
    kunci_hari: str | None = None


SLOT = (
    # Tiap hari, termasuk akhir pekan, seperti crontab lamanya: tenggat Sabtu
    # tetap perlu diingatkan.
    Slot("pengingat-tenggat", DEADLINE_REMINDER_TIME, "plane.bgtasks.deadline_reminder_task.kirim_pengingat_tenggat"),
    Slot(
        "ringkasan-pagi", DIGEST_MORNING_TIME, "plane.bgtasks.daily_digest_task.kirim_ringkasan_harian", DIGEST_WEEKDAYS
    ),
    Slot(
        "ringkasan-sore", DIGEST_EVENING_TIME, "plane.bgtasks.daily_digest_task.kirim_ringkasan_sore", DIGEST_WEEKDAYS
    ),
    Slot(
        "ringkasan-direktur",
        DIRECTOR_DIGEST_TIME,
        "plane.bgtasks.direktur_digest_task.kirim_ringkasan_direktur",
        DIGEST_WEEKDAYS,
    ),
)
SLOT_PER_NAMA = {s.nama: s for s in SLOT}


def slot_jatuh_tempo(sekarang: datetime) -> tuple[date, list[Slot]]:
    """(tanggal kantor, slot yang jamnya sudah lewat hari ini dan harinya diizinkan).

    Belum melihat penanda: slot yang sudah jalan hari ini tetap ikut di sini.
    """
    lokal = sekarang.astimezone(zona_kantor())
    jam = lokal.time().replace(tzinfo=None)
    hari = lokal.isoweekday()
    hasil = []
    for slot in SLOT:
        if slot.kunci_hari and hari not in setelan_hari_kerja(slot.kunci_hari):
            continue
        if jam >= setelan_jam(slot.kunci_jam):
            hasil.append(slot)
    return lokal.date(), hasil


def klaim(slot: str, tanggal: date, hasil: dict | None = None) -> JadwalTerlaksana | None:
    """Tulis penanda (slot, tanggal). None = sudah diklaim orang lain (atau detak sebelumnya)."""
    try:
        with transaction.atomic():
            return JadwalTerlaksana.objects.create(slot=slot, tanggal=tanggal, hasil=hasil or {})
    except IntegrityError:
        return None


def tandai_sudah_dikirim(tanggal: date, slot_nama: list[str], alasan: str) -> list[str]:
    """Tulis penanda selesai tanpa menjalankan slot (mis. crontab lama sudah mengirimnya hari ini).

    Slot yang sudah punya penanda dibiarkan (ignore_conflicts). Mengembalikan nama
    slot yang dikenal dan ditandai; nama asing dibuang.
    """
    dikenal = [n for n in slot_nama if n in SLOT_PER_NAMA]
    if not dikenal:
        return []
    sekarang = timezone.now()
    JadwalTerlaksana.objects.bulk_create(
        [
            JadwalTerlaksana(slot=n, tanggal=tanggal, selesai_at=sekarang, hasil={"dilewati": alasan})
            for n in dikenal
        ],
        ignore_conflicts=True,
    )
    logger.info("Jadwal kantor %s: ditandai tanpa dikirim %s (%s)", tanggal, dikenal, alasan)
    return dikenal


@shared_task
def jalankan_jadwal_kantor(sekarang: str | None = None):
    """Didetakkan beat tiap 5 menit (plane/celery.py). Mengantrekan slot yang jatuh tempo.

    `sekarang`: ISO datetime untuk uji; kosong = jam sekarang.
    """
    waktu = datetime.fromisoformat(sekarang) if sekarang else timezone.now()
    tanggal, jatuh_tempo = slot_jatuh_tempo(waktu)
    diantrekan = []
    for slot in jatuh_tempo:
        penanda = klaim(slot.nama, tanggal)
        if penanda is None:
            continue
        try:
            jalankan_slot.delay(penanda.id)
        except Exception as e:  # noqa: BLE001
            # Broker tidak terjangkau: lepaskan klaim supaya detak berikutnya mencoba lagi.
            penanda.delete()
            log_exception(e)
            continue
        diantrekan.append(slot.nama)
    if diantrekan:
        logger.info("Jadwal kantor %s: diantrekan %s", tanggal, diantrekan)
    return {"tanggal": tanggal.isoformat(), "diantrekan": diantrekan}


@shared_task
def jalankan_slot(penanda_id: int):
    """Jalankan pekerjaan satu slot yang sudah diklaim, lalu catat hasilnya di penandanya.

    Gagal = tetap tercatat selesai dengan galatnya, TIDAK diulang hari itu: task
    ringkasan tidak mencatat per penerima, jadi mengulang berarti email ganda untuk
    yang sudah menerima.
    """
    # Klaim "sedang dijalankan" secara atomik: UPDATE bersyarat selesai_at IS NULL.
    # Pesan yang dikirim ulang broker (acks_late, worker mati, visibility timeout)
    # bisa tiba dua kali bersamaan; hanya satu yang mendapat baris terubah = 1.
    # selesai_at diisi lebih dulu sebagai tanda klaim lalu ditimpa jam selesai yang
    # sebenarnya; worker yang mati di tengah jalan tetap menahan slot sampai besok
    # (lihat model JadwalTerlaksana: email hilang sehari lebih murah daripada ganda).
    if not JadwalTerlaksana.objects.filter(id=penanda_id, selesai_at__isnull=True).update(selesai_at=timezone.now()):
        return None
    penanda = JadwalTerlaksana.objects.get(id=penanda_id)
    slot = SLOT_PER_NAMA.get(penanda.slot)
    if slot is None:
        hasil = {"galat": f"slot tidak dikenal: {penanda.slot}"}
    else:
        try:
            hasil = symbol_by_name(slot.task)(tanggal=penanda.tanggal.isoformat())
        except Exception as e:  # noqa: BLE001
            log_exception(e)
            hasil = {"galat": f"{type(e).__name__}: {e}"[:500]}
    penanda.hasil = hasil if isinstance(hasil, dict) else {"hasil": str(hasil)}
    penanda.selesai_at = timezone.now()
    penanda.save(update_fields=["hasil", "selesai_at"])
    return penanda.hasil
