# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: laporan harian direktur
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu email per direktur per workspace per hari kerja: ikhtisar per divisi.

Keputusan user 2026-11-02 (mengganti daftar tugas selesai per project): direktur
hanya butuh gambaran dari manager dan supervisor, bukan rincian staf. Isinya
ANGKA per divisi (+ nama manager) dan per departemen (+ nama supervisor):
selesai di jendela laporan, terlambat (dan yang macet > STUCK_AFTER_DAYS, bawaan 7
hari), jatuh tempo hari ini, dan DIGEST_LOOKAHEAD_DAYS (bawaan 7) hari ke depan.
Render ada di `direktur_digest_email` (murni).

Cakupan = `divisi_diawasi()`: seluruh project (baris `PengawasanDivisi` tidak
lagi membatasi, KEP-93). Struktur divisi belum diisi = tiap project jadi satu unit di
bawah "Tanpa divisi".

Tetap tanpa opt-in (KEP-42: "keep it always on"). Ringkasan harian direktur
(`daily_digest_task`) sekarang hanya berisi tugas pribadinya, jadi tidak ada
rincian tim yang dobel. Jadwal: slot `ringkasan-direktur` di plane/bgtasks/jadwal_kantor.py
(God Mode DIRECTOR_DIGEST_TIME pada DIGEST_WEEKDAYS, bawaan Senin-Jumat 08.30). Jendela
"selesai" mundur sampai hari kirim sebelumnya: dengan bawaan, Senin mencakup Jumat
sore sampai Minggu.

Sekali per hari dijamin penanda `JadwalTerlaksana` penjadwal kantor; jalankan task ini
manual dua kali = dua email.
"""

import logging
from collections import defaultdict
from datetime import date, timedelta

from celery import shared_task
from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone

from plane.bgtasks.daily_digest_task import _koneksi, hari_ke_depan_pagi
from plane.bgtasks.deadline_reminder_email import _base_url
from plane.bgtasks.deadline_reminder_task import GRUP_SELESAI, hari_ini_kantor
from plane.bgtasks.direktur_digest_email import Angka, DivisiLaporan, Laporan, Unit, susun_email
from plane.utils.email_merek import bahasa_penerima, buat_pesan
from plane.db.models import (
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_SUPERVISOR,
    DepartemenProject,
    Issue,
    JabatanOrganisasi,
    PersetujuanPenugasan,
    Project,
    STATUS_PERSETUJUAN_DISETUJUI,
    Workspace,
)
from plane.utils.exception_logger import log_exception
from plane.utils.hierarki import divisi_diawasi
from plane.utils.menunggu_persetujuan import q_bisa_terlambat
from plane.utils.saklar_instance import STUCK_AFTER_DAYS, setelan_angka
from plane.utils.setelan_instance import DIGEST_WEEKDAYS, setelan_hari_kerja

logger = logging.getLogger("plane")

TANPA_DIVISI = "Tanpa divisi"
HARI_KERJA_BAWAAN = frozenset({1, 2, 3, 4, 5})


def jendela_hari(hari_ini, hari_kerja=HARI_KERJA_BAWAAN) -> int:
    """Hari mundur ke hari kirim sebelumnya (`hari_kerja`: hari ISO, DIGEST_WEEKDAYS).

    Senin-Jumat: Senin menutup akhir pekan (3), hari lain 1. Hari di luar
    `hari_kerja` (panggilan manual) tetap mundur ke hari kirim terakhir.
    """
    for jarak in range(1, 8):
        if (hari_ini - timedelta(days=jarak)).isoweekday() in hari_kerja:
            return jarak
    return 1


def jendela_jam(hari_ini, hari_kerja=HARI_KERJA_BAWAAN) -> int:
    """Lebar jendela "selesai" dalam jam. Bawaan: Senin 72, hari lain 24."""
    return 24 * jendela_hari(hari_ini, hari_kerja)


def label_jendela(hari_ini, hari) -> str:
    """Label jendela untuk email (diterjemahkan `direktur_digest_email._jendela`)."""
    if hari == 1:
        return "24 jam terakhir"
    if hari == 3 and hari_ini.isoweekday() == 1:
        return "Jumat s.d. Minggu"
    return f"{hari} hari terakhir"


def _nama(user):
    return user.display_name or user.first_name or user.email


class DataWorkspace:
    """Angka per project + peta project -> (divisi, departemen) + nama pimpinan, dimuat SEKALI."""

    def __init__(self, workspace_id, hari_ini, sejak, hari_macet=None, hari_ke_depan=None):
        """`hari_macet` / `hari_ke_depan`: None = God Mode STUCK_AFTER_DAYS / DIGEST_LOOKAHEAD_DAYS."""
        self.hari_ini = hari_ini
        self.hari_macet = setelan_angka(STUCK_AFTER_DAYS) if hari_macet is None else hari_macet
        self.hari_ke_depan = hari_ke_depan_pagi() if hari_ke_depan is None else hari_ke_depan
        dasar = Issue.issue_objects.filter(workspace_id=workspace_id, project__deleted_at__isnull=True)
        # KEP-84: yang menunggu persetujuan selesai tidak terbuka bagi staf: tidak
        # terlambat, tidak macet, tidak jatuh tempo.
        terbuka = Q(target_date__isnull=False) & ~Q(state__group__in=GRUP_SELESAI) & q_bisa_terlambat()
        # Selesai sejak laporan lalu: `completed_at` (KEP-84: bisa = saat diajukan),
        # ATAU disetujui sejak laporan lalu, supaya tugas yang diajukan sebelum
        # `sejak` dan disetujui sesudahnya tetap terhitung sekali.
        disetujui_sejak = Exists(
            PersetujuanPenugasan.objects.filter(
                issue_id=OuterRef("pk"), status=STATUS_PERSETUJUAN_DISETUJUI, diputuskan_pada__gte=sejak
            )
        )
        self.angka = defaultdict(Angka)
        for baris in (
            dasar.values("project_id").annotate(
                selesai=Count(
                    "id",
                    filter=Q(completed_at__gte=sejak) | (Q(state__group="completed") & Q(disetujui_sejak)),
                ),
                lewat=Count("id", filter=terbuka & Q(target_date__lt=hari_ini)),
                macet=Count("id", filter=terbuka & Q(target_date__lt=hari_ini - timedelta(days=self.hari_macet))),
                hari=Count("id", filter=terbuka & Q(target_date=hari_ini)),
                depan=Count(
                    "id",
                    filter=terbuka
                    & Q(target_date__gt=hari_ini, target_date__lte=hari_ini + timedelta(days=self.hari_ke_depan)),
                ),
            )
        ):
            pid = baris.pop("project_id")
            self.angka[pid] = Angka(**baris)

        self.nama_project = dict(
            Project.objects.filter(workspace_id=workspace_id, deleted_at__isnull=True).values_list("id", "name")
        )
        self.tempat = {}  # project_id -> (divisi, departemen)
        for dp in DepartemenProject.objects.filter(
            workspace_id=workspace_id, departemen__deleted_at__isnull=True, project__deleted_at__isnull=True
        ).select_related("departemen", "departemen__divisi"):
            self.tempat[dp.project_id] = (dp.departemen.divisi, dp.departemen)

        self.manager, self.supervisor = defaultdict(list), defaultdict(list)
        for j in JabatanOrganisasi.objects.filter(
            workspace_id=workspace_id,
            tingkat__in=[TINGKAT_SUPERVISOR, TINGKAT_MANAGER],
            member__is_active=True,
        ).select_related("member"):
            if j.tingkat == TINGKAT_MANAGER and j.divisi_id:
                self.manager[j.divisi_id].append(_nama(j.member))
            elif j.tingkat == TINGKAT_SUPERVISOR and j.departemen_id:
                self.supervisor[j.departemen_id].append(_nama(j.member))


def susun_laporan(data, pids, jendela):
    """Laporan untuk satu direktur, dibatasi `pids` (project yang ia awasi)."""
    per_divisi = {}
    for pid in pids:
        if pid not in data.nama_project:
            continue
        divisi, dept = data.tempat.get(pid, (None, None))
        kunci = divisi.id if divisi else TANPA_DIVISI
        if kunci not in per_divisi:
            per_divisi[kunci] = DivisiLaporan(
                nama=divisi.nama if divisi else TANPA_DIVISI,
                pimpinan=sorted(data.manager.get(divisi.id, [])) if divisi else [],
            )
        per_divisi[kunci].unit.append(
            Unit(
                nama=dept.nama if dept else data.nama_project[pid],
                pimpinan=sorted(data.supervisor.get(dept.id, [])) if dept else [],
                angka=data.angka.get(pid, Angka()),
            )
        )
    for d in per_divisi.values():
        d.unit.sort(key=lambda u: (-u.angka.lewat, u.nama))
    # Yang paling butuh perhatian di atas; "Tanpa divisi" selalu paling bawah.
    urut = sorted(per_divisi.values(), key=lambda d: (d.nama == TANPA_DIVISI, -d.angka.lewat, d.nama))
    return Laporan(divisi=urut, jendela=jendela, hari_macet=data.hari_macet, hari_ke_depan=data.hari_ke_depan)


def direktur_workspace():
    """{workspace_id: [User]} direktur aktif, satu kali per orang per workspace."""
    hasil = defaultdict(dict)
    for j in JabatanOrganisasi.objects.filter(
        tingkat__gte=TINGKAT_DIREKTUR, member__is_active=True, member__is_bot=False
    ).select_related("member"):
        hasil[j.workspace_id][j.member_id] = j.member
    return {ws: list(orang.values()) for ws, orang in hasil.items()}


@shared_task
def kirim_ringkasan_direktur(tanggal: str | None = None):
    """Slot `ringkasan-direktur` di plane/bgtasks/jadwal_kantor.py.

    `tanggal`: tanggal kantor ISO dari penjadwal; kosong = hari ini (OFFICE_TIMEZONE).
    """
    sekarang = timezone.now()
    hari_ini = date.fromisoformat(tanggal) if tanggal else hari_ini_kantor()
    hari = jendela_hari(hari_ini, setelan_hari_kerja(DIGEST_WEEKDAYS))
    jendela = label_jendela(hari_ini, hari)
    sejak = sekarang - timedelta(hours=24 * hari)
    url = _base_url()
    koneksi, efrom = _koneksi()

    terkirim = kosong = gagal = 0
    slug = dict(Workspace.objects.values_list("id", "slug"))
    for workspace_id, direktur in direktur_workspace().items():
        data = DataWorkspace(workspace_id, hari_ini, sejak)
        for orang in direktur:
            try:
                laporan = susun_laporan(data, divisi_diawasi(orang.id, workspace_id), jendela)
                if not laporan:
                    kosong += 1
                    continue
                tautan = f"{url}/{slug.get(workspace_id, '')}" if url else ""
                subjek, teks, html = susun_email(orang, laporan, hari_ini, tautan, bahasa=bahasa_penerima(orang))
                buat_pesan(
                    ke=orang.email, subjek=subjek, html=html, teks=teks, koneksi=koneksi, dari=efrom
                ).send(fail_silently=False)
                terkirim += 1
            except Exception as e:  # noqa: BLE001
                gagal += 1
                log_exception(e)

    logger.info("Laporan direktur %s: %s terkirim, %s kosong, %s gagal", hari_ini, terkirim, kosong, gagal)
    return {"terkirim": terkirim, "kosong": kosong, "gagal": gagal}
