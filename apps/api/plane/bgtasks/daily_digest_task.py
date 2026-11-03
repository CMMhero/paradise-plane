# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: ringkasan tugas harian lewat email
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu email ringkasan per orang per workspace per hari kerja: jatuh tempo hari
ini, 7 hari ke depan, dan terlambat. Isinya disesuaikan jabatan (KEP-43):

    staf       -> tugas yang di-assign ke dia + tugas yang ia berikan ke orang lain
    supervisor -> + project SEMUA departemennya
    manager    -> + project divisinya
    direktur   -> TANPA bagian tim (keputusan user 2026-11-02): ikhtisar divisinya
                  datang lewat laporan direktur (`direktur_digest_task`), angka saja

Cakupan tim dibaca dari `divisi_diawasi`, sumber yang sama dengan wewenang
memutuskan persetujuan, jadi "yang dia awasi" tidak punya dua definisi.

HIDUP secara bawaan untuk semua jabatan (keputusan user 2026-10-30) dan
menggantikan pengingat per tugas (`deadline_reminder_task`, kini bawaannya mati).
Orang mematikannya sendiri di Profil > Notifikasi. Jadwal: Senin-Jumat 08.30
Jakarta (beat_schedule di plane/celery.py).

Edisi sore (`kirim_ringkasan_sore`, 17.30 Jakarta, saklar `daily_digest_sore`,
keputusan user 2026-11-02): isi sama, ditambah yang SELESAI hari ini, dan jendela
depan menyempit ke hari kerja berikutnya. Lihat docstring daily_digest_email.

ponytail: tidak ada tabel pencatat "sudah terkirim hari ini". Beat memicu sekali
sehari; kalau task dijalankan manual dua kali, orang menerima dua email.
"""

import logging
from collections import defaultdict
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from celery import shared_task
from django.core.mail import get_connection

from plane.bgtasks.daily_digest_email import (
    HARI_KE_DEPAN,
    GrupTim,
    Kelompok,
    Ringkasan,
    hari_ke_hari_kerja_berikutnya,
    kelompokkan,
    susun_email,
)
from plane.bgtasks.deadline_reminder_task import GRUP_SELESAI
from plane.utils.email_merek import bahasa_penerima, buat_pesan
from plane.db.models import (
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_SUPERVISOR,
    Departemen,
    Divisi,
    Issue,
    IssueAssignee,
    UserNotificationPreference,
    Workspace,
    WorkspaceMember,
)
from plane.license.utils.instance_value import get_email_configuration
from plane.utils.exception_logger import log_exception
from plane.utils.hierarki import divisi_diawasi, semua_departemen_ids, semua_divisi_ids, tingkat_efektif
from plane.utils.preferensi_email import saklar_efektif

logger = logging.getLogger("plane")

NAMA_PERAN = {TINGKAT_SUPERVISOR: "Supervisor", TINGKAT_MANAGER: "Manager", TINGKAT_DIREKTUR: "Direktur"}

# Celery dan Django berjalan di UTC. "Hari ini" dan "selesai hari ini" harus hari
# kantor: tugas yang selesai 06.30 WIB tercatat 23.30 UTC kemarin.
ZONA_KANTOR = ZoneInfo("Asia/Jakarta")


def hari_ini_kantor():
    return datetime.now(ZONA_KANTOR).date()


class TugasWorkspace:
    """Semua tugas terbuka dalam jendela ringkasan di satu workspace, dimuat SEKALI.

    Tiap penerima lalu disaring di memori: 90 orang x 3 bagian tidak boleh berarti
    270 kueri tugas.
    """

    def __init__(self, workspace_id, hari_ini, hari_ke_depan=HARI_KE_DEPAN, dengan_selesai=False):
        self.hari_ke_depan = hari_ke_depan
        self.tugas = list(
            Issue.issue_objects.filter(
                workspace_id=workspace_id,
                project__deleted_at__isnull=True,
                target_date__isnull=False,
                target_date__lte=hari_ini + timedelta(days=hari_ke_depan),
            )
            .exclude(state__group__in=GRUP_SELESAI)
            .select_related("project", "workspace", "state")
        )
        # Edisi sore: yang pindah ke grup "completed" sejak 00.00 WIB hari ini,
        # bertenggat atau tidak. Dibatalkan (cancelled) bukan "selesai".
        self.selesai_ids = set()
        if dengan_selesai:
            awal = datetime.combine(hari_ini, time.min, tzinfo=ZONA_KANTOR)
            selesai = list(
                Issue.issue_objects.filter(
                    workspace_id=workspace_id,
                    project__deleted_at__isnull=True,
                    state__group="completed",
                    completed_at__gte=awal,
                    completed_at__lt=awal + timedelta(days=1),
                ).select_related("project", "workspace", "state")
            )
            self.selesai_ids = {i.id for i in selesai}
            self.tugas += selesai
        # Lewat IssueAssignee (manajer soft-delete), bukan `issue.assignees`: M2M
        # through ikut membawa penugasan yang sudah dicabut.
        self.assignee = defaultdict(set)
        self.nama = defaultdict(list)
        for ia in IssueAssignee.objects.filter(
            issue_id__in=[i.id for i in self.tugas], assignee__is_active=True
        ).select_related("assignee"):
            self.assignee[ia.issue_id].add(ia.assignee_id)
            self.nama[ia.issue_id].append(ia.assignee.display_name or ia.assignee.first_name or ia.assignee.email)


def _cakupan(user_id, workspace_id, tingkat, jumlah_project):
    """(cakupan, judul_tim) untuk baris peran dan judul bagian tim."""
    if tingkat >= TINGKAT_DIREKTUR:
        return "Seluruh divisi", "Seluruh divisi"
    if tingkat >= TINGKAT_MANAGER:
        nama = list(Divisi.objects.filter(id__in=semua_divisi_ids(user_id, workspace_id)).values_list("nama", flat=True))
        judul = "Divisi Anda"
    else:
        nama = list(
            Departemen.objects.filter(id__in=semua_departemen_ids(user_id, workspace_id)).values_list("nama", flat=True)
        )
        judul = "Departemen Anda" if tingkat >= TINGKAT_SUPERVISOR else ""
    if nama:
        return ", ".join(sorted(nama)), judul
    # Struktur divisi/departemen belum diisi: jangkauan jatuh ke keanggotaan project.
    return (f"{jumlah_project} project" if jumlah_project else ""), (judul and "Project yang Anda awasi")


def _saring_bagian(kelompok, bagian):
    """Kosongkan jendela tenggat yang dimatikan orangnya (digest_terlambat/hari_ini/depan).

    "Selesai hari ini" (edisi sore) bagian dari "hari ini", jadi ikut `digest_hari_ini`.
    """
    hari_ini_hidup = bagian.get("digest_hari_ini", True)
    return Kelompok(
        hari=kelompok.hari if hari_ini_hidup else [],
        depan=kelompok.depan if bagian.get("digest_depan", True) else [],
        lewat=kelompok.lewat if bagian.get("digest_terlambat", True) else [],
        selesai=kelompok.selesai if hari_ini_hidup else [],
    )


def _kelompok(daftar, data, hari_ini, bagian):
    """Kelompok tenggat untuk tugas terbuka, plus yang selesai hari ini (edisi sore)."""
    kelompok = kelompokkan([i for i in daftar if i.id not in data.selesai_ids], hari_ini, data.hari_ke_depan)
    kelompok.selesai = sorted(
        (i for i in daftar if i.id in data.selesai_ids), key=lambda i: (i.completed_at, i.sequence_id)
    )
    return _saring_bagian(kelompok, bagian)


def susun_ringkasan(user, workspace_id, data, hari_ini, bagian=None, sore=False):
    """Ringkasan satu orang di satu workspace, disaring dari `data` (TugasWorkspace).

    `bagian`: saklar SAKLAR_RINGKASAN yang berlaku untuk orangnya (keputusan user
    2026-11-02, ringkasan bisa diatur per bagian). None = semua bagian.
    `sore`: edisi 17.30; `data` sebaiknya dimuat dengan `dengan_selesai=True`.
    """
    bagian = bagian or {}
    tingkat = tingkat_efektif(user.id, workspace_id)
    sendiri = [i for i in data.tugas if user.id in data.assignee[i.id]]
    diberikan = [
        i for i in data.tugas if i.created_by_id == user.id and data.assignee[i.id] and user.id not in data.assignee[i.id]
    ]
    # Daftar utuh tetap dipakai untuk mencegah tugas yang sama tampil lagi di bagian tim.
    sudah = {i.id for i in sendiri} | {i.id for i in diberikan}
    if not bagian.get("digest_diberikan", True):
        diberikan = []

    # Direktur: tanpa bagian tim. Ikhtisar divisinya datang lewat laporan direktur
    # (direktur_digest_task), angka saja, tanpa rincian staf (keputusan 2026-11-02).
    pids = divisi_diawasi(user.id, workspace_id) if TINGKAT_SUPERVISOR <= tingkat < TINGKAT_DIREKTUR else set()
    cakupan, judul_tim = _cakupan(user.id, workspace_id, tingkat, len(pids))
    ringkasan = Ringkasan(
        peran=NAMA_PERAN.get(tingkat, "Staf"),
        cakupan=cakupan,
        sendiri=_kelompok(sendiri, data, hari_ini, bagian),
        diberikan=_kelompok(diberikan, data, hari_ini, bagian),
        judul_tim=judul_tim or "Tim Anda",
        penanggung=data.nama,
        bagian=bagian,
        sore=sore,
        hari_ke_depan=data.hari_ke_depan,
    )
    if not pids or not bagian.get("digest_tim", True):
        return ringkasan

    per_project = defaultdict(list)
    for i in data.tugas:
        if i.project_id in pids and i.id not in sudah:
            per_project[i.project].append(i)
    grup = [GrupTim(nama=p.name, tugas=_kelompok(t, data, hari_ini, bagian)) for p, t in per_project.items()]
    # Yang paling butuh perhatian di atas: terlambat terbanyak, lalu hari ini.
    ringkasan.tim = sorted(grup, key=lambda g: (-len(g.tugas.lewat), -len(g.tugas.hari), g.nama))
    return ringkasan


def penerima_dan_saklar(workspace_id, kunci="daily_digest"):
    """[(user, saklar_berlaku)] untuk anggota aktif yang saklar `kunci`-nya BERLAKU hidup.

    `kunci`: `daily_digest` (edisi pagi) atau `daily_digest_sore`.
    """
    anggota = list(
        WorkspaceMember.objects.filter(
            workspace_id=workspace_id, is_active=True, member__is_active=True, member__is_bot=False
        ).select_related("member")
    )
    pref = {
        p.user_id: p
        for p in UserNotificationPreference.objects.filter(
            user_id__in=[a.member_id for a in anggota], workspace=None, project=None
        )
    }
    hasil = [(a.member, saklar_efektif(pref.get(a.member_id), a.member_id)) for a in anggota]
    return [(orang, saklar) for orang, saklar in hasil if saklar[kunci]]


def penerima_workspace(workspace_id):
    """Anggota aktif yang saklar `daily_digest`-nya BERLAKU hidup (bawaan: semua)."""
    return [orang for orang, _ in penerima_dan_saklar(workspace_id)]


def _koneksi():
    host, user, pwd, port, use_tls, use_ssl, efrom = get_email_configuration()
    koneksi = get_connection(
        host=host,
        port=int(port),
        username=user,
        password=pwd,
        use_tls=str(use_tls) == "1",
        use_ssl=str(use_ssl) == "1",
        timeout=30,
    )
    return koneksi, efrom


def _kirim(sore):
    hari_ini = hari_ini_kantor()
    kunci = "daily_digest_sore" if sore else "daily_digest"
    hari_ke_depan = hari_ke_hari_kerja_berikutnya(hari_ini) if sore else HARI_KE_DEPAN
    koneksi, efrom = _koneksi()

    terkirim = kosong = gagal = 0
    for workspace_id in Workspace.objects.values_list("id", flat=True):
        penerima = penerima_dan_saklar(workspace_id, kunci)
        if not penerima:
            continue
        data = TugasWorkspace(workspace_id, hari_ini, hari_ke_depan, dengan_selesai=sore)
        for orang, saklar in penerima:
            try:
                ringkasan = susun_ringkasan(orang, workspace_id, data, hari_ini, saklar, sore=sore)
                if not ringkasan:
                    kosong += 1
                    continue
                subjek, teks, html = susun_email(orang, ringkasan, hari_ini, bahasa=bahasa_penerima(orang))
                buat_pesan(
                    ke=orang.email, subjek=subjek, html=html, teks=teks, koneksi=koneksi, dari=efrom
                ).send(fail_silently=False)
                terkirim += 1
            except Exception as e:  # noqa: BLE001
                # Satu alamat rusak tidak boleh menahan ringkasan orang lain.
                gagal += 1
                log_exception(e)

    edisi = "sore" if sore else "pagi"
    logger.info("Ringkasan %s %s: %s terkirim, %s kosong, %s gagal", edisi, hari_ini, terkirim, kosong, gagal)
    return {"terkirim": terkirim, "kosong": kosong, "gagal": gagal}


@shared_task
def kirim_ringkasan_harian():
    """Edisi pagi, 08.30 WIB. Lihat beat_schedule di plane/celery.py."""
    return _kirim(sore=False)


@shared_task
def kirim_ringkasan_sore():
    """Edisi sore, 17.30 WIB. Lihat beat_schedule di plane/celery.py."""
    return _kirim(sore=True)
