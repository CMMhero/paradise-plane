# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Sisi PENYEWA dari denyut ke bidang kendali.

Berjalan di dalam instance pelanggan, bukan di panel pemilik. Ia melaporkan
pemakaian ke atas, lalu menerapkan tingkatan yang dijawab bidang kendali ke
seluruh workspace di instance ini.

MATI SECARA BAWAAN. Tanpa `CONTROL_PLANE_URL` dan `CONTROL_PLANE_SECRET` ia
langsung berhenti tanpa satu permintaan pun. Itu keadaan yang benar untuk kolam
gratis, untuk instance pasang-sendiri milik pelanggan Enterprise, dan untuk
mesin pengembang siapa pun. Instance yang tidak menyetel keduanya tetap
berjalan, hanya saja tingkatannya tidak pernah diubah dari luar.

KENAPA MENDORONG, BUKAN DITARIK

Kalau bidang kendali yang menarik pemakaian, ia butuh kredensial baca ke setiap
database pelanggan, dan seluruh alasan memisahkan database jadi hilang. Yang
keluar dari sini hanya tiga angka. Tidak ada nama orang, tidak ada judul
pekerjaan, tidak ada isi berkas.
"""

# Python imports
import logging
import os

# Third party imports
import requests
from celery import shared_task
from django.db.models import Count, Sum
from django.utils import timezone

# Module imports
from plane.db.models import FileAsset, Workspace, WorkspaceMember, WorkspacePlan

logger = logging.getLogger("plane")

BATAS_WAKTU_DETIK = 15


def kumpulkan_pemakaian():
    """Tiga angka, dan sengaja hanya tiga.

    Apa pun yang lebih rinci dari ini mulai menjadi keterangan tentang isi kerja
    pelanggan, dan itu bukan sesuatu yang pantas mengalir keluar dari instance
    mereka hanya untuk keperluan penagihan.
    """
    penyimpanan = FileAsset.objects.filter(
        is_uploaded=True, deleted_at__isnull=True
    ).aggregate(total=Sum("size"))["total"]

    return {
        "workspaces": Workspace.objects.filter(deleted_at__isnull=True).count(),
        "members": WorkspaceMember.objects.filter(is_active=True, deleted_at__isnull=True)
        .aggregate(jumlah=Count("member_id", distinct=True))["jumlah"]
        or 0,
        "storage_bytes": int(penyimpanan or 0),
        "version": os.environ.get("APP_RELEASE", ""),
    }


def terapkan_tingkatan(tier, batas_dari_pusat=None):
    """Tulis tingkatan yang dijawab pusat ke seluruh workspace di instance ini.

    Seluruh workspace, karena di topologi berbayar satu instance memang milik
    satu perusahaan. Kalau suatu saat satu instance melayani lebih dari satu
    perusahaan, fungsi inilah yang harus tahu bedanya, dan sengaja ditulis
    sebagai satu tempat supaya perubahan itu tidak menyebar.
    """
    diubah = 0
    for workspace_id in Workspace.objects.filter(deleted_at__isnull=True).values_list(
        "id", flat=True
    ):
        baris, dibuat = WorkspacePlan.objects.get_or_create(
            workspace_id=workspace_id, deleted_at__isnull=True, defaults={"tier": tier}
        )
        if not dibuat and baris.tier == tier:
            continue
        baris.tier = tier
        # `disable_auto_set_user=True`: di dalam Celery tidak ada request, dan
        # tanpa ini BaseModel.save() menolkan created_by baris yang sudah ada.
        baris.save(update_fields=["tier"], disable_auto_set_user=True)
        diubah += 1
    return diubah


@shared_task
def denyut_bidang_kendali():
    url = os.environ.get("CONTROL_PLANE_URL", "").rstrip("/")
    rahasia = os.environ.get("CONTROL_PLANE_SECRET", "")
    if not url or not rahasia:
        return "bidang kendali tidak disetel, dilewati"

    muatan = kumpulkan_pemakaian()
    try:
        jawaban = requests.post(
            f"{url}/control/heartbeat/",
            json=muatan,
            headers={"X-Instance-Secret": rahasia},
            timeout=BATAS_WAKTU_DETIK,
        )
    except requests.RequestException as e:
        # Pusat tidak terjangkau BUKAN alasan mengubah tingkatan apa pun. Instance
        # yang menurunkan dirinya sendiri karena jaringan putus akan mengunci
        # pelanggan yang sudah membayar, dan itu kegagalan yang jauh lebih mahal
        # daripada terlambat menurunkan yang menunggak.
        logger.warning(f"[kendali] denyut gagal: {e}")
        return "pusat tidak terjangkau"

    if jawaban.status_code != 200:
        logger.warning(f"[kendali] pusat menjawab {jawaban.status_code}")
        return f"pusat menjawab {jawaban.status_code}"

    isi = jawaban.json()
    tier = isi.get("tier")
    if not tier:
        return "jawaban pusat tanpa tingkatan"

    diubah = terapkan_tingkatan(tier)
    logger.info(f"[kendali] denyut {timezone.now():%H:%M} tier={tier} diubah={diubah}")
    return {"tier": tier, "diubah": diubah, **muatan}
