# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Aturan penagihan. Tidak ada satu pun panggilan HTTP ke penyedia di sini.

Pembagiannya disengaja: `xendit.py` tahu cara bicara dengan penyedia dan tidak
tahu apa-apa soal langganan; berkas ini tahu apa artinya sebuah pembayaran dan
tidak tahu penyedianya siapa. Kalau suatu saat pindah ke Midtrans, berkas ini
tidak ikut berubah.

HARGANYA KEPUTUSAN BISNIS

Angka bawaan di bawah adalah TEMPAT DUDUK, bukan harga yang sudah diputuskan.
Pemilik produk belum menetapkannya per 28 Agt 2026. Keduanya dibaca dari
lingkungan supaya penetapannya nanti tidak menunggu rilis.
"""

import os
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from plane.control.models import Company, Invoice, Subscription


def _int_env(nama, bawaan):
    try:
        return int(os.environ.get(nama, bawaan))
    except (TypeError, ValueError):
        return int(bawaan)


# Rupiah bulat per bulan. Enterprise sengaja TIDAK ada di sini: rencana produk
# menyebutnya "khusus", dan yang khusus ditagih lewat kesepakatan, bukan lewat
# tabel.
HARGA = {
    "PRO": _int_env("PRICE_PRO_IDR", 499000),
    "EXPERT": _int_env("PRICE_EXPERT_IDR", 1499000),
}

PERIODE_HARI = _int_env("BILLING_PERIOD_DAYS", 30)
JATUH_TEMPO_HARI = _int_env("BILLING_DUE_DAYS", 7)
# Berapa lama sesudah jatuh tempo sebelum ditangguhkan. Bukan nol, karena
# transfer antar bank di Indonesia bisa butuh satu hari kerja untuk terbaca, dan
# menangguhkan pelanggan yang uangnya sedang di jalan adalah cara kehilangan
# pelanggan yang justru sudah membayar.
TENGGANG_HARI = _int_env("BILLING_GRACE_DAYS", 7)


class TidakBisaDitagih(RuntimeError):
    pass


def harga(tier):
    if tier not in HARGA:
        raise TidakBisaDitagih(
            f"Tingkatan '{tier}' tidak punya harga daftar. "
            "FREE tidak ditagih, dan ENTERPRISE ditagih lewat kesepakatan."
        )
    return HARGA[tier]


def terbitkan_tagihan(company, tier=None, sekarang=None):
    """Buat baris tagihan untuk satu periode. TIDAK memanggil penyedia.

    Dipisah dari pemanggilan penyedia supaya barisnya sudah ada sebelum ada
    permintaan jaringan. Kalau urutannya dibalik dan panggilan berhasil tapi
    penyimpanan barisnya gagal, ada tagihan hidup di Xendit yang tidak dikenali
    sistem ini, dan pembayarannya tidak akan pernah bisa dicocokkan.
    """
    sekarang = sekarang or timezone.now()
    berjalan = Subscription.objects.filter(company=company, ended_at__isnull=True).first()
    tier = tier or (berjalan.tier if berjalan else None)
    if not tier:
        raise TidakBisaDitagih(f"'{company.slug}' belum punya langganan berjalan.")

    jumlah = harga(tier)
    # Pengenal MILIK KITA, dan harus unik selamanya karena penyedia memakainya
    # sebagai kunci. Stempel detik sudah cukup: dua tagihan untuk perusahaan yang
    # sama dalam detik yang sama bukan keadaan yang masuk akal.
    external_id = f"{company.slug}-{tier.lower()}-{int(sekarang.timestamp())}"

    return Invoice.objects.create(
        company=company,
        subscription=berjalan,
        external_id=external_id,
        tier=tier,
        amount=jumlah,
        period_start=sekarang,
        period_end=sekarang + timedelta(days=PERIODE_HARI),
        due_at=sekarang + timedelta(days=JATUH_TEMPO_HARI),
    )


@transaction.atomic
def terapkan_pembayaran(data):
    """Terapkan satu webhook pembayaran. AMAN dijalankan berulang.

    Penyedia pembayaran mengirim ulang webhook yang tidak dijawab 200, dan
    sebagian mengirim ganda tanpa alasan. Fungsi yang memperpanjang langganan
    setiap kali dipanggil akan memberi pelanggan tiga bulan gratis karena
    jaringan sedang buruk.
    """
    tagihan = Invoice.objects.select_for_update().filter(
        external_id=data["external_id"]
    ).first()
    if tagihan is None:
        return None, "tagihan tidak dikenali"

    if tagihan.status == Invoice.Status.PAID:
        return tagihan, "sudah lunas sebelumnya"

    if data["status"] != "PAID":
        if data["status"] == "EXPIRED":
            tagihan.status = Invoice.Status.EXPIRED
            tagihan.save(update_fields=["status", "updated_at"])
            return tagihan, "ditandai kedaluwarsa"
        return tagihan, f"status '{data['status']}' diabaikan"

    # Jumlah DIPERIKSA, tidak dipercaya begitu saja. Webhook yang mengaku lunas
    # dengan jumlah lebih kecil dari tagihannya adalah pembayaran sebagian, dan
    # memperlakukannya sebagai lunas berarti memberi langganan penuh untuk uang
    # yang tidak penuh.
    if data["paid_amount"] < tagihan.amount:
        return tagihan, (
            f"dibayar {data['paid_amount']} kurang dari tagihan {tagihan.amount}, "
            "tidak ditandai lunas"
        )

    tagihan.status = Invoice.Status.PAID
    tagihan.paid_amount = data["paid_amount"]
    tagihan.paid_at = timezone.now()
    tagihan.save(update_fields=["status", "paid_amount", "paid_at", "updated_at"])

    _pastikan_langganan(tagihan)

    company = tagihan.company
    if company.status != Company.Status.ACTIVE:
        company.status = Company.Status.ACTIVE
        company.save(update_fields=["status", "updated_at"])

    return tagihan, "lunas"


def _pastikan_langganan(tagihan):
    """Langganan berjalan harus cocok dengan tingkatan yang baru dibayar."""
    berjalan = Subscription.objects.filter(
        company=tagihan.company, ended_at__isnull=True
    ).first()
    if berjalan is not None and berjalan.tier == tagihan.tier:
        return berjalan
    if berjalan is not None:
        berjalan.ended_at = timezone.now()
        berjalan.save(update_fields=["ended_at", "updated_at"])
    return Subscription.objects.create(
        company=tagihan.company, tier=tagihan.tier, started_at=timezone.now()
    )


def sapu_lewat_tempo(sekarang=None):
    """Tagihan yang lewat tempo menandai perusahaannya menunggak, lalu menangguhkan.

    DUA tahap, bukan satu. Menangguhkan langsung di hari jatuh tempo menghukum
    pelanggan yang transfernya masih di jalan; tidak menangguhkan sama sekali
    membuat "menunggak" jadi status yang tidak berarti apa-apa.

    Tidak pernah menyentuh perusahaan yang sudah CHURNED: mereka sudah pergi, dan
    menagih orang yang sudah berhenti adalah cara memastikan mereka tidak kembali.
    """
    sekarang = sekarang or timezone.now()
    hasil = {"kedaluwarsa": 0, "menunggak": 0, "ditangguhkan": 0}

    lewat = Invoice.objects.filter(
        status=Invoice.Status.PENDING, due_at__lt=sekarang
    ).select_related("company")
    for tagihan in lewat:
        tagihan.status = Invoice.Status.EXPIRED
        tagihan.save(update_fields=["status", "updated_at"])
        hasil["kedaluwarsa"] += 1

        company = tagihan.company
        if company.status in (Company.Status.TRIAL, Company.Status.ACTIVE):
            company.status = Company.Status.PAST_DUE
            company.save(update_fields=["status", "updated_at"])
            hasil["menunggak"] += 1

    ambang = sekarang - timedelta(days=TENGGANG_HARI)
    for company in Company.objects.filter(status=Company.Status.PAST_DUE):
        tertua = (
            Invoice.objects.filter(company=company, status=Invoice.Status.EXPIRED)
            .order_by("due_at")
            .first()
        )
        if tertua is not None and tertua.due_at < ambang:
            company.status = Company.Status.SUSPENDED
            company.save(update_fields=["status", "updated_at"])
            hasil["ditangguhkan"] += 1

    return hasil
