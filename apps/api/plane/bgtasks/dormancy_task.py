# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Rem 3 kolam gratis: workspace yang lama tidak dipakai berhenti memakan tempat.

KENAPA REM INI PERLU, DAN KENAPA BENTUKNYA BEGINI

Di kolam gratis, sebagian besar workspace yang lahir tidak akan pernah dipakai
lagi sesudah minggu pertama. Yang mahal dari mereka BUKAN barisnya melainkan
BERKASNYA: di produksi Paradise, 79 orang dengan pemakaian nyata dua bulan
menghasilkan database 598 KB ter-gzip tapi 95 MB unggahan. Jadi rem ini menyasar
penyimpanan, dan tahap "beku" artinya berhenti menerima unggahan baru, bukan
berhenti bisa dibaca.

TIGA TAHAP, DAN TAHAP KEEMPAT YANG SENGAJA TIDAK ADA

    peringatan  surel ke pemiliknya, tidak ada yang berubah
    beku        unggahan baru ditolak, isinya tetap utuh dan tetap bisa dibaca
    ditandai    `pending_deletion_at` diisi, DAN BERHENTI DI SITU

Penghapusan TIDAK dijalankan berkas ini, dan itu keputusan yang disengaja.
Menghapus data pelanggan lewat timer adalah tindakan yang tidak bisa dibatalkan,
dan tindakan tak bisa dibatalkan tidak pantas dijalankan tanpa satu manusia pun
melihatnya. Yang dihasilkan tahap ketiga adalah DAFTAR untuk operator, bukan
eksekusi. Kalau nanti penghapusan otomatis memang diinginkan, tempat
menambahkannya jelas dan sengaja dibiarkan kosong.

SINYAL TIDURNYA MENUMPANG YANG SUDAH ADA

Tidak ada kolom stempel baru yang ditulis tiap permintaan. Kesegaran sebuah
workspace diturunkan dari `User.last_active` milik anggota aktifnya, yang sudah
dipelihara `middleware/last_active.py`. Lihat `plan_limits.aktivitas_terakhir`.
"""

# Python imports
import logging

# Third party imports
from celery import shared_task
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils import timezone

# Module imports
from plane.db.models import Workspace, WorkspacePlan
from plane.license.utils.instance_value import get_email_configuration
from plane.utils.plan_limits import (
    TIDUR_BEKU_HARI,
    TIDUR_PERINGATAN_HARI,
    TIDUR_TANDAI_HAPUS_HARI,
    TINGKATAN_BAWAAN,
    aktivitas_terakhir,
)

logger = logging.getLogger("plane")


def _kirim_peringatan(workspace, pemilik, hari_menganggur):
    """Surel peringatan sebelum pembekuan. Kegagalannya tidak menggagalkan task.

    Sengaja teks polos tanpa berkas template: yang dibutuhkan orang di sini cuma
    tahu apa yang akan terjadi dan bagaimana membatalkannya, dan satu berkas
    template lagi berarti satu berkas lagi yang harus ikut diterjemahkan.
    """
    if not getattr(pemilik, "email", None):
        return False

    try:
        host, user, pwd, port, use_tls, use_ssl, efrom = get_email_configuration()
        if not host:
            return False

        sisa = max(TIDUR_BEKU_HARI - hari_menganggur, 0)
        subjek = f"Workspace \"{workspace.name}\" akan dibekukan"
        isi = (
            f"Halo,\n\n"
            f"Workspace \"{workspace.name}\" ({workspace.slug}) sudah "
            f"{hari_menganggur} hari tidak dipakai siapa pun.\n\n"
            f"Kalau dalam {sisa} hari ke depan masih tidak ada yang masuk, "
            f"workspace ini akan berhenti menerima unggahan baru. Isinya TIDAK "
            f"dihapus dan tetap bisa dibaca.\n\n"
            f"Untuk membatalkannya, cukup masuk ke workspace-nya sekali.\n"
        )
        pesan = EmailMultiAlternatives(
            subject=subjek,
            body=isi,
            from_email=efrom,
            to=[pemilik.email],
            connection=get_connection(
                host=host,
                port=int(port),
                username=user,
                password=pwd,
                use_tls=use_tls == "1",
                use_ssl=use_ssl == "1",
            ),
        )
        pesan.send()
        return True
    except Exception as e:
        # Surel gagal tidak boleh menghentikan sapuan untuk workspace lain, dan
        # tidak boleh membuat tahapnya maju diam-diam tanpa ada yang diberi tahu.
        logger.warning(f"[tidur] gagal mengirim peringatan ke {workspace.slug}: {e}")
        return False


@shared_task
def sapu_workspace_tidur():
    """Satu sapuan harian atas seluruh workspace bertingkatan gratis."""
    if TIDUR_PERINGATAN_HARI <= 0 and TIDUR_BEKU_HARI <= 0:
        return "rem tidur dimatikan lewat lingkungan"

    sekarang = timezone.now()
    berbayar = set(
        WorkspacePlan.objects.filter(deleted_at__isnull=True)
        .exclude(tier=TINGKATAN_BAWAAN)
        .values_list("workspace_id", flat=True)
    )

    hitung = {"diperiksa": 0, "diperingatkan": 0, "dibekukan": 0, "ditandai": 0, "dibangunkan": 0}

    for workspace in Workspace.objects.filter(deleted_at__isnull=True).select_related("owner"):
        # Yang berbayar tidak pernah ditidurkan. Mereka membayar justru supaya
        # datanya tetap ada walau sedang tidak dipakai.
        if workspace.id in berbayar:
            continue

        hitung["diperiksa"] += 1
        terakhir = aktivitas_terakhir(workspace.id) or workspace.created_at
        menganggur = (sekarang - terakhir).days

        baris, _ = WorkspacePlan.objects.get_or_create(
            workspace=workspace, deleted_at__isnull=True, defaults={"tier": TINGKATAN_BAWAAN}
        )
        baris.last_activity_at = terakhir
        ubah = ["last_activity_at"]

        if TIDUR_TANDAI_HAPUS_HARI > 0 and menganggur >= TIDUR_TANDAI_HAPUS_HARI:
            if baris.pending_deletion_at is None:
                baris.pending_deletion_at = sekarang
                ubah.append("pending_deletion_at")
                hitung["ditandai"] += 1
            if baris.uploads_frozen_at is None:
                baris.uploads_frozen_at = sekarang
                ubah.append("uploads_frozen_at")

        elif TIDUR_BEKU_HARI > 0 and menganggur >= TIDUR_BEKU_HARI:
            if baris.uploads_frozen_at is None:
                baris.uploads_frozen_at = sekarang
                ubah.append("uploads_frozen_at")
                hitung["dibekukan"] += 1

        elif TIDUR_PERINGATAN_HARI > 0 and menganggur >= TIDUR_PERINGATAN_HARI:
            if baris.dormant_warned_at is None and _kirim_peringatan(
                workspace, workspace.owner, menganggur
            ):
                baris.dormant_warned_at = sekarang
                ubah.append("dormant_warned_at")
                hitung["diperingatkan"] += 1

        else:
            # Dipakai lagi. Ketiga tanda dicabut sekaligus, termasuk tanda hapus:
            # workspace yang hidup lagi bukan calon hapus lagi.
            if any(
                (baris.dormant_warned_at, baris.uploads_frozen_at, baris.pending_deletion_at)
            ):
                baris.dormant_warned_at = None
                baris.uploads_frozen_at = None
                baris.pending_deletion_at = None
                ubah += ["dormant_warned_at", "uploads_frozen_at", "pending_deletion_at"]
                hitung["dibangunkan"] += 1

        # `disable_auto_set_user=True` karena di dalam Celery tidak ada request,
        # dan tanpa ini BaseModel.save() akan MENOLKAN created_by baris yang
        # sudah ada. Jebakan yang sama pernah memakan tugas berulang.
        baris.save(update_fields=ubah, disable_auto_set_user=True)

    logger.info(f"[tidur] {hitung}")
    return hitung
