# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: email pemberitahuan pesan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Beri tahu lewat email kalau ada pesan Obrolan yang tidak dibaca-baca.

Tanpa ini, lencana di sidebar hanya berguna bagi orang yang kebetulan sedang
membuka aplikasi. Yang tidak membukanya seharian tidak akan pernah tahu ada
pesan masuk, dan chat yang pesannya mengendap berhari-hari lebih buruk daripada
tidak ada chat sama sekali, karena pengirimnya menyangka sudah tersampaikan.

BUKAN sinyal pada tiap pesan terkirim. Dua orang yang saling membalas cepat akan
saling mengirimi belasan email dalam sepuluh menit, dan email yang datang lebih
cepat daripada yang bisa dibaca akan diabaikan seluruhnya, termasuk yang penting.
Yang dipakai: putaran berkala dengan dua rem, sama polanya dengan pengingat
tenggat dan sinkronisasi kalender.

Rem pertama, JEDA_TENANG: pesan baru diberitahukan setelah diam beberapa menit.
Orang yang membalas dalam lima menit tidak pernah memicu satu email pun.

Rem kedua, JEDA_ANTAR_EMAIL: satu orang tidak menerima email berikutnya sebelum
lewat satu jam, sedahsyat apa pun percakapan yang masuk.
"""

import logging
import os
from datetime import timedelta

from django.db.models import Max
from django.utils import timezone

from plane.db.models import PesanLangsung
from plane.utils.exception_logger import log_exception

from .chat_email import kirim_email_pesan
from celery import shared_task

# "plane.worker": lihat catatan yang sama di app/views/chat.py. Logger "plane"
# polos tidak terdaftar di konfigurasi produksi.
logger = logging.getLogger("plane.worker")

# Umur minimum pesan sebelum layak diberitahukan.
JEDA_TENANG = timedelta(minutes=10)

# Jarak minimum antar email ke orang yang sama.
JEDA_ANTAR_EMAIL = timedelta(hours=1)


# Saklar pengaman, MATI secara bawaan, mengikuti pola ENABLE_DEADLINE_REMINDER.
# Fitur ini mengirim email ke karyawan sungguhan, jadi menyalakannya harus
# tindakan sadar, bukan efek samping sebuah deploy. Nyalakan lewat
# `ENABLE_CHAT_EMAIL=1` di `apps/api/.env` lalu `docker compose up -d`
# (restart saja TIDAK cukup, env file hanya dibaca ulang saat container dibuat
# ulang).
def _aktif() -> bool:
    return os.environ.get("ENABLE_CHAT_EMAIL", "0") == "1"


def _email_terakhir(user_ids) -> dict:
    """Kapan tiap orang terakhir dikirimi email, dalam SATU kueri.

    Versi per-orang di dalam loop akan jadi 79 kali bolak-balik ke database tiap
    lima menit, selamanya, hanya untuk memutuskan tidak mengirim apa pun.
    """
    return dict(
        PesanLangsung.objects.filter(penerima_id__in=user_ids, dinotifikasi_pada__isnull=False)
        .values_list("penerima_id")
        .annotate(kapan=Max("dinotifikasi_pada"))
    )


@shared_task
def kirim_pemberitahuan_pesan():
    if not _aktif():
        return

    sekarang = timezone.now()
    batas = sekarang - JEDA_TENANG

    # Kandidat: masuk, belum dibaca, belum pernah diberitahukan, dan sudah
    # cukup lama diam. Pesan yang sudah dibaca TIDAK PERNAH ikut, jadi orang
    # tidak menerima email untuk sesuatu yang sudah dilihatnya di layar.
    kandidat = PesanLangsung.objects.filter(
        dibaca_pada__isnull=True,
        dinotifikasi_pada__isnull=True,
        created_at__lte=batas,
    ).select_related("penerima", "pengirim", "workspace")

    per_penerima = {}
    for pesan in kandidat:
        per_penerima.setdefault(pesan.penerima_id, []).append(pesan)

    terakhir_dikirimi = _email_terakhir(list(per_penerima.keys()))

    terkirim = 0
    for user_id, pesan_masuk in per_penerima.items():
        terakhir = terakhir_dikirimi.get(user_id)
        if terakhir is not None and (sekarang - terakhir) < JEDA_ANTAR_EMAIL:
            # Dilewati TANPA menandai. Pesannya tetap kandidat pada putaran
            # berikutnya sesudah jeda habis, jadi tidak ada yang hilang.
            continue

        penerima = pesan_masuk[0].penerima
        if not penerima.email or not penerima.is_active:
            continue

        # Rangkum per lawan bicara: berapa pesan dan apa yang terakhir ditulis.
        per_pengirim = {}
        for pesan in sorted(pesan_masuk, key=lambda p: p.created_at):
            per_pengirim[pesan.pengirim_id] = (
                pesan.pengirim,
                per_pengirim.get(pesan.pengirim_id, (None, 0, ""))[1] + 1,
                pesan.isi,
            )
        ringkasan = sorted(per_pengirim.values(), key=lambda baris: baris[1], reverse=True)

        try:
            kirim_email_pesan(penerima, pesan_masuk[0].workspace.slug, ringkasan)
        except Exception as e:
            # Ditandai HANYA kalau emailnya benar-benar terkirim. Menandai lebih
            # dulu berarti satu SMTP yang sedang ngambek menelan pemberitahuan
            # itu selamanya, dan tidak ada yang tahu.
            log_exception(e)
            logger.warning("Email obrolan gagal untuk %s", penerima.email)
            continue

        PesanLangsung.objects.filter(id__in=[p.id for p in pesan_masuk]).update(dinotifikasi_pada=sekarang)
        terkirim += 1

    if terkirim:
        logger.info("Email obrolan terkirim ke %s orang", terkirim)
