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
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils import timezone

# Third party imports
from celery import shared_task

# Module imports
from plane.db.models import RETENSI_HARI, LoginActivity
from plane.license.models import InstanceAdmin
from plane.license.utils.instance_value import get_email_configuration

logger = logging.getLogger("plane.worker")

# Berapa hari sebelum penghapusan peringatan mulai muncul.
AMBANG_PERINGATAN_HARI = 7

# Sekali hapus berapa baris. Menghapus puluhan ribu baris dalam satu perintah
# mengunci tabel cukup lama untuk terasa di aplikasi.
UKURAN_BATCH = 5000


def hitung_peringatan():
    """Keadaan retensi. Dipakai task DAN endpoint God Mode, satu sumber.

    Dipisah dari task supaya angka yang dilihat di layar tidak mungkin berbeda
    dari angka yang dipakai saat menghapus.
    """
    sekarang = timezone.now()
    batas_hapus = sekarang - timedelta(days=RETENSI_HARI)
    batas_peringatan = batas_hapus + timedelta(days=AMBANG_PERINGATAN_HARI)

    tertua = (
        LoginActivity.objects.order_by("terjadi_pada")
        .values_list("terjadi_pada", flat=True)
        .first()
    )
    akan_dibuang = LoginActivity.objects.filter(terjadi_pada__lt=batas_peringatan).count()
    sudah_lewat = LoginActivity.objects.filter(terjadi_pada__lt=batas_hapus).count()

    sisa_hari = None
    if tertua:
        sisa_hari = max(0, RETENSI_HARI - (sekarang - tertua).days)

    return {
        "retensi_hari": RETENSI_HARI,
        "ambang_peringatan_hari": AMBANG_PERINGATAN_HARI,
        "tertua": tertua,
        "sisa_hari": sisa_hari,
        "akan_dibuang": akan_dibuang,
        "sudah_lewat": sudah_lewat,
        "perlu_peringatan": akan_dibuang > 0,
    }


def _kirim_email_peringatan(keadaan):
    """Email ke semua instance admin. Diam kalau SMTP belum jalan."""
    penerima = list(
        InstanceAdmin.objects.filter(user__is_active=True)
        .exclude(user__email="")
        .values_list("user__email", flat=True)
    )
    if not penerima:
        logger.info("Retensi: tidak ada instance admin aktif untuk dikirimi email")
        return 0

    (
        EMAIL_HOST,
        EMAIL_HOST_USER,
        EMAIL_HOST_PASSWORD,
        EMAIL_PORT,
        EMAIL_USE_TLS,
        EMAIL_USE_SSL,
        EMAIL_FROM,
    ) = get_email_configuration()

    if not EMAIL_HOST:
        logger.warning("Retensi: EMAIL_HOST kosong, peringatan tidak terkirim")
        return 0

    tertua = keadaan["tertua"]
    subject = f"[Paradise Task Tracker] {keadaan['akan_dibuang']} riwayat login akan dihapus"
    body = (
        "Peringatan otomatis dari Paradise Task Tracker.\n\n"
        f"Riwayat login disimpan {keadaan['retensi_hari']} hari (3 bulan). "
        f"Sebanyak {keadaan['akan_dibuang']} peristiwa akan dihapus dalam "
        f"{keadaan['ambang_peringatan_hari']} hari ke depan"
        + (f", terhitung dari data tertua {tertua:%d %B %Y}" if tertua else "")
        + ".\n\n"
        "Kalau angkanya masih diperlukan, ekspor dulu lewat God Mode -> Aktivitas "
        "sebelum tanggal itu. Sesudah dihapus, data ini tidak bisa dikembalikan.\n\n"
        "Email ini dikirim ke semua instance admin."
    )

    connection = get_connection(
        host=EMAIL_HOST,
        port=int(EMAIL_PORT),
        username=EMAIL_HOST_USER,
        password=EMAIL_HOST_PASSWORD,
        use_tls=EMAIL_USE_TLS == "1",
        use_ssl=EMAIL_USE_SSL == "1",
    )
    msg = EmailMultiAlternatives(
        subject=subject, body=body, from_email=EMAIL_FROM, to=penerima, connection=connection
    )
    msg.send()
    logger.info("Retensi: peringatan terkirim ke %s admin", len(penerima))
    return len(penerima)


@shared_task
def bersihkan_login_activity():
    """Peringatkan lalu buang. Jalan harian lewat celery beat."""
    keadaan = hitung_peringatan()

    terkirim = 0
    if keadaan["perlu_peringatan"]:
        try:
            terkirim = _kirim_email_peringatan(keadaan)
        except Exception:
            # SMTP patah tidak boleh menghentikan pembersihan, kalau tidak,
            # tabel tumbuh selamanya karena email tidak bisa dikirim.
            logger.exception("Retensi: gagal mengirim email peringatan, pembersihan tetap lanjut")

    batas = timezone.now() - timedelta(days=RETENSI_HARI)
    dibuang = 0
    while True:
        # `all_objects` + `.delete()` di queryset = hapus KERAS. Jangan pakai
        # `.delete()` per instance: BaseModel menghapus lunak dan mengantre satu
        # task Celery per baris lewat soft_delete_related_objects.
        pk_batch = list(
            LoginActivity.all_objects.filter(terjadi_pada__lt=batas).values_list(
                "pk", flat=True
            )[:UKURAN_BATCH]
        )
        if not pk_batch:
            break
        dibuang += LoginActivity.all_objects.filter(pk__in=pk_batch).delete()[0]

    logger.info("Retensi: %s peristiwa dibuang, email ke %s admin", dibuang, terkirim)
    return {"dibuang": dibuang, "email_terkirim": terkirim, **{
        k: v for k, v in keadaan.items() if k != "tertua"
    }}
