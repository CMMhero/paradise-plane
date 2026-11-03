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
from django.utils import timezone

# Module imports
from plane.db.models import Workspace, WorkspacePlan
from plane.license.utils.instance_value import get_email_configuration
from plane.utils.email_merek import bahasa_penerima, base_url, bungkus, buat_pesan, judul_html, kotak, paragraf, tombol
from plane.utils.plan_limits import (
    TIDUR_BEKU_HARI,
    TIDUR_PERINGATAN_HARI,
    TIDUR_TANDAI_HAPUS_HARI,
    TINGKATAN_BAWAAN,
    aktivitas_terakhir,
)

logger = logging.getLogger("plane")


TEKS_TIDUR = {
    "id": {
        "subjek": 'Workspace "{nama}" akan dibekukan',
        "judul": "Workspace ini akan dibekukan",
        "p1": 'Workspace "{nama}" ({slug}) sudah {hari} hari tidak dipakai siapa pun.',
        "p2": "Kalau dalam {sisa} hari ke depan masih tidak ada yang masuk, workspace ini akan berhenti "
        "menerima unggahan baru. Isinya TIDAK dihapus dan tetap bisa dibaca.",
        "p3": "Untuk membatalkannya, cukup masuk ke workspace-nya sekali.",
        "tombol": "Buka workspace",
        "alasan": "Anda menerima email ini karena Anda pemilik workspace ini.",
    },
    "en": {
        "subjek": 'Workspace "{nama}" will be frozen',
        "judul": "This workspace will be frozen",
        "p1": 'Nobody has used the "{nama}" workspace ({slug}) for {hari} days.',
        "p2": "If nobody signs in within the next {sisa} days, it will stop accepting new uploads. "
        "Its content is NOT deleted and stays readable.",
        "p3": "To cancel this, just sign in to the workspace once.",
        "tombol": "Open workspace",
        "alasan": "You received this email because you own this workspace.",
    },
}


def susun_peringatan_tidur(nama, slug, hari, sisa, bahasa="id", email=""):
    """(subjek, teks, html). Murni: dipakai pengirim dan `kirim_contoh_email`."""
    s = {k: v.format(nama=nama, slug=slug, hari=hari, sisa=sisa) for k, v in TEKS_TIDUR.get(bahasa, TEKS_TIDUR["id"]).items()}
    dasar = base_url()
    isi = (
        judul_html(s["judul"])
        + paragraf(s["p1"])
        + kotak(s["p2"], nada="peringatan")
        + paragraf(s["p3"])
        + tombol(s["tombol"], f"{dasar}/{slug}/" if dasar else "")
    )
    html = bungkus(isi, bahasa=bahasa, judul=s["subjek"], pratajuk=s["p1"], alasan=s["alasan"], email_penerima=email)
    return s["subjek"], "\n\n".join([s["p1"], s["p2"], s["p3"]]) + "\n", html


def _kirim_peringatan(workspace, pemilik, hari_menganggur):
    """Surel peringatan sebelum pembekuan. Kegagalannya tidak menggagalkan task."""
    if not getattr(pemilik, "email", None):
        return False

    try:
        if not get_email_configuration()[0]:
            return False

        sisa = max(TIDUR_BEKU_HARI - hari_menganggur, 0)
        subjek, teks, html = susun_peringatan_tidur(
            workspace.name, workspace.slug, hari_menganggur, sisa, bahasa_penerima(pemilik), pemilik.email
        )
        buat_pesan(ke=pemilik.email, subjek=subjek, html=html, teks=teks).send()
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
