# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: retensi riwayat login
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Buang riwayat login yang lewat 3 bulan, dan beri tahu sebelum dibuang.

Permintaan kantor: riwayat bisa ditelusuri mundur sampai 3 bulan, dan **sebelum
data tertua hilang**, God Mode memberi peringatan dan super admin dikirimi
email.

Peringatannya sengaja muncul beberapa hari di depan (AMBANG_PERINGATAN_HARI),
bukan pada hari penghapusan. Pemberitahuan yang datang bersamaan dengan
hilangnya data tidak memberi siapa pun kesempatan mengekspornya.
"""

# Python imports
import logging
from datetime import timedelta

# Django imports
from django.core.cache import cache
from django.utils import timezone

# Third party imports
from celery import shared_task

# Module imports
from plane.db.models import LoginActivity
from plane.license.models import InstanceAdmin
from plane.license.utils.instance_value import email_aktif, get_email_configuration
from plane.utils.email_merek import (
    MEREK,
    bahasa_penerima,
    bungkus,
    buat_pesan,
    judul_html,
    kelompokkan_penerima,
    kotak,
    paragraf,
    tanggal,
)
from plane.utils.saklar_instance import (
    ENABLE_ADMIN_RETENTION_EMAIL,
    LOGIN_HISTORY_RETENTION_DAYS,
    saklar_aktif,
    setelan_angka,
)

logger = logging.getLogger("plane.worker")

# Berapa hari sebelum penghapusan peringatan mulai muncul.
AMBANG_PERINGATAN_HARI = 7

# Peringatan terus benar selama ada data yang akan dibuang, dan itu keadaan tetap
# sesudah bulan ketiga: tiap hari ada baris yang masuk jendela 7 hari. Email
# harian jadi gangguan yang akhirnya diabaikan. Satu email per minggu cukup untuk
# memberi waktu mengekspor; angka yang melonjak tetap dikirim lebih cepat.
ULANG_EMAIL_HARI = 7
# Lonjakan yang dianggap kabar baru: jumlah yang terancam sekurangnya segini kali
# jumlah di email terakhir (misalnya retensi dipersingkat di God Mode).
LONJAKAN_PELIPATAN = 2
KUNCI_EMAIL_TERAKHIR = "retensi:email-peringatan-terakhir"
# Penanda dibuang sendiri kalau task berhenti jalan; email berikutnya tetap sah.
TTL_PENANDA_DETIK = 60 * 60 * 24 * 60

# Sekali hapus berapa baris. Menghapus puluhan ribu baris dalam satu perintah
# mengunci tabel cukup lama untuk terasa di aplikasi.
UKURAN_BATCH = 5000


def hitung_peringatan():
    """Keadaan retensi. Dipakai task DAN endpoint God Mode, satu sumber.

    Dipisah dari task supaya angka yang dilihat di layar tidak mungkin berbeda
    dari angka yang dipakai saat menghapus.
    """
    sekarang = timezone.now()
    retensi = setelan_angka(LOGIN_HISTORY_RETENTION_DAYS)
    batas_hapus = sekarang - timedelta(days=retensi)
    batas_peringatan = batas_hapus + timedelta(days=AMBANG_PERINGATAN_HARI)

    tertua = LoginActivity.objects.order_by("terjadi_pada").values_list("terjadi_pada", flat=True).first()
    akan_dibuang = LoginActivity.objects.filter(terjadi_pada__lt=batas_peringatan).count()
    sudah_lewat = LoginActivity.objects.filter(terjadi_pada__lt=batas_hapus).count()

    sisa_hari = None
    if tertua:
        sisa_hari = max(0, retensi - (sekarang - tertua).days)

    return {
        "retensi_hari": retensi,
        "ambang_peringatan_hari": AMBANG_PERINGATAN_HARI,
        "tertua": tertua,
        "sisa_hari": sisa_hari,
        "akan_dibuang": akan_dibuang,
        "sudah_lewat": sudah_lewat,
        "perlu_peringatan": akan_dibuang > 0,
    }


TEKS_RETENSI = {
    "id": {
        "subjek": "[{merek}] {n} riwayat login akan dihapus",
        "judul": "Riwayat login akan dihapus",
        "p1": "Riwayat login disimpan {retensi} hari. Sebanyak {n} peristiwa akan dihapus dalam {ambang} hari ke depan{tertua}.",
        "tertua": ", terhitung dari data tertua {tgl}",
        "p2": "Kalau angkanya masih diperlukan, ekspor dulu lewat God Mode > Activity sebelum tanggal itu. "
        "Sesudah dihapus, data ini tidak bisa dikembalikan.",
        "alasan": "Anda menerima email ini karena Anda admin instance.",
    },
    "en": {
        "subjek": "[{merek}] {n} login records will be deleted",
        "judul": "Login history will be deleted",
        "p1": "Login history is kept for {retensi} days. {n} events will be deleted within the next {ambang} days{tertua}.",
        "tertua": ", counting from the oldest record on {tgl}",
        "p2": "If you still need these numbers, export them from God Mode > Activity before then. "
        "Once deleted, this data cannot be recovered.",
        "alasan": "You received this email because you are an instance admin.",
    },
}


def susun_peringatan_retensi(keadaan, bahasa="id", email=""):
    """(subjek, teks, html). Murni: dipakai pengirim dan `kirim_contoh_email`.

    `email` = satu alamat atau daftar alamat (satu email bersama ke semua admin).
    """
    s = TEKS_RETENSI.get(bahasa, TEKS_RETENSI["id"])
    tertua = keadaan.get("tertua")
    isian = {
        "merek": MEREK,
        "n": keadaan["akan_dibuang"],
        "retensi": keadaan["retensi_hari"],
        "ambang": keadaan["ambang_peringatan_hari"],
        "tertua": s["tertua"].format(tgl=tanggal(tertua, bahasa)) if tertua else "",
    }
    subjek = s["subjek"].format(**isian)
    p1 = s["p1"].format(**isian)
    isi = judul_html(s["judul"]) + paragraf(p1) + kotak(s["p2"], nada="peringatan")
    html = bungkus(isi, bahasa=bahasa, judul=subjek, pratajuk=p1, alasan=s["alasan"], email_penerima=email)
    return subjek, f"{p1}\n\n{s['p2']}\n\n{s['alasan']}\n", html


def perlu_kirim_email(terakhir, keadaan, sekarang=None):
    """Murni: apakah email peringatan hari ini layak dikirim.

    `terakhir` = {"pada": datetime, "jumlah": int} dari email sebelumnya, atau None.
    Kirim kalau belum pernah, sudah ULANG_EMAIL_HARI hari, atau jumlah yang
    terancam melonjak (dan sudah lewat sehari, supaya tidak berulang pada hari
    yang sama).
    """
    if not terakhir:
        return True
    sekarang = sekarang or timezone.now()
    lewat = sekarang - terakhir["pada"]
    if lewat >= timedelta(days=ULANG_EMAIL_HARI):
        return True
    sebelumnya = max(terakhir.get("jumlah", 0), 1)
    return lewat >= timedelta(days=1) and keadaan["akan_dibuang"] >= sebelumnya * LONJAKAN_PELIPATAN


def _kirim_email_peringatan(keadaan):
    """Email ke semua instance admin, masing-masing dalam bahasanya. Diam kalau SMTP belum jalan.

    Saklar God Mode `ENABLE_ADMIN_RETENTION_EMAIL` mematikan emailnya saja; banner
    di God Mode dan pembersihan tidak ikut berhenti.
    """
    if not saklar_aktif(ENABLE_ADMIN_RETENTION_EMAIL):
        logger.info("Retensi: email peringatan dimatikan di God Mode, dilewati")
        return 0
    admin = [
        a.user
        for a in InstanceAdmin.objects.filter(user__is_active=True)
        .exclude(user__email="")
        .select_related("user", "user__profile")
    ]
    if not admin:
        logger.info("Retensi: tidak ada instance admin aktif untuk dikirimi email")
        return 0

    if not email_aktif(get_email_configuration()[0]):
        logger.warning("Retensi: SMTP belum diatur atau dimatikan, peringatan tidak terkirim")
        return 0

    # Isinya sama untuk semua admin, jadi satu pesan per bahasa dengan semua
    # alamat di To: tiap admin melihat siapa lagi yang diberi tahu.
    terkirim = 0
    for kelompok in kelompokkan_penerima(admin):
        alamat = [u.email for u in kelompok]
        subjek, teks, html = susun_peringatan_retensi(keadaan, bahasa_penerima(kelompok[0]), alamat)
        buat_pesan(ke=alamat, subjek=subjek, html=html, teks=teks).send()
        terkirim += len(kelompok)
    logger.info("Retensi: peringatan terkirim ke %s admin", terkirim)
    return terkirim

@shared_task
def bersihkan_login_activity():
    """Peringatkan lalu buang. Jalan harian lewat celery beat."""
    keadaan = hitung_peringatan()

    terkirim = 0
    if keadaan["perlu_peringatan"]:
        try:
            terakhir = cache.get(KUNCI_EMAIL_TERAKHIR)
            if perlu_kirim_email(terakhir, keadaan):
                terkirim = _kirim_email_peringatan(keadaan)
                if terkirim:
                    cache.set(
                        KUNCI_EMAIL_TERAKHIR,
                        {"pada": timezone.now(), "jumlah": keadaan["akan_dibuang"]},
                        TTL_PENANDA_DETIK,
                    )
            else:
                logger.info("Retensi: email peringatan dikirim %s, ditahan sampai minggu depan", terakhir["pada"])
        except Exception:
            # SMTP patah tidak boleh menghentikan pembersihan, kalau tidak,
            # tabel tumbuh selamanya karena email tidak bisa dikirim.
            logger.exception("Retensi: gagal mengirim email peringatan, pembersihan tetap lanjut")

    batas = timezone.now() - timedelta(days=setelan_angka(LOGIN_HISTORY_RETENTION_DAYS))
    dibuang = 0
    while True:
        # `all_objects` + `.delete()` di queryset = hapus KERAS. Jangan pakai
        # `.delete()` per instance: BaseModel menghapus lunak dan mengantre satu
        # task Celery per baris lewat soft_delete_related_objects.
        pk_batch = list(
            LoginActivity.all_objects.filter(terjadi_pada__lt=batas).values_list("pk", flat=True)[:UKURAN_BATCH]
        )
        if not pk_batch:
            break
        dibuang += LoginActivity.all_objects.filter(pk__in=pk_batch).delete()[0]

    logger.info("Retensi: %s peristiwa dibuang, email ke %s admin", dibuang, terkirim)
    return {"dibuang": dibuang, "email_terkirim": terkirim, **{k: v for k, v in keadaan.items() if k != "tertua"}}
