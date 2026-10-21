# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu endpoint, dan sengaja hanya satu.

Denyut dari instance ke bidang kendali melakukan DUA arah sekaligus: instance
melaporkan pemakaiannya, dan menerima balik tingkatan yang berlaku untuknya.
Dibuat satu endpoint, bukan dua, karena keduanya selalu terjadi bersamaan dan
dua endpoint berarti dua kesempatan bagi keduanya jadi tidak sinkron.

Arahnya juga disengaja: instance yang MENDORONG. Kalau bidang kendali yang
menarik pemakaian, ia butuh kredensial baca ke setiap database pelanggan, dan
seluruh alasan memisahkan database jadi hilang.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.utils import timezone
from plane.control.models import Company, Subscription, TenantInstance, UsageSnapshot
from plane.license.api.permissions import InstanceAdminPermission

# Tabel batas TIDAK disalin ke sini. Ia hidup di satu tempat, dan bidang kendali
# membacanya dari sana persis seperti penegaknya di sisi penyewa. Dua salinan
# angka kuota adalah dua angka yang suatu saat berbeda.
from plane.utils.plan_limits import BATAS_TINGKATAN, TINGKATAN_BAWAAN


def _int(nilai, bawaan=0):
    try:
        return max(int(nilai), 0)
    except (TypeError, ValueError):
        return bawaan


class HeartbeatEndpoint(APIView):
    """`POST /control/heartbeat/` dengan header `X-Instance-Secret`.

    Tanpa autentikasi DRF sama sekali, dan itu bukan kelalaian: yang memanggil
    endpoint ini adalah mesin, bukan orang, jadi tidak ada sesi maupun pengguna
    yang bisa dipakai. Identitasnya rahasia per instance, dicocokkan lewat
    sidiknya.

    Batas atas yang diketahui dan sengaja belum ditutup: rahasia dikirim apa
    adanya di header, jadi keamanannya bersandar penuh pada TLS, dan permintaan
    yang direkam bisa diputar ulang. Untuk laporan pemakaian yang idempoten
    akibatnya kecil. Kalau nanti endpoint ini dipakai untuk sesuatu yang mengubah
    uang, ganti dengan tanda tangan HMAC bertimestamp, dan tempat menggantinya
    satu: fungsi `_instance_dari`.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def _instance_dari(self, request):
        rahasia = request.headers.get("X-Instance-Secret", "")
        if not rahasia:
            return None
        return (
            TenantInstance.objects.filter(
                secret_hash=TenantInstance.sidik(rahasia), is_active=True
            )
            .select_related("company")
            .first()
        )

    def post(self, request):
        instance = self._instance_dari(request)
        if instance is None:
            # Sengaja tidak membedakan "rahasia salah" dari "instance dimatikan".
            # Membedakannya memberi tahu penebak bahwa tebakannya sudah benar.
            return Response(
                {"error": "Rahasia instance tidak dikenali."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        sekarang = timezone.now()
        UsageSnapshot.objects.create(
            instance=instance,
            taken_at=sekarang,
            workspaces=_int(request.data.get("workspaces")),
            members=_int(request.data.get("members")),
            storage_bytes=_int(request.data.get("storage_bytes")),
        )

        instance.last_seen_at = sekarang
        versi = str(request.data.get("version", ""))[:64]
        if versi:
            instance.version = versi
        instance.save(update_fields=["last_seen_at", "version", "updated_at"])

        langganan = (
            Subscription.objects.filter(company=instance.company, ended_at__isnull=True)
            .order_by("-started_at")
            .first()
        )
        tier = langganan.tier if langganan else TINGKATAN_BAWAAN

        # Perusahaan yang ditangguhkan diturunkan ke tingkatan gratis, bukan
        # dimatikan. Mematikan akses berarti pelanggan yang menunggak kehilangan
        # jalan untuk membayar, dan orang yang tidak bisa masuk tidak akan
        # menyelesaikan tagihannya.
        if instance.company.status in (
            instance.company.Status.SUSPENDED,
            instance.company.Status.CHURNED,
        ):
            tier = TINGKATAN_BAWAAN

        return Response(
            {
                "tier": tier,
                "company_status": instance.company.status,
                "limits": BATAS_TINGKATAN.get(tier, BATAS_TINGKATAN[TINGKATAN_BAWAAN]),
                "acknowledged_at": sekarang.isoformat(),
            },
            status=status.HTTP_200_OK,
        )


class CompaniesEndpoint(APIView):
    """`GET /control/companies/` dan `PATCH /control/companies/<slug>/`.

    Ini yang akan dipanggil Owner Panel. Halamannya sendiri milik tim frontend
    dan arah desainnya milik Design Leads, jadi yang disiapkan di sini datanya,
    bukan tampilannya.

    Autentikasinya MENUMPANG `InstanceAdminPermission` yang sudah ada, dan itu
    bukan kemalasan melainkan jawaban yang benar: di deployment pemilik, admin
    instance memang pemilik produk. Membuat lapisan identitas kedua khusus
    Owner Panel berarti pintu login kedua yang harus dijaga, dirotasi, dan
    dipulihkan sendiri, untuk melindungi orang yang sama.

    Satu endpoint daftar dan satu endpoint aksi, bukan tujuh. Yang dibutuhkan
    halaman daftar adalah SATU permintaan yang sudah membawa tingkatan, jejak
    hidup, dan pemakaian terakhir; kalau tidak, sepuluh perusahaan berarti tiga
    puluh permintaan.
    """

    permission_classes = [InstanceAdminPermission]

    def get(self, request):
        perusahaan = Company.objects.prefetch_related("instances", "subscriptions").all()

        # Pemakaian terakhir per instance dalam SATU kueri, bukan satu per
        # perusahaan. Di sepuluh pelanggan bedanya belum terasa; di angka berapa
        # pun, sepuluh kueri untuk pertanyaan yang sama tetap salah.
        terakhir = {}
        for snap in UsageSnapshot.objects.order_by("instance_id", "-taken_at").distinct(
            "instance_id"
        ):
            terakhir[snap.instance_id] = {
                "taken_at": snap.taken_at,
                "workspaces": snap.workspaces,
                "members": snap.members,
                "storage_bytes": snap.storage_bytes,
            }

        data = []
        for c in perusahaan:
            berjalan = next(
                (s for s in c.subscriptions.all() if s.ended_at is None), None
            )
            data.append(
                {
                    "slug": c.slug,
                    "name": c.name,
                    "contact_email": c.contact_email,
                    "status": c.status,
                    "tier": berjalan.tier if berjalan else TINGKATAN_BAWAAN,
                    "subscribed_since": berjalan.started_at if berjalan else None,
                    "instances": [
                        {
                            "subdomain": i.subdomain,
                            "is_active": i.is_active,
                            "version": i.version,
                            "last_seen_at": i.last_seen_at,
                            "usage": terakhir.get(i.id),
                        }
                        for i in c.instances.all()
                    ],
                }
            )
        return Response({"companies": data}, status=status.HTTP_200_OK)

    def patch(self, request, slug):
        perusahaan = Company.objects.filter(slug=slug).first()
        if perusahaan is None:
            return Response(
                {"error": f"Perusahaan '{slug}' tidak ada."}, status=status.HTTP_404_NOT_FOUND
            )

        ubah = []
        status_baru = request.data.get("status")
        if status_baru:
            if status_baru not in Company.Status.values:
                return Response(
                    {"error": f"Status '{status_baru}' tidak dikenali."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            perusahaan.status = status_baru
            ubah.append("status")

        if ubah:
            perusahaan.save(update_fields=ubah + ["updated_at"])

        tier_baru = request.data.get("tier")
        if tier_baru:
            if tier_baru not in BATAS_TINGKATAN:
                return Response(
                    {"error": f"Tingkatan '{tier_baru}' tidak dikenali."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            sekarang = timezone.now()
            berjalan = Subscription.objects.filter(
                company=perusahaan, ended_at__isnull=True
            ).first()
            if berjalan is not None and berjalan.tier == tier_baru:
                pass  # sudah di tingkatan itu, jangan bikin baris kembar
            else:
                # Langganan lama DIAKHIRI, bukan ditimpa. Pertanyaan "sejak kapan
                # mereka Pro" dan "kapan turun kelas" pasti ditanyakan penagihan,
                # dan kolom yang ditimpa tidak bisa menjawabnya.
                if berjalan is not None:
                    berjalan.ended_at = sekarang
                    berjalan.save(update_fields=["ended_at", "updated_at"])
                Subscription.objects.create(
                    company=perusahaan, tier=tier_baru, started_at=sekarang
                )
                ubah.append("tier")

        return Response(
            {"slug": perusahaan.slug, "status": perusahaan.status, "changed": ubah},
            status=status.HTTP_200_OK,
        )
