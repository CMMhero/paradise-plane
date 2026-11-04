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

Rem pertama, jeda_tenang(): pesan baru diberitahukan setelah diam beberapa menit
(bawaan 10, diatur di God Mode > Features). Balasan cepat tidak memicu email.

Rem kedua, jeda_antar_email(): satu orang tidak menerima email berikutnya sebelum
jedanya lewat (bawaan satu jam), sedahsyat apa pun percakapan yang masuk.
"""

import logging
from datetime import timedelta

from django.db.models import Max
from django.utils import timezone

from plane.db.models import PesanLangsung
from plane.utils.exception_logger import log_exception
from plane.utils.penerima_aktif import aktif_sejak, batas_aktif
from plane.utils.preferensi_email import penyaring
from plane.utils.saklar_instance import (
    CHAT_EMAIL_INTERVAL_MINUTES,
    CHAT_EMAIL_QUIET_MINUTES,
    ENABLE_CHAT_EMAIL,
    saklar_aktif,
    setelan_angka,
)

from .chat_email import kirim_email_pesan
from celery import shared_task

# "plane.worker": lihat catatan yang sama di app/views/chat.py. Logger "plane"
# polos tidak terdaftar di konfigurasi produksi.
logger = logging.getLogger("plane.worker")


# Umur minimum pesan sebelum layak diberitahukan. Diatur di God Mode > Features.
def jeda_tenang() -> timedelta:
    return timedelta(minutes=setelan_angka(CHAT_EMAIL_QUIET_MINUTES))


# Jarak minimum antar email ke orang yang sama. Diatur di God Mode > Features.
def jeda_antar_email() -> timedelta:
    return timedelta(minutes=setelan_angka(CHAT_EMAIL_INTERVAL_MINUTES))


# Saklar pengaman, MATI secara bawaan, mengikuti pola ENABLE_DEADLINE_REMINDER.
# Fitur ini mengirim email ke karyawan sungguhan, jadi menyalakannya harus
# tindakan sadar, bukan efek samping sebuah deploy. Diatur Super Admin di
# God Mode > Fitur & otomasi.
def _aktif() -> bool:
    return saklar_aktif(ENABLE_CHAT_EMAIL)


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
    batas = sekarang - jeda_tenang()
    jeda_email = jeda_antar_email()

    # Kandidat: masuk, belum dibaca, belum pernah diberitahukan, dan sudah
    # cukup lama diam. Pesan yang sudah dibaca TIDAK PERNAH ikut, jadi orang
    # tidak menerima email untuk sesuatu yang sudah dilihatnya di layar.
    # Hanya DM: pesan kanal tidak punya satu penerima (`penerima` kosong).
    kandidat = PesanLangsung.objects.filter(
        penerima__isnull=False,
        dibaca_pada__isnull=True,
        dinotifikasi_pada__isnull=True,
        created_at__lte=batas,
    ).select_related("penerima", "pengirim", "workspace")

    per_penerima = {}
    for pesan in kandidat:
        per_penerima.setdefault(pesan.penerima_id, []).append(pesan)

    # Saklar `chat` per orang (keputusan user 2026-11-02). Yang mematikannya: pesannya
    # ditandai sudah ditangani, supaya menyalakannya lagi tidak memicu email untuk
    # tumpukan pesan lama.
    mau = penyaring(per_penerima.keys(), "chat")
    tolak = [p.id for uid, daftar in per_penerima.items() if uid not in mau for p in daftar]
    if tolak:
        PesanLangsung.objects.filter(id__in=tolak).update(dinotifikasi_pada=sekarang)
    per_penerima = {uid: daftar for uid, daftar in per_penerima.items() if uid in mau}

    terakhir_dikirimi = _email_terakhir(list(per_penerima.keys()))
    batas = batas_aktif(sekarang)

    terkirim = 0
    for user_id, pesan_masuk in per_penerima.items():
        terakhir = terakhir_dikirimi.get(user_id)
        if terakhir is not None and (sekarang - terakhir) < jeda_email:
            # Dilewati TANPA menandai. Pesannya tetap kandidat pada putaran
            # berikutnya sesudah jeda habis, jadi tidak ada yang hilang.
            continue

        penerima = pesan_masuk[0].penerima
        if not penerima.email or not penerima.is_active:
            continue
        if not aktif_sejak(penerima, batas):
            # ENABLE_EMAIL_ACTIVE_ONLY: ditandai sudah ditangani seperti saklar
            # `chat` yang mati, supaya kembali aktif tidak memicu email tumpukan lama.
            PesanLangsung.objects.filter(id__in=[p.id for p in pesan_masuk]).update(dinotifikasi_pada=sekarang)
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
