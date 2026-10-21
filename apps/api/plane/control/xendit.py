# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Sambungan ke Xendit. SATU berkas, dan itu disengaja.

KENAPA XENDIT

Dipilih 28 Agt 2026 dari dua kandidat yang sama-sama disetujui pemilik produk,
Midtrans dan Xendit. Alasannya: Invoice API-nya menghasilkan satu halaman bayar
ter-hosting yang sekaligus menawarkan virtual account, QRIS, dan e-wallet dalam
satu panggilan; verifikasi webhooknya satu token statis alih-alih SHA512 atas
empat medan yang digabung; dan penagihan B2B di Indonesia praktis selalu lewat
transfer atau VA, bukan kartu.

KENAPA SEMUA PANGGILAN PENYEDIA DIKURUNG DI SATU BERKAS

Bukan demi abstraksi. Penyedia pembayaran adalah keputusan bisnis yang bisa
berubah karena biaya, dukungan, atau kontrak, dan perubahan itu tidak boleh
menyebar ke model, view, dan task. Yang perlu diganti kalau suatu saat pindah ke
Midtrans: berkas ini, dan bentuk muatan webhooknya.

TIDAK ADA KUNCI DI KODE

`XENDIT_SECRET_KEY` dan `XENDIT_CALLBACK_TOKEN` dibaca dari lingkungan, dan tanpa
keduanya seluruh fungsi di sini menolak jalan dengan pesan yang menyebut apa yang
kurang. Instance yang belum disetel lebih baik berhenti terang-terangan daripada
diam-diam membuat tagihan yang tidak pernah sampai ke siapa pun.
"""

import os

import requests

API = "https://api.xendit.co"
BATAS_WAKTU_DETIK = 20


class XenditBelumDisetel(RuntimeError):
    pass


class XenditGagal(RuntimeError):
    pass


def _kunci():
    kunci = os.environ.get("XENDIT_SECRET_KEY", "")
    if not kunci:
        raise XenditBelumDisetel(
            "XENDIT_SECRET_KEY belum disetel. Tanpa itu tidak ada tagihan yang bisa dibuat."
        )
    return kunci


def token_callback():
    """Token verifikasi webhook. Kosong berarti webhook HARUS ditolak semuanya."""
    return os.environ.get("XENDIT_CALLBACK_TOKEN", "")


def buat_invoice(external_id, jumlah, surel, keterangan, berlaku_detik, url_sukses=""):
    """Terbitkan satu tagihan dan kembalikan (provider_id, invoice_url, status).

    `external_id` adalah pengenal milik kita. Xendit mengembalikannya apa adanya
    di webhook, dan itulah satu-satunya cara mencocokkan pembayaran dengan baris
    di database ini.
    """
    muatan = {
        "external_id": external_id,
        "amount": int(jumlah),
        "payer_email": surel,
        "description": keterangan,
        "invoice_duration": int(berlaku_detik),
        "currency": "IDR",
    }
    if url_sukses:
        muatan["success_redirect_url"] = url_sukses

    try:
        jawab = requests.post(
            f"{API}/v2/invoices",
            json=muatan,
            # Basic auth dengan secret key sebagai username dan sandi KOSONG.
            # Itu bentuk yang diminta Xendit, bukan kelalaian.
            auth=(_kunci(), ""),
            timeout=BATAS_WAKTU_DETIK,
        )
    except requests.RequestException as e:
        raise XenditGagal(f"Tidak bisa menghubungi Xendit: {e}")

    if jawab.status_code >= 400:
        # Badan jawabannya ikut disebut karena pesan galat Xendit menyebutkan
        # medan mana yang ditolak, dan tanpa itu orang menebak.
        raise XenditGagal(f"Xendit menolak ({jawab.status_code}): {jawab.text[:400]}")

    isi = jawab.json()
    return isi.get("id", ""), isi.get("invoice_url", ""), isi.get("status", "")


def baca_webhook(muatan):
    """Ambil yang kita butuhkan dari muatan webhook, tanpa mempercayainya.

    Yang dikembalikan sengaja cuma empat medan. Menyalin seluruh muatan penyedia
    ke dalam logika kita berarti bentuk data penyedia merembes ke mana-mana, dan
    pindah penyedia jadi menyentuh setiap tempat yang pernah membacanya.
    """
    status = str(muatan.get("status", "")).upper()
    try:
        dibayar = int(muatan.get("paid_amount") or 0)
    except (TypeError, ValueError):
        dibayar = 0
    return {
        "external_id": str(muatan.get("external_id", "")),
        "status": status,
        "paid_amount": dibayar,
        "paid_at": muatan.get("paid_at") or None,
    }
