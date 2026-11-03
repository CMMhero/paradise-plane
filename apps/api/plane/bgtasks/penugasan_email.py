# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: email "tugas baru untuk Anda"
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu email ke tiap orang yang BARU ditambahkan sebagai penanggung jawab tugas.

Keputusan user 2026-11-02: staf harus tahu lewat email begitu atasannya memberi
tugas. Sebelumnya kabar itu cuma lewat DM (`tugas_ke_dm_task`) dan email umum
Plane yang menumpang saklar `property_change`, yang bawaannya mati untuk semua
jabatan (KEP-42), jadi praktis staf tidak pernah diemail.

Dipicu dari corong yang sama dengan DM (`issue_activities_task`), jadi semua jalur
penugasan ikut: layar mana pun, API token, tugas berulang. Penerima disaring
saklar `assigned` (bawaan: hidup untuk staf, mati untuk pimpinan). Tugas yang
punya tenggat ikut membawa lampiran `.ics`, sama dengan pengingat tenggat.
"""

from celery import shared_task

from plane.bgtasks.daily_digest_task import _koneksi
from plane.bgtasks.deadline_reminder_email import _base_url, bangun_ics, tanggal_id
from plane.bgtasks.tugas_ke_dm_task import BATAS_DESKRIPSI, BATAS_JUDUL, _potong
from plane.db.models import Issue, User, WorkspaceMember
from plane.db.models.hierarki import TINGKAT_NAMA
from plane.utils.email_merek import (
    WARNA,
    avatar_untuk,
    bahasa_penerima,
    baris_orang,
    bungkus,
    buat_pesan,
    catatan_kecil,
    judul_html,
    kartu,
    paragraf,
    tanggal,
    terjemah_data,
    tombol,
    url_preferensi,
)
from plane.utils.email_teks import PRIORITAS
from plane.utils.exception_logger import log_exception
from plane.utils.hierarki import tingkat_anggota
from plane.utils.preferensi_email import boleh_email

TEKS = {
    "id": {
        "subjek": "[Tugas baru] {kode} {judul}",
        "subjek_tenggat": " (tenggat {tenggat})",
        "sapaan": "Halo {nama},",
        "kalimat": "{siapa} memberi Anda tugas baru.",
        "judul": "Tugas baru untuk Anda",
        "project": "Project",
        "prioritas": "Prioritas",
        "status": "Status",
        "mulai": "Mulai",
        "tenggat": "Tenggat",
        "deskripsi": "Deskripsi:",
        "tombol": "Buka tugas",
        "buka": "Buka: {url}",
        "ics": "Berkas .ics terlampir untuk memasukkan tenggat ini ke kalender Anda.",
        "alasan": "Anda menerima email ini karena Anda ditambahkan sebagai penanggung jawab.",
    },
    "en": {
        "subjek": "[New task] {kode} {judul}",
        "subjek_tenggat": " (due {tenggat})",
        "sapaan": "Hi {nama},",
        "kalimat": "{siapa} gave you a new task.",
        "judul": "A new task for you",
        "project": "Project",
        "prioritas": "Priority",
        "status": "State",
        "mulai": "Start",
        "tenggat": "Due date",
        "deskripsi": "Description:",
        "tombol": "Open work item",
        "buka": "Open: {url}",
        "ics": "An .ics file is attached so you can add this deadline to your calendar.",
        "alasan": "You received this email because you were added as an assignee.",
    },
}


def _nama(user) -> str:
    return (getattr(user, "display_name", "") or getattr(user, "first_name", "") or getattr(user, "email", "")).strip()


def susun_email_penugasan(
    issue, penerima, pemberi, jabatan_pemberi: str = "", tautan: str = "", bahasa="id", gambar=None
):
    """(subjek, teks, html). Murni kecuali foto pemberi (dibaca dari storage, boleh gagal).

    Baris yang kosong (tanpa tenggat, tanpa deskripsi) tidak ditulis sama sekali,
    alasan yang sama dengan DM penugasan: "Tenggat: -" mengajari orang berhenti
    membaca.
    """
    s = TEKS.get(bahasa, TEKS["id"])
    kode = f"{issue.project.identifier}-{issue.sequence_id}"
    judul = _potong(issue.name, BATAS_JUDUL)
    siapa = _nama(pemberi) + (f" ({terjemah_data(jabatan_pemberi, bahasa)})" if jabatan_pemberi else "")
    tenggat = tanggal(issue.target_date, bahasa)
    subjek = s["subjek"].format(kode=kode, judul=judul)
    if tenggat:
        subjek += s["subjek_tenggat"].format(tenggat=tenggat)

    prioritas = PRIORITAS.get(bahasa, PRIORITAS["id"])
    rincian = [
        (s["project"], issue.project.name),
        (s["prioritas"], prioritas.get(issue.priority or "", "")),
        (s["status"], issue.state.name if getattr(issue, "state", None) else ""),
        (s["mulai"], tanggal(issue.start_date, bahasa)),
        (s["tenggat"], tenggat, WARNA["bahaya"]),
    ]
    rincian = [r for r in rincian if r[1]]
    deskripsi = _potong(getattr(issue, "description_stripped", "") or "", BATAS_DESKRIPSI)
    sapaan = s["sapaan"].format(nama=_nama(penerima)).replace(" ,", ",")
    kalimat = s["kalimat"].format(siapa=siapa)

    teks = [sapaan, "", kalimat, "", f"  {kode}  {judul}"]
    teks += [f"  {r[0]:<9}: {r[1]}" for r in rincian]
    if deskripsi:
        teks += ["", s["deskripsi"], deskripsi]
    if tautan:
        teks += ["", s["buka"].format(url=tautan)]
    if tenggat:
        teks += ["", s["ics"]]

    av, _ = avatar_untuk(pemberi, gambar=gambar)
    jabatan = terjemah_data(jabatan_pemberi, bahasa) if jabatan_pemberi else ""
    isi = (
        judul_html(s["judul"])
        + baris_orang(av, jabatan)
        + paragraf(f"{sapaan} {kalimat}")
        + kartu(kode, judul, tautan, rincian, catatan=deskripsi)
        + tombol(s["tombol"], tautan)
        + (catatan_kecil(s["ics"]) if tenggat else "")
    )
    html = bungkus(
        isi,
        bahasa=bahasa,
        judul=subjek,
        pratajuk=kalimat,
        alasan=s["alasan"],
        url_preferensi=url_preferensi(getattr(getattr(issue, "workspace", None), "slug", "")),
        email_penerima=getattr(penerima, "email", ""),
    )
    return subjek, "\n".join(teks), html


def penerima_email(issue, actor_id, penerima_ids) -> list:
    """Orang yang dikirimi: baru ditugaskan, bukan pemberinya, anggota aktif, saklar `assigned` hidup."""
    tujuan = {str(p) for p in penerima_ids or []} - {str(actor_id)}
    if not tujuan:
        return []
    aktif = WorkspaceMember.objects.filter(
        workspace_id=issue.workspace_id, member_id__in=tujuan, is_active=True
    ).values_list("member_id", flat=True)
    orang = User.objects.filter(id__in=aktif, is_active=True, is_bot=False)
    return [o for o in orang if boleh_email(o.id, "assigned")]


@shared_task
def kirim_email_penugasan(issue_id, actor_id, penerima_ids):
    """Dipanggil `issue_activities_task` untuk penerima yang BARU ditambahkan."""
    if not actor_id or not penerima_ids:
        return {"terkirim": 0, "gagal": 0}
    issue = Issue.objects.select_related("project", "state", "workspace").filter(pk=issue_id).first()
    pemberi = User.objects.filter(pk=actor_id).first()
    if issue is None or pemberi is None:
        return {"terkirim": 0, "gagal": 0}
    penerima = penerima_email(issue, actor_id, penerima_ids)
    if not penerima:
        return {"terkirim": 0, "gagal": 0}

    tingkat = tingkat_anggota(pemberi.id, issue.workspace_id)
    jabatan = TINGKAT_NAMA.get(tingkat, "") if tingkat else ""
    url = _base_url()
    tautan = f"{url}/{issue.workspace.slug}/projects/{issue.project_id}/issues/{issue.id}" if url else ""
    kode = f"{issue.project.identifier}-{issue.sequence_id}"
    ics = (
        bangun_ics(
            issue=issue,
            judul=f"{kode} {issue.name}",
            deskripsi=f"Project {issue.project.name}. Tenggat {tanggal_id(issue.target_date)}."
            + (f" {tautan}" if tautan else ""),
            url=tautan,
        )
        if issue.target_date
        else None
    )
    lampiran = [(f"{kode}.ics", ics, "text/calendar; method=PUBLISH")] if ics else []

    koneksi, efrom = _koneksi()
    terkirim = gagal = 0
    for orang in penerima:
        try:
            gambar = []
            subjek, teks, html = susun_email_penugasan(
                issue, orang, pemberi, jabatan, tautan, bahasa=bahasa_penerima(orang), gambar=gambar
            )
            buat_pesan(
                ke=orang.email,
                subjek=subjek,
                html=html,
                teks=teks,
                koneksi=koneksi,
                dari=efrom,
                gambar=gambar,
                lampiran=lampiran,
            ).send(fail_silently=False)
            terkirim += 1
        except Exception as e:  # noqa: BLE001
            # Satu alamat rusak tidak boleh menahan rekan setugasnya.
            gagal += 1
            log_exception(e)
    return {"terkirim": terkirim, "gagal": gagal}
