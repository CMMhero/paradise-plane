# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pengingat tenggat
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Pengingat tenggat work item, lewat email dan (sejak 2026-11-02) inbox di aplikasi.

Titiknya diatur di God Mode (KEP-83, DEADLINE_REMINDER_EMAIL_DAYS); bawaannya
delapan titik: H-7, H-5, H-3, H-1, hari H, lalu H+3, H+5, H+7 sebagai OVERDUE.

Tiap email membawa lampiran `.ics` supaya penerima bisa memasukkan tenggatnya ke
kalender apa pun dengan sekali klik: Outlook (yang dipakai kantor), Google, atau
ponsel. Ini sengaja dipilih daripada integrasi Google Calendar langsung, karena
integrasi itu terganjal dua hal di luar kendali kita: aplikasi belum HTTPS, dan
Google mewajibkan verifikasi untuk scope kalender pada akun non-Workspace.
Lampiran ICS tidak butuh keduanya dan melayani semua orang, bukan hanya pengguna
Gmail.
"""

import logging
from datetime import date, datetime, timedelta

from plane.db.models import Issue, Notification, PengingatTenggat
from plane.utils.exception_logger import log_exception
from plane.utils.menunggu_persetujuan import menunggu_tidak_terlambat, q_bisa_terlambat, q_menunggu_persetujuan
from plane.utils.penerima_aktif import aktif_sejak, batas_aktif
from plane.utils.preferensi_email import boleh_email, penyaring
from plane.utils.saklar_instance import ENABLE_DEADLINE_REMINDER, saklar_aktif
from plane.utils.setelan_instance import (
    DEADLINE_REMINDER_EMAIL_DAYS,
    DEADLINE_REMINDER_INBOX_DAYS,
    setelan_hari,
    zona_kantor,
)

from .deadline_reminder_email import kirim_email_pengingat, kirim_email_pengingat_bersama  # noqa: F401
from celery import shared_task

logger = logging.getLogger("plane")

# Baris inbox tenggat (tulis_inbox_tenggat). `field` dibaca kartu inbox di apps/web.
SENDER_TENGGAT = "in_app:deadline"
FIELD_TENGGAT = "deadline"
# KEP-84: baris untuk PENYETUJU tugas yang menunggu persetujuan selesai dan
# lewat tenggat. Sender sendiri supaya tidak bertabrakan dengan baris staf.
SENDER_TENGGAT_PENYETUJU = "in_app:deadline_approval"
VERB_PENYETUJU = "approval_overdue"


def titik_email() -> tuple:
    """Titik pengingat email (God Mode DEADLINE_REMINDER_EMAIL_DAYS), dibaca tiap putaran.

    Bawaan -7,-5,-3,-1,0,3,5,7: H-7 sampai hari H, lalu H+3, H+5, H+7 sebagai OVERDUE.
    """
    return setelan_hari(DEADLINE_REMINDER_EMAIL_DAYS)


def titik_inbox() -> tuple:
    """Titik baris inbox (God Mode DEADLINE_REMINDER_INBOX_DAYS), dibaca tiap putaran.

    Bawaan -1,0,1,3,7: H-1, hari H, lalu terlambat H+1, H+3, H+7. Lebih jarang
    daripada email: inbox yang terisi delapan baris per tugas berhenti dibaca.
    """
    return setelan_hari(DEADLINE_REMINDER_INBOX_DAYS)


def hari_ini_kantor() -> date:
    """Tanggal hari ini menurut OFFICE_TIMEZONE (Celery dan Django berjalan di UTC)."""
    return datetime.now(zona_kantor()).date()

# Tugas yang sudah selesai atau dibatalkan tidak perlu diingatkan lagi,
# termasuk yang sudah lewat tenggat.
GRUP_SELESAI = ["completed", "cancelled"]

# Saklar pengaman, MATI secara bawaan. Fitur ini mengirim email massal ke
# seluruh karyawan, jadi menyalakannya harus tindakan sadar, bukan efek samping
# dari sebuah deploy. Diatur Super Admin di God Mode > Fitur & otomasi, berlaku
# di putaran berikutnya tanpa membuat ulang container.
#
# Saklar ini hanya menjaga tugas terjadwal. `kirim_email_pengingat()` tetap bisa
# dipanggil langsung untuk mengirim contoh ke satu alamat saat pengujian.
def _aktif() -> bool:
    return saklar_aktif(ENABLE_DEADLINE_REMINDER)


def _label_titik(titik: int) -> str:
    if titik == 0:
        return "jatuh tempo hari ini"
    if titik < 0:
        return f"tinggal {-titik} hari lagi"
    return f"TERLAMBAT {titik} hari"


def _orang_tugas(issue):
    """Penanggung jawab + pembuat, aktif dan bukan bot. Himpunan: diri sendiri dihitung sekali."""
    orang = {a for a in issue.assignees.filter(is_active=True, is_bot=False)}
    if issue.created_by and issue.created_by.is_active and not issue.created_by.is_bot:
        orang.add(issue.created_by)
    return orang


def _baris_inbox(issue, penerima_id, titik, tenggat, penyetuju=False):
    data_issue = {
        "id": str(issue.id),
        "name": issue.name,
        "identifier": issue.project.identifier,
        "sequence_id": issue.sequence_id,
        "state_name": issue.state.name if issue.state else "",
        "state_group": issue.state.group if issue.state else "",
    }
    return Notification(
        workspace_id=issue.workspace_id,
        project_id=issue.project_id,
        sender=_sender_inbox(titik, tenggat, penyetuju),
        triggered_by=None,
        receiver_id=penerima_id,
        entity_identifier=issue.id,
        entity_name="issue",
        title="",
        data={
            "issue": data_issue,
            "issue_activity": {
                "id": None,
                # Dibaca kartu inbox (apps/web notification-card/content.tsx):
                # new_value = selisih hari terhadap tenggat, negatif = belum lewat.
                # KEP-84: `approval_overdue` = baris untuk penyetuju (tugas sudah
                # diajukan selesai, belum diputuskan, tenggatnya lewat).
                "verb": VERB_PENYETUJU if penyetuju else ("overdue" if titik > 0 else "due"),
                "field": FIELD_TENGGAT,
                "actor": None,
                "new_value": str(titik),
                "old_value": "",
                "new_identifier": None,
                "old_identifier": None,
            },
        },
    )


def _sender_inbox(titik, tenggat, penyetuju=False) -> str:
    # Tanggal tenggat ikut di sender: kalau tenggat digeser, titik yang sama untuk
    # tenggat baru adalah kabar baru, bukan duplikat.
    awalan = SENDER_TENGGAT_PENYETUJU if penyetuju else SENDER_TENGGAT
    return f"{awalan}:{titik}:{tenggat.isoformat()}"


def _titik_lewat(titik_semua) -> tuple:
    """Titik SESUDAH tenggat saja (> 0): penyetuju diingatkan begitu tenggat lewat,
    bukan sebelumnya. Pekerjaannya sudah diserahkan; yang ditunggu keputusannya."""
    return tuple(t for t in titik_semua if t > 0)


def penyetuju_tugas_menunggu(tenggat) -> tuple[list, dict]:
    """(tugas, {issue_id: {id penyetuju}}) untuk tugas yang menunggu persetujuan
    selesai dengan Due date = `tenggat` (KEP-84).

    Penyetuju = aturan yang sama dengan pemberitahuan pengajuan
    (`beritahu_diajukan`): `calon_penyetuju` project itu, disaring jenjang pemohon
    (`saring_penyetuju`), tanpa pemohonnya sendiri. Dihitung sekali per project.
    """
    from plane.db.models import STATUS_PERSETUJUAN_MENUNGGU, PersetujuanPenugasan  # noqa: PLC0415
    from plane.utils.hierarki import calon_penyetuju, peta_tingkat, saring_penyetuju  # noqa: PLC0415

    antrian = list(
        Issue.issue_objects.filter(target_date=tenggat)
        .filter(q_menunggu_persetujuan())
        .exclude(state__group__in=GRUP_SELESAI)
        .exclude(project__archived_at__isnull=False)
        .select_related("project", "workspace", "state", "created_by")
    )
    if not antrian:
        return [], {}
    pemohon = dict(
        PersetujuanPenugasan.objects.filter(
            issue_id__in=[i.id for i in antrian], status=STATUS_PERSETUJUAN_MENUNGGU
        ).values_list("issue_id", "pemohon_id")
    )
    peta, calon, hasil = {}, {}, {}
    for issue in antrian:
        ws = issue.workspace_id
        # KEP-93: jenjang yang berlaku DI project itu, jadi peta per project.
        kunci = (ws, issue.project_id)
        if kunci not in peta:
            peta[kunci] = peta_tingkat(ws, issue.project_id)
            calon[kunci] = calon_penyetuju(ws, issue.project_id, peta=peta[kunci])
        pid = pemohon.get(issue.id)
        hasil[issue.id] = {uid for uid in saring_penyetuju(calon[kunci], peta[kunci], pid) if uid != pid}
    return antrian, hasil


def tulis_inbox_penyetuju(hari_ini):
    """Baris inbox untuk penyetuju tugas menunggu yang lewat tenggat (KEP-84).

    Titiknya = titik inbox God Mode yang sesudah tenggat. Disaring saklar
    `inbox_approval` tiap orang (direktur mati, KEP-59). Hanya saat
    APPROVAL_PENDING_NOT_LATE hidup: mati = stafnya yang diingatkan, seperti dulu.
    """
    if not menunggu_tidak_terlambat():
        return 0
    ditulis = 0
    for titik in _titik_lewat(titik_inbox()):
        tenggat = hari_ini - timedelta(days=titik)
        antrian, penyetuju = penyetuju_tugas_menunggu(tenggat)
        if not antrian:
            continue
        boleh = penyaring(set().union(*penyetuju.values()), "inbox_approval")
        sender = _sender_inbox(titik, tenggat, penyetuju=True)
        sudah = set(
            Notification.objects.filter(
                sender=sender, entity_identifier__in=[i.id for i in antrian]
            ).values_list("entity_identifier", "receiver_id")
        )
        baru = [
            _baris_inbox(issue, uid, titik, tenggat, penyetuju=True)
            for issue in antrian
            for uid in penyetuju[issue.id] & boleh
            if (issue.id, uid) not in sudah
        ]
        Notification.objects.bulk_create(baru, batch_size=100)
        ditulis += len(baru)
    return ditulis


def _catat_terkirim(issue, kelompok, titik, tenggat):
    PengingatTenggat.objects.bulk_create(
        [
            PengingatTenggat(
                workspace_id=issue.workspace_id,
                project_id=issue.project_id,
                issue=issue,
                penerima=orang,
                titik=titik,
                tenggat=tenggat,
            )
            for orang in kelompok
        ]
    )


def kirim_email_penyetuju(hari_ini) -> dict:
    """Email ke penyetuju tugas menunggu yang lewat tenggat (KEP-84).

    Ikut rem ENABLE_DEADLINE_REMINDER (dipanggil sesudahnya) dan titik email God
    Mode sesudah tenggat. Disaring saklar email `approval` tiap orang (kabar
    persetujuan) dan member aktif. Sekali per (tugas, orang, titik, tenggat),
    dicatat di PengingatTenggat seperti pengingat staf.
    """
    from plane.db.models import User  # noqa: PLC0415

    terkirim = dilewati = gagal = 0
    if not menunggu_tidak_terlambat():
        return {"terkirim": 0, "dilewati": 0, "gagal": 0}
    batas = batas_aktif()
    for titik in _titik_lewat(titik_email()):
        tenggat = hari_ini - timedelta(days=titik)
        antrian, penyetuju = penyetuju_tugas_menunggu(tenggat)
        if not antrian:
            continue
        orang = {
            u.id: u
            for u in User.objects.filter(id__in=set().union(*penyetuju.values()), is_active=True, is_bot=False)
            if aktif_sejak(u, batas) and boleh_email(u.id, "approval")
        }
        for issue in antrian:
            penerima = [orang[uid] for uid in penyetuju[issue.id] if uid in orang]
            sudah = set(
                PengingatTenggat.objects.filter(
                    issue=issue, penerima__in=penerima, titik=titik, tenggat=tenggat
                ).values_list("penerima_id", flat=True)
            )
            dilewati += len(sudah)
            belum = [o for o in penerima if o.id not in sudah]
            if not belum:
                continue
            for kelompok, galat in kirim_email_pengingat_bersama(issue, belum, titik, penyetuju=True):
                if galat is not None:
                    gagal += len(kelompok)
                    log_exception(galat)
                    continue
                _catat_terkirim(issue, kelompok, titik, tenggat)
                terkirim += len(kelompok)
    return {"terkirim": terkirim, "dilewati": dilewati, "gagal": gagal}


def tulis_inbox_tenggat(hari_ini):
    """Baris inbox "jatuh tempo" dan "terlambat" untuk yang saklar `inbox_deadline`-nya hidup.

    Keputusan user 2026-11-02: kabar terlambat juga harus terlihat di inbox, bukan
    cuma lewat email. Tidak mengirim email apa pun, jadi TIDAK ikut rem
    ENABLE_DEADLINE_REMINDER. Titiknya dari `titik_inbox()` (God Mode).
    """
    ditulis = 0
    # KEP-84: tugas yang sudah diajukan selesai tidak diingatkan ke stafnya;
    # penyetujunya yang diingatkan (`tulis_inbox_penyetuju`).
    bisa_terlambat = q_bisa_terlambat()
    for titik in titik_inbox():
        tenggat = hari_ini - timedelta(days=titik)
        antrian = list(
            Issue.issue_objects.filter(target_date=tenggat)
            .filter(bisa_terlambat)
            .exclude(state__group__in=GRUP_SELESAI)
            .exclude(project__archived_at__isnull=False)
            .select_related("project", "workspace", "state", "created_by")
            .prefetch_related("assignees")
        )
        if not antrian:
            continue
        orang = {issue.id: {o.id for o in _orang_tugas(issue)} for issue in antrian}
        boleh_inbox = penyaring(set().union(*orang.values()), "inbox_deadline")
        sender = _sender_inbox(titik, tenggat)
        sudah = set(
            Notification.objects.filter(
                sender=sender, entity_identifier__in=[i.id for i in antrian]
            ).values_list("entity_identifier", "receiver_id")
        )
        baru = [
            _baris_inbox(issue, uid, titik, tenggat)
            for issue in antrian
            for uid in orang[issue.id] & boleh_inbox
            if (issue.id, uid) not in sudah
        ]
        Notification.objects.bulk_create(baru, batch_size=100)
        ditulis += len(baru)
    return ditulis


def _penerima(issue):
    """Siapa yang diingatkan: yang dikerjai tugasnya, dan yang memberi tugas.

    Keputusan user 2026-08-11. Kalau seseorang memberi tugas ke dirinya sendiri,
    ia tetap menerima satu email, bukan dua, karena dikumpulkan sebagai himpunan.

    Bot dan akun nonaktif dibuang: mengirim ke akun mati hanya menghasilkan
    bounce yang mengotori reputasi pengirim.

    Lalu disaring saklar `deadline_reminder` yang berlaku (keputusan user
    2026-10-30): hidup untuk staf, mati untuk pimpinan kecuali dinyalakan sendiri.
    """
    # ENABLE_EMAIL_ACTIVE_ONLY: yang lama tak membuka aplikasi tidak diemail
    # (inbox tenggat tetap ditulis `tulis_inbox_tenggat`).
    batas = batas_aktif()
    return {o for o in _orang_tugas(issue) if aktif_sejak(o, batas) and boleh_email(o.id, "deadline_reminder")}


@shared_task
def kirim_pengingat_tenggat(tanggal: str | None = None):
    """Dijalankan sekali sehari oleh slot `pengingat-tenggat` di plane/bgtasks/jadwal_kantor.py
    (jam DEADLINE_REMINDER_TIME, tiap hari termasuk akhir pekan).

    `tanggal`: tanggal kantor ISO yang diklaim penjadwal. Kosong = hari ini menurut
    OFFICE_TIMEZONE (panggilan manual).

    Menghitung ulang dari `target_date` yang berlaku HARI INI, bukan dari
    jadwal yang disimpan di depan. Jadi kalau tenggat digeser, pengingatnya
    ikut bergeser sendiri tanpa perlu ada yang membatalkan jadwal lama.
    """
    hari_ini = date.fromisoformat(tanggal) if tanggal else hari_ini_kantor()
    # Inbox SENGAJA ditulis sebelum rem ENABLE_DEADLINE_REMINDER dan tidak ikut
    # rem itu: saklarnya berlabel email di God Mode, dan baris inbox diatur saklar
    # `inbox_deadline` milik tiap orang. Mematikan email tidak boleh ikut
    # membungkam inbox (keputusan user 2026-11-02, dipertahankan di KEP-83).
    try:
        inbox = tulis_inbox_tenggat(hari_ini)
        logger.info("Inbox tenggat %s: %s baris", hari_ini, inbox)
    except Exception as e:  # noqa: BLE001
        # Inbox gagal tidak boleh menahan email pengingat.
        log_exception(e)
    try:
        inbox_penyetuju = tulis_inbox_penyetuju(hari_ini)
        logger.info("Inbox tenggat penyetuju %s: %s baris", hari_ini, inbox_penyetuju)
    except Exception as e:  # noqa: BLE001
        log_exception(e)

    if not _aktif():
        logger.info("Pengingat tenggat dilewati: ENABLE_DEADLINE_REMINDER mati di God Mode")
        return {"aktif": False}

    terkirim = dilewati = gagal = 0
    bisa_terlambat = q_bisa_terlambat()

    for titik in titik_email():
        # titik -7 berarti "7 hari sebelum tenggat", jadi tenggatnya hari_ini + 7.
        tenggat = hari_ini - timedelta(days=titik)

        antrian = (
            Issue.issue_objects.filter(target_date=tenggat)
            .filter(bisa_terlambat)
            .exclude(state__group__in=GRUP_SELESAI)
            .exclude(project__archived_at__isnull=False)
            .select_related("project", "workspace", "state", "created_by")
            .prefetch_related("assignees")
        )

        for issue in antrian:
            penerima = _penerima(issue)
            sudah = set(
                PengingatTenggat.objects.filter(
                    issue=issue, penerima__in=penerima, titik=titik, tenggat=tenggat
                ).values_list("penerima_id", flat=True)
            )
            dilewati += len(sudah)
            belum = [o for o in penerima if o.id not in sudah]
            if not belum:
                continue

            # Satu email bersama (To: a; b; c) untuk semua orang di tugas ini,
            # dipecah hanya per bahasa dan posisi di utas. Kelompok yang gagal
            # tidak menahan kelompok lain maupun tugas berikutnya.
            for kelompok, galat in kirim_email_pengingat_bersama(issue, belum, titik, label=_label_titik(titik)):
                if galat is not None:
                    gagal += len(kelompok)
                    log_exception(galat)
                    continue

                # Dicatat SESUDAH terkirim. Kalau dicatat lebih dulu lalu
                # pengiriman gagal, pengingat itu hilang selamanya karena
                # dianggap sudah dikirim.
                PengingatTenggat.objects.bulk_create(
                    [
                        PengingatTenggat(
                            workspace_id=issue.workspace_id,
                            project_id=issue.project_id,
                            issue=issue,
                            penerima=orang,
                            titik=titik,
                            tenggat=tenggat,
                        )
                        for orang in kelompok
                    ]
                )
                terkirim += len(kelompok)

    # KEP-84: penyetuju tugas menunggu yang lewat tenggat. Angkanya digabung ke
    # total: satu laporan untuk semua email pengingat hari ini.
    try:
        penyetuju = kirim_email_penyetuju(hari_ini)
        terkirim += penyetuju["terkirim"]
        dilewati += penyetuju["dilewati"]
        gagal += penyetuju["gagal"]
    except Exception as e:  # noqa: BLE001
        log_exception(e)

    logger.info(
        "Pengingat tenggat %s: %s terkirim, %s dilewati (sudah pernah), %s gagal",
        hari_ini,
        terkirim,
        dilewati,
        gagal,
    )
    return {"terkirim": terkirim, "dilewati": dilewati, "gagal": gagal}
