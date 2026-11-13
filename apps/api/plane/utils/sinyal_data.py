# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: sinyal "data berubah" (tanpa refresh)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kabar "ada yang berubah" ke peramban, supaya layar menyegarkan diri.

Yang dikirim HANYA petunjuk kecil: jenis sumber daya, id project/tugas, dan nama
bidang yang berubah. Tidak ada judul, nilai, atau isi. Peramban lalu menarik
ulang datanya lewat API biasa, yang sudah menegakkan siapa boleh melihat apa.
Mengirim isinya lewat Redis berarti aturan hak lihat harus ditegakkan di dua
tempat, dan yang kedua pasti tertinggal (pelajaran yang sama dengan
`obrolan_siaran.py`).

Siapa yang menerima ditentukan DI SINI, bukan di peramban: tiap siaran membawa
`untuk` (daftar id pengguna). `apps/live` hanya meneruskannya ke soket milik
orang di daftar itu dan membuang `untuk` sebelum sampai ke peramban. Dengan
begitu id project/tugas tidak pernah sampai ke orang yang tak bisa melihatnya.

Kanal Redis: `data:<slug workspace>`. Awalan ini ada di DUA berkas, berkas ini
dan `apps/live/src/controllers/obrolan.controller.ts`. Mengubah salah satu tanpa
yang lain membuat siaran hilang tanpa error di mana pun.

ponytail: siaran satu arah tanpa jaminan sampai. Kalau Redis mati atau soket
peramban sedang putus tidak ada yang hilang, karena data sebenarnya selalu
diambil lewat API; peramban menyegarkan diri saat soket tersambung lagi dan
punya jam cadangan saat putus. Itu sebabnya SEMUA fungsi di sini menelan
galatnya sendiri: menyimpan tugas jauh lebih penting daripada menyiarkannya.
"""

import json
import logging

from plane.settings.redis import redis_instance

# "plane.api", BUKAN "plane": konfigurasi logging produksi memakai
# disable_existing_loggers dan tidak punya entri untuk "plane" polos.
logger = logging.getLogger("plane.api")

AWALAN_KANAL = "data:"

ROLE_TAMU = 5

# Jenis sinyal yang dikenal peramban. Menambah satu di sini tanpa menambahnya di
# `apps/web/core/lib/data-live.ts` tidak merusak apa pun, hanya tak didengar.
JENIS_TUGAS = "tugas"
JENIS_NOTIFIKASI = "notifikasi"
JENIS_ANGGOTA_PROJECT = "anggota-project"

_klien = None


def kanal_workspace(slug: str) -> str:
    return f"{AWALAN_KANAL}{slug}"


def _redis():
    """Satu koneksi per proses. `redis_instance()` membuat koneksi baru tiap
    dipanggil, dan jalur ini bisa menyala puluhan kali per detik saat impor atau
    aksi massal."""
    global _klien
    if _klien is None:
        _klien = redis_instance()
    return _klien


def siarkan_data(slug: str, jenis: str, untuk, **isi) -> None:
    """Terbitkan satu sinyal ke orang-orang di `untuk` (id pengguna).

    `untuk` kosong = tidak ada yang perlu tahu, jadi tidak ada yang diterbitkan.
    Menelan semua galat; lihat docstring modul.
    """
    global _klien
    penerima = sorted({str(u) for u in (untuk or []) if u})
    if not slug or not penerima:
        return
    try:
        _redis().publish(
            kanal_workspace(slug),
            json.dumps({"jenis": jenis, "untuk": penerima, **isi}),
        )
    except Exception as e:  # noqa: BLE001 - sengaja ditelan
        # Buang koneksi yang mungkin sudah rusak; panggilan berikutnya membuat baru.
        _klien = None
        logger.warning("sinyal-data: gagal menyiarkan %s untuk %s: %s", jenis, slug, e)


def penerima_project(project_id, pembuat_tugas_id=None):
    """(slug workspace, [id pengguna]) yang boleh melihat isi project ini.

    Mengikuti hak lihat API: anggota aktif project. Tamu (role 5) hanya kalau
    project mengizinkan tamu melihat semuanya, atau tugas itu buatannya sendiri.
    Super Admin dan penghuni jenjang organisasi sudah dimaterialkan menjadi
    baris `ProjectMember` (lihat `db/jangkauan.py`, `db/superadmin.py`), jadi
    tidak perlu cabang khusus di sini.
    """
    from plane.db.models import Project, ProjectMember  # noqa: PLC0415 - hindari impor melingkar

    info = Project.objects.filter(pk=project_id).values_list("workspace__slug", "guest_view_all_features").first()
    if not info:
        return None, []
    slug, tamu_lihat_semua = info
    baris = ProjectMember.objects.filter(project_id=project_id, is_active=True, deleted_at__isnull=True).values_list(
        "member_id", "role"
    )
    penerima = [
        m
        for m, role in baris
        if m and (role != ROLE_TAMU or tamu_lihat_semua or (pembuat_tugas_id and str(m) == str(pembuat_tugas_id)))
    ]
    return slug, penerima


def _pembuat_tugas(issue_id):
    if not issue_id:
        return None
    from plane.db.models import Issue  # noqa: PLC0415

    return Issue.all_objects.filter(pk=issue_id).values_list("created_by_id", flat=True).first()


def siarkan_tugas(project_id, issue_id=None, bidang=None, aksi="updated", oleh_id=None) -> None:
    """Sebuah tugas (atau isinya: komentar, lampiran, tautan, relasi) berubah."""
    try:
        slug, penerima = penerima_project(project_id, _pembuat_tugas(issue_id))
        siarkan_data(
            slug,
            JENIS_TUGAS,
            penerima,
            proyek=str(project_id),
            tugas=str(issue_id) if issue_id else None,
            bidang=sorted({str(b) for b in (bidang or []) if b}),
            aksi=aksi,
            oleh=str(oleh_id) if oleh_id else None,
        )
    except Exception as e:  # noqa: BLE001 - sengaja ditelan
        logger.warning("sinyal-data: gagal menyiapkan sinyal tugas %s: %s", issue_id, e)


def siarkan_notifikasi(workspace_id, penerima_ids) -> None:
    """Ada pemberitahuan baru, atau status baca berubah, untuk orang-orang ini."""
    try:
        penerima = {str(p) for p in (penerima_ids or []) if p}
        if not penerima:
            return
        from plane.db.models import Workspace  # noqa: PLC0415

        slug = Workspace.objects.filter(pk=workspace_id).values_list("slug", flat=True).first()
        siarkan_data(slug, JENIS_NOTIFIKASI, penerima)
    except Exception as e:  # noqa: BLE001 - sengaja ditelan
        logger.warning("sinyal-data: gagal menyiapkan sinyal notifikasi: %s", e)


def siarkan_notifikasi_baris(baris) -> None:
    """Sama dengan `siarkan_notifikasi`, tapi dari objek `Notification` yang baru
    ditulis (bisa campuran workspace). Satu siaran per workspace."""
    try:
        per_workspace = {}
        for n in baris or []:
            per_workspace.setdefault(n.workspace_id, set()).add(n.receiver_id)
        for workspace_id, penerima in per_workspace.items():
            siarkan_notifikasi(workspace_id, penerima)
    except Exception as e:  # noqa: BLE001 - sengaja ditelan
        logger.warning("sinyal-data: gagal menyiapkan sinyal notifikasi: %s", e)


def siarkan_anggota_project(project_id, user_ids=(), oleh_id=None) -> None:
    """Keanggotaan project berubah. `user_ids` yang baru dilepas ikut diberi tahu
    walau sudah bukan anggota, supaya layarnya sendiri ikut menyegarkan diri."""
    try:
        slug, penerima = penerima_project(project_id)
        siarkan_data(
            slug,
            JENIS_ANGGOTA_PROJECT,
            [*penerima, *user_ids],
            proyek=str(project_id),
            oleh=str(oleh_id) if oleh_id else None,
        )
    except Exception as e:  # noqa: BLE001 - sengaja ditelan
        logger.warning("sinyal-data: gagal menyiapkan sinyal anggota project %s: %s", project_id, e)
