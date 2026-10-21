# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Dua endpoint penagihan: menerbitkan tagihan, dan menerima kabar pembayaran.

Dipisah dari `views.py` karena keduanya punya model ancaman yang berbeda. Yang
satu hanya boleh disentuh pemilik produk; yang satu lagi TERBUKA ke internet dan
dipanggil mesin milik orang lain. Menaruh keduanya di satu berkas membuat orang
berikutnya menyalin `permission_classes` dari tetangga yang salah.
"""

import secrets

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from plane.control import billing, xendit
from plane.control.models import Company, Invoice
from plane.license.api.permissions import InstanceAdminPermission


class InvoicesEndpoint(APIView):
    """`GET /control/companies/<slug>/invoices/` dan `POST` untuk menerbitkan."""

    permission_classes = [InstanceAdminPermission]

    def get(self, request, slug):
        company = Company.objects.filter(slug=slug).first()
        if company is None:
            return Response({"error": "Perusahaan tidak ada."}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                "invoices": [
                    {
                        "external_id": t.external_id,
                        "tier": t.tier,
                        "amount": t.amount,
                        "currency": t.currency,
                        "status": t.status,
                        "invoice_url": t.invoice_url,
                        "period_start": t.period_start,
                        "period_end": t.period_end,
                        "due_at": t.due_at,
                        "paid_at": t.paid_at,
                    }
                    for t in Invoice.objects.filter(company=company)[:50]
                ]
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, slug):
        company = Company.objects.filter(slug=slug).first()
        if company is None:
            return Response({"error": "Perusahaan tidak ada."}, status=status.HTTP_404_NOT_FOUND)

        # Barisnya dibuat DULU, panggilan ke penyedia belakangan. Kalau urutannya
        # dibalik dan panggilan berhasil tapi penyimpanan gagal, ada tagihan hidup
        # di Xendit yang tidak dikenali sistem ini, dan pembayarannya tidak akan
        # pernah bisa dicocokkan dengan siapa pun.
        try:
            tagihan = billing.terbitkan_tagihan(company, tier=request.data.get("tier"))
        except billing.TidakBisaDitagih as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        berlaku = int((tagihan.due_at - timezone.now()).total_seconds())
        try:
            provider_id, url, _status = xendit.buat_invoice(
                external_id=tagihan.external_id,
                jumlah=tagihan.amount,
                surel=company.contact_email,
                keterangan=f"Langganan {tagihan.tier} {company.name}",
                berlaku_detik=max(berlaku, 3600),
            )
        except xendit.XenditBelumDisetel as e:
            # Barisnya dibatalkan, bukan dibiarkan menggantung. Tagihan PENDING
            # yang tidak pernah punya halaman bayar akan disapu jadi kedaluwarsa
            # lalu menandai pelanggan menunggak padahal tidak ada yang pernah
            # menagih mereka.
            tagihan.status = Invoice.Status.VOID
            tagihan.save(update_fields=["status", "updated_at"])
            return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except xendit.XenditGagal as e:
            tagihan.status = Invoice.Status.VOID
            tagihan.save(update_fields=["status", "updated_at"])
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        tagihan.provider_id = provider_id
        tagihan.invoice_url = url
        tagihan.save(update_fields=["provider_id", "invoice_url", "updated_at"])

        return Response(
            {
                "external_id": tagihan.external_id,
                "amount": tagihan.amount,
                "invoice_url": tagihan.invoice_url,
                "due_at": tagihan.due_at,
            },
            status=status.HTTP_201_CREATED,
        )


class XenditWebhookEndpoint(APIView):
    """`POST /control/payments/xendit/`. Terbuka ke internet, dipanggil Xendit.

    Tanpa autentikasi DRF, karena yang memanggil bukan pengguna. Identitasnya
    token statis di header `x-callback-token`, dicocokkan dengan
    `secrets.compare_digest` supaya lama pembandingannya tidak bocor.

    🔴 TOKEN KOSONG BERARTI MENOLAK SEMUA, bukan menerima semua. Instance yang
    belum menyetel tokennya lebih baik kehilangan webhook daripada menerima
    perintah "tandai lunas" dari siapa pun yang menemukan alamatnya.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        harapan = xendit.token_callback()
        diberikan = request.headers.get("x-callback-token", "")
        if not harapan or not secrets.compare_digest(harapan, diberikan):
            return Response(
                {"error": "Token callback tidak cocok."}, status=status.HTTP_401_UNAUTHORIZED
            )

        data = xendit.baca_webhook(request.data if isinstance(request.data, dict) else {})
        if not data["external_id"]:
            return Response({"error": "external_id kosong."}, status=status.HTTP_400_BAD_REQUEST)

        tagihan, keterangan = billing.terapkan_pembayaran(data)

        # SELALU 200 selama tokennya sah, termasuk saat tagihannya tidak dikenali.
        # Penyedia mengirim ulang apa pun yang tidak dijawab 200, dan mengirim
        # ulang selamanya sesuatu yang memang tidak akan pernah cocok hanya
        # menghasilkan antrean yang tidak pernah kosong.
        return Response(
            {
                "handled": tagihan is not None,
                "detail": keterangan,
                "external_id": data["external_id"],
            },
            status=status.HTTP_200_OK,
        )
