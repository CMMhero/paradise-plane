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
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape

from plane.bgtasks.daily_digest_task import _koneksi
from plane.bgtasks.deadline_reminder_email import KANTOR, PRODUK, _base_url, bangun_ics, tanggal_id
from plane.bgtasks.tugas_ke_dm_task import BATAS_DESKRIPSI, BATAS_JUDUL, PRIORITAS, _potong, _tanggal
from plane.db.models import Issue, User, WorkspaceMember
from plane.db.models.hierarki import TINGKAT_NAMA
from plane.utils.exception_logger import log_exception
from plane.utils.hierarki import tingkat_anggota
from plane.utils.preferensi_email import boleh_email

GELAP, ABU, MERAH = "#1f2937", "#6b7280", "#b91c1c"


def _nama(user) -> str:
    return (getattr(user, "display_name", "") or getattr(user, "first_name", "") or getattr(user, "email", "")).strip()


def susun_email_penugasan(issue, penerima, pemberi, jabatan_pemberi: str = "", tautan: str = ""):
    """(subjek, teks, html). Murni, tanpa I/O: semua yang dibaca ada di argumen.

    Baris yang kosong (tanpa tenggat, tanpa deskripsi) tidak ditulis sama sekali,
    alasan yang sama dengan DM penugasan: "Tenggat: -" mengajari orang berhenti
    membaca.
    """
    kode = f"{issue.project.identifier}-{issue.sequence_id}"
    judul = _potong(issue.name, BATAS_JUDUL)
    siapa = _nama(pemberi) + (f" ({jabatan_pemberi})" if jabatan_pemberi else "")
    tenggat = _tanggal(issue.target_date)
    subjek = f"[Tugas baru] {kode} {judul}" + (f" (tenggat {tenggat})" if tenggat else "")

    rincian = [
        ("Project", issue.project.name),
        ("Prioritas", PRIORITAS.get(issue.priority or "", "")),
        ("Status", issue.state.name if getattr(issue, "state", None) else ""),
        ("Mulai", _tanggal(issue.start_date)),
        ("Tenggat", tenggat),
    ]
    rincian = [(k, v) for k, v in rincian if v]
    deskripsi = _potong(getattr(issue, "description_stripped", "") or "", BATAS_DESKRIPSI)
    sapaan = _nama(penerima)

    teks = [f"Halo {sapaan},".strip(), "", f"{siapa} memberi Anda tugas baru.", "", f"  {kode}  {judul}"]
    teks += [f"  {k:<9}: {v}" for k, v in rincian]
    if deskripsi:
        teks += ["", "Deskripsi:", deskripsi]
    if tautan:
        teks += ["", f"Buka: {tautan}"]
    if tenggat:
        teks += ["", "Lampiran .ics terlampir untuk memasukkan tenggat ini ke kalender Anda."]
    teks += ["", f"Email otomatis dari {PRODUK}. Atur di Profil > Notifikasi. Tidak perlu dibalas."]

    sel_kiri = f"padding:4px 12px 4px 0;color:{ABU};vertical-align:top"
    baris = "".join(
        f'<tr><td style="{sel_kiri}">{escape(k)}</td><td style="padding:4px 0;'
        f'{"color:" + MERAH + ";font-weight:bold" if k == "Tenggat" else ""}">{escape(v)}</td></tr>'
        for k, v in rincian
    )
    tombol = (
        f'<p><a href="{escape(tautan)}" style="background:{GELAP};color:#fff;padding:8px 16px;border-radius:4px;'
        f'text-decoration:none;display:inline-block">Buka tugas</a></p>'
        if tautan
        else ""
    )
    html = (
        f'<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:{GELAP};max-width:560px">'
        f"<p>Halo {escape(sapaan)},</p>"
        f"<p><strong>{escape(siapa)}</strong> memberi Anda tugas baru.</p>"
        f'<p style="font-size:16px;margin:16px 0 4px"><strong>{escape(kode)}</strong> {escape(judul)}</p>'
        f'<table style="border-collapse:collapse;margin:8px 0 16px;font-size:13px">{baris}</table>'
        + (
            f'<div style="background:#f9fafb;border-left:3px solid #e5e7eb;padding:8px 12px;margin:0 0 16px;'
            f'font-size:13px;white-space:pre-wrap">{escape(deskripsi)}</div>'
            if deskripsi
            else ""
        )
        + tombol
        + (
            f'<p style="color:{ABU};font-size:12px">Berkas <strong>.ics</strong> terlampir. Buka sekali untuk '
            f"memasukkan tenggat ini ke kalender Anda.</p>"
            if tenggat
            else ""
        )
        + f'<p style="color:#9ca3af;font-size:11px;margin-top:24px">Email otomatis dari {PRODUK}, sistem internal '
        f"{KANTOR}. Atur di Profil &gt; Notifikasi. Tidak perlu dibalas.</p></div>"
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

    koneksi, efrom = _koneksi()
    terkirim = gagal = 0
    for orang in penerima:
        try:
            subjek, teks, html = susun_email_penugasan(issue, orang, pemberi, jabatan, tautan)
            pesan = EmailMultiAlternatives(subject=subjek, body=teks, from_email=efrom, to=[orang.email], connection=koneksi)
            pesan.attach_alternative(html, "text/html")
            if ics:
                pesan.attach(f"{kode}.ics", ics, "text/calendar; method=PUBLISH")
            pesan.send(fail_silently=False)
            terkirim += 1
        except Exception as e:  # noqa: BLE001
            # Satu alamat rusak tidak boleh menahan rekan setugasnya.
            gagal += 1
            log_exception(e)
    return {"terkirim": terkirim, "gagal": gagal}
