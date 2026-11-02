# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: laporan harian direktur
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu email per direktur per workspace per hari kerja: ikhtisar per divisi.

Keputusan user 2026-11-02 (mengganti daftar tugas selesai per project): direktur
hanya butuh gambaran dari manager dan supervisor, bukan rincian staf. Isinya
ANGKA per divisi (+ nama manager) dan per departemen (+ nama supervisor):
selesai di jendela laporan, terlambat (dan yang macet > 7 hari), jatuh tempo hari
ini, dan 7 hari ke depan. Render ada di `direktur_digest_email` (murni).

Cakupan = `divisi_diawasi()`: seluruh project, atau yang dibatasi
`PengawasanDivisi`. Struktur divisi belum diisi = tiap project jadi satu unit di
bawah "Tanpa divisi".

Tetap tanpa opt-in (KEP-42: "keep it always on"). Ringkasan harian direktur
(`daily_digest_task`) sekarang hanya berisi tugas pribadinya, jadi tidak ada
rincian tim yang dobel. Jadwal: Senin-Jumat 08.30 Jakarta; Senin mencakup Jumat
sore sampai Minggu.

ponytail: tanpa tabel pencatat "sudah terkirim"; jalankan manual dua kali = dua email.
"""

import logging
from collections import defaultdict
from datetime import timedelta

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.db.models import Count, Q
from django.utils import timezone

from plane.bgtasks.daily_digest_email import HARI_KE_DEPAN
from plane.bgtasks.daily_digest_task import _koneksi
from plane.bgtasks.deadline_reminder_email import _base_url
from plane.bgtasks.deadline_reminder_task import GRUP_SELESAI
from plane.bgtasks.direktur_digest_email import HARI_MACET, Angka, DivisiLaporan, Laporan, Unit, susun_email
from plane.db.models import (
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_SUPERVISOR,
    DepartemenProject,
    Issue,
    JabatanOrganisasi,
    Project,
    Workspace,
)
from plane.utils.exception_logger import log_exception
from plane.utils.hierarki import divisi_diawasi

logger = logging.getLogger("plane")

TANPA_DIVISI = "Tanpa divisi"


def jendela_jam(hari_ini):
    """Senin menutup akhir pekan; hari lain cukup 24 jam."""
    return 72 if hari_ini.weekday() == 0 else 24


def _nama(user):
    return user.display_name or user.first_name or user.email


class DataWorkspace:
    """Angka per project + peta project -> (divisi, departemen) + nama pimpinan, dimuat SEKALI."""

    def __init__(self, workspace_id, hari_ini, sejak):
        self.hari_ini = hari_ini
        dasar = Issue.issue_objects.filter(workspace_id=workspace_id, project__deleted_at__isnull=True)
        terbuka = Q(target_date__isnull=False) & ~Q(state__group__in=GRUP_SELESAI)
        self.angka = defaultdict(Angka)
        for baris in (
            dasar.values("project_id").annotate(
                selesai=Count("id", filter=Q(completed_at__gte=sejak)),
                lewat=Count("id", filter=terbuka & Q(target_date__lt=hari_ini)),
                macet=Count("id", filter=terbuka & Q(target_date__lt=hari_ini - timedelta(days=HARI_MACET))),
                hari=Count("id", filter=terbuka & Q(target_date=hari_ini)),
                depan=Count(
                    "id",
                    filter=terbuka
                    & Q(target_date__gt=hari_ini, target_date__lte=hari_ini + timedelta(days=HARI_KE_DEPAN)),
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
    return Laporan(divisi=urut, jendela=jendela)


def direktur_workspace():
    """{workspace_id: [User]} direktur aktif, satu kali per orang per workspace."""
    hasil = defaultdict(dict)
    for j in JabatanOrganisasi.objects.filter(
        tingkat__gte=TINGKAT_DIREKTUR, member__is_active=True, member__is_bot=False
    ).select_related("member"):
        hasil[j.workspace_id][j.member_id] = j.member
    return {ws: list(orang.values()) for ws, orang in hasil.items()}


@shared_task
def kirim_ringkasan_direktur():
    """Dijalankan sekali sehari. Lihat beat_schedule di plane/celery.py."""
    sekarang = timezone.now()
    hari_ini = timezone.localtime(sekarang).date()
    jam = jendela_jam(hari_ini)
    jendela = "Jumat s.d. Minggu" if jam == 72 else "24 jam terakhir"
    sejak = sekarang - timedelta(hours=jam)
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
                subjek, teks, html = susun_email(orang, laporan, hari_ini, tautan)
                pesan = EmailMultiAlternatives(subject=subjek, body=teks, from_email=efrom, to=[orang.email], connection=koneksi)
                pesan.attach_alternative(html, "text/html")
                pesan.send(fail_silently=False)
                terkirim += 1
            except Exception as e:  # noqa: BLE001
                gagal += 1
                log_exception(e)

    logger.info("Laporan direktur %s: %s terkirim, %s kosong, %s gagal", hari_ini, terkirim, kosong, gagal)
    return {"terkirim": terkirim, "kosong": kosong, "gagal": gagal}
