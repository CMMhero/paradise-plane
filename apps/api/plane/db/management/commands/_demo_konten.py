# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: isi data demo, konten pelengkap
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Lampiran, tautan, relasi, reaksi, worklog, draft, Wiki, riwayat login, kunjungan.

Berkas berawalan `_` supaya Django tidak membacanya sebagai command.

Dipanggil SESUDAH work item demo ada; bahannya dibaca ulang dari database,
bukan dioper dari command, supaya tiap bagian bisa dipahami sendiri.

Wiki mengikuti KEP-51/KEP-94: folder Divisi sudah dibuat `pastikan_folder_unit`;
sub-topik (`WikiFolder`) dibuat admin (hanya admin yang boleh), materinya
(`WikiMaterial`) diunggah anggota departemen di bawah divisi itu (hak unggah
mereka), sehingga kolom "pengunggah" di Wiki menunjuk orang yang memang boleh.
"""

# Python imports
from datetime import timedelta

# Third party imports
from crum import impersonate

# Module imports
from plane.db.management.commands import _demo_berkas as berkas
from plane.db.management.commands import _demo_data as data
from plane.db.models import (
    DraftIssue,
    DraftIssueAssignee,
    FileAsset,
    Issue,
    IssueComment,
    IssueLink,
    IssueReaction,
    IssueRelation,
    IssueWorkLog,
    CommentReaction,
    LoginActivity,
    State,
    UserRecentVisit,
    WikiFolder,
    WikiMaterial,
)

SUMBER = "seed-demo"
REAKSI = ["128077", "127881", "128640", "128064", "9989"]  # kode emoji seperti yang dikirim web
UA = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 Version/18.1 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 14; SM-A556E) AppleWebKit/537.36 Chrome/131.0 Mobile Safari/537.36",
]
SUB_TOPIK = [
    ("SOP & Prosedur", "Prosedur kerja baku divisi."),
    ("Template & Formulir", "Formulir dan template yang dipakai sehari-hari."),
]
TAUTAN = [
    ("Folder dokumen di Google Drive", "https://drive.google.com/drive/folders/demo"),
    ("Spreadsheet rekap", "https://docs.google.com/spreadsheets/d/demo"),
    ("Referensi regulasi", "https://peraturan.go.id"),
]


def isi_konten(cmd):
    """Semua konten pelengkap untuk project demo. Kembalikan ringkasan jumlah."""
    hitung = {"lampiran": 0, "tautan": 0, "relasi": 0, "worklog": 0, "draft": 0, "materi_wiki": 0}
    for kode_dep, project in cmd.project.items():
        _isi_issue(cmd, kode_dep, project, hitung)
        _draft(cmd, kode_dep, project, hitung)
    _draft_admin(cmd, next(iter(cmd.project.values())), hitung)
    _wiki(cmd, hitung)
    _riwayat_login(cmd)
    _kunjungan(cmd)
    return hitung


# ------------------------------------------------------------ work item


def _isi_issue(cmd, kode_dep, project, hitung):
    rng = cmd.rng
    induk = list(Issue.objects.filter(project=project, parent__isnull=True).order_by("sequence_id"))
    for issue in induk:
        pembuat = issue.created_by or cmd.supervisor[kode_dep]
        if rng.random() < 0.35:
            _lampiran_issue(cmd, project, issue, pembuat)
            hitung["lampiran"] += 1
        if rng.random() < 0.3:
            judul, url = rng.choice(TAUTAN)
            with impersonate(pembuat):
                IssueLink.objects.create(project=project, workspace=cmd.ws, issue=issue, title=judul, url=url)
            hitung["tautan"] += 1
        if rng.random() < 0.25:
            for u in rng.sample(cmd.staf[kode_dep], k=min(2, len(cmd.staf[kode_dep]))):
                with impersonate(u):
                    IssueReaction.objects.get_or_create(
                        project=project, workspace=cmd.ws, issue=issue, actor=u, reaction=rng.choice(REAKSI)
                    )
    for a, b in zip(induk[::2], induk[1::2]):
        if rng.random() < 0.5:
            jenis = rng.choice(["relates_to", "blocked_by"])
            with impersonate(cmd.supervisor[kode_dep]):
                IssueRelation.objects.get_or_create(
                    project=project, workspace=cmd.ws, issue=a, related_issue=b, relation_type=jenis
                )
            hitung["relasi"] += 1
    _worklog(cmd, project, hitung)
    for c in IssueComment.objects.filter(project=project):
        if rng.random() < 0.3:
            pembaca = rng.choice([cmd.supervisor[kode_dep], *cmd.staf[kode_dep]])
            if pembaca.id != c.actor_id:
                with impersonate(pembaca):
                    CommentReaction.objects.get_or_create(
                        project=project, workspace=cmd.ws, comment=c, actor=pembaca, reaction=rng.choice(REAKSI)
                    )


def _lampiran_issue(cmd, project, issue, pembuat):
    rng, slug = cmd.rng, project.identifier.lower()
    pilihan = rng.choice(["pdf", "png", "csv"])
    if pilihan == "pdf":
        nama, tipe = f"{slug}-{issue.sequence_id}-laporan.pdf", "application/pdf"
        isi = berkas.pdf(
            issue.name, [f"Project: {project.name}", "", "Ringkasan pekerjaan dan catatan progres.", "Dokumen demo."]
        )
    elif pilihan == "png":
        nama, tipe = f"{slug}-{issue.sequence_id}-grafik.png", "image/png"
        isi = berkas.png_grafik([rng.randint(20, 100) for _ in range(6)])
    else:
        nama, tipe = f"{slug}-{issue.sequence_id}-data.csv", "text/csv"
        isi = berkas.csv(["Minggu", "Target", "Realisasi"], [(f"M{i}", 100, rng.randint(60, 120)) for i in range(1, 5)])
    berkas.unggah(
        cmd.ws,
        pembuat,
        nama,
        isi,
        tipe,
        FileAsset.EntityTypeContext.ISSUE_ATTACHMENT,
        project=project,
        issue=issue,
        entity_identifier=str(issue.id),
    )


def _worklog(cmd, project, hitung):
    """Catatan waktu untuk tugas yang sedang/sudah dikerjakan, oleh assignee-nya."""
    rng = cmd.rng
    qs = Issue.objects.filter(project=project, state__group__in=["started", "completed"]).prefetch_related(
        "issue_assignee"
    )
    for issue in qs:
        for ia in issue.issue_assignee.all()[:1]:
            for _ in range(rng.randint(1, 3)):
                kapan = cmd.now - timedelta(days=rng.randint(1, 20), hours=rng.randint(0, 8))
                with impersonate(ia.assignee):
                    IssueWorkLog.objects.create(
                        project=project,
                        workspace=cmd.ws,
                        issue=issue,
                        logged_by=ia.assignee,
                        duration=rng.choice([30, 45, 60, 90, 120, 180, 240]),
                        description=rng.choice(["Mengerjakan draft", "Koordinasi dengan tim", "Revisi", "Finalisasi"]),
                        logged_at=kapan,
                    )
                hitung["worklog"] += 1


def _draft(cmd, kode_dep, project, hitung):
    for u in cmd.staf[kode_dep][:1]:
        _buat_draft(cmd, project, u, f"Draft: usulan perbaikan proses {project.name}", hitung)


def _draft_admin(cmd, project, hitung):
    """Draft milik Super Admin. Menempel ke project demo, jadi ikut terhapus saat --reset."""
    _buat_draft(cmd, project, cmd.actor, f"Draft: rencana audit akses {project.name}", hitung)


def _buat_draft(cmd, project, pemilik, judul, hitung):
    backlog = State.objects.filter(project=project, group="backlog").first()
    with impersonate(pemilik):
        d = DraftIssue.objects.create(
            workspace=cmd.ws,
            project=project,
            name=judul,
            description_html="<p>Masih dirapikan sebelum diajukan.</p>",
            priority="medium",
            state=backlog,
        )
        DraftIssueAssignee.objects.create(workspace=cmd.ws, project=project, draft_issue=d, assignee=pemilik)
    hitung["draft"] += 1


# ----------------------------------------------------------------- wiki


def _wiki(cmd, hitung):
    for kode, nama, deps in data.ORGANISASI:
        folder = WikiFolder.objects.filter(workspace=cmd.ws, divisi__nama=nama).first()
        if folder is None:
            continue
        kode_dep = [k for k, _ in deps]
        pengunggah = [cmd.supervisor[d] for d in kode_dep] + [u for d in kode_dep for u in cmd.staf[d][:2]]
        for judul, ket in SUB_TOPIK:
            topik = WikiFolder(workspace=cmd.ws, parent=folder, nama=judul, keterangan=ket)
            topik.save(created_by_id=cmd.actor.id)
            for n in range(cmd.rng.randint(2, 3)):
                _materi(cmd, topik, nama, judul, cmd.rng.choice(pengunggah), n)
                hitung["materi_wiki"] += 1
        # Super Admin boleh mengunggah ke divisi mana pun (KEP-51); satu materi per divisi.
        _materi(cmd, topik, nama, judul, cmd.actor, 3)
        hitung["materi_wiki"] += 1


def _materi(cmd, topik, nama_divisi, judul, pengunggah, n):
    singkat = nama_divisi.split()[0].lower()
    if judul.startswith("SOP"):
        nama = f"sop-{singkat}-{n + 1}.pdf"
        isi = berkas.pdf(
            f"SOP {nama_divisi} #{n + 1}",
            ["1. Tujuan", "2. Ruang lingkup", "3. Langkah kerja", "4. Dokumen terkait", "", "Dokumen demo."],
        )
        tipe = "application/pdf"
    elif n % 2 == 0:
        nama, tipe = f"template-{singkat}-{n + 1}.csv", "text/csv"
        isi = berkas.csv(["No", "Uraian", "PIC", "Tenggat"], [(i, "Isi uraian", "-", "-") for i in range(1, 6)])
    else:
        nama, tipe = f"catatan-{singkat}-{n + 1}.txt", "text/plain"
        isi = berkas.txt(f"Catatan {judul} divisi {nama_divisi}.\nGunakan template terbaru di folder ini.\n")
    aset = berkas.unggah(
        cmd.ws,
        pengunggah,
        nama,
        isi,
        tipe,
        FileAsset.EntityTypeContext.WIKI_MATERIAL,
        entity_identifier=str(topik.id),
    )
    WikiMaterial(id=aset.id, workspace=cmd.ws, folder=topik, berkas=aset, judul=nama).save(
        created_by_id=pengunggah.id
    )


# ------------------------------------------------- jejak pemakaian akun


def _riwayat_login(cmd):
    """Login (dan sebagian logout) 14 hari terakhir: mengisi God Mode > Logs > Activity."""
    rng, baris = cmd.rng, []
    for u in _semua_orang(cmd):
        for _ in range(rng.randint(3, 9)):
            masuk = cmd.now - timedelta(days=rng.randint(0, 13), hours=rng.randint(0, 10), minutes=rng.randint(0, 59))
            ip, ua = f"10.10.{rng.randint(1, 20)}.{rng.randint(2, 250)}", rng.choice(UA)
            kunci = f"demo-{u.id.hex[:8]}-{int(masuk.timestamp())}"
            baris.append(
                LoginActivity(
                    user=u,
                    jenis="LOGIN",
                    terjadi_pada=masuk,
                    ip=ip,
                    user_agent=ua,
                    medium="email",
                    permukaan="app",
                    session_key=kunci,
                )
            )
            if rng.random() < 0.6:
                baris.append(
                    LoginActivity(
                        user=u,
                        jenis="LOGOUT",
                        terjadi_pada=masuk + timedelta(hours=rng.randint(1, 9)),
                        ip=ip,
                        user_agent=ua,
                        permukaan="app",
                        session_key=kunci,
                    )
                )
    LoginActivity.objects.bulk_create(baris)
    for u in _semua_orang(cmd):
        terakhir = max((b.terjadi_pada for b in baris if b.user_id == u.id and b.jenis == "LOGIN"), default=None)
        if terakhir:
            type(u).objects.filter(pk=u.pk).update(last_login=terakhir, last_active=terakhir)


def _kunjungan(cmd):
    """Home > Recents: project departemennya dan beberapa tugas yang baru dibuka."""
    for dep, users in cmd.staf.items():
        project = cmd.project[dep]
        tugas = list(Issue.objects.filter(project=project).values_list("id", flat=True)[:6])
        for u in [cmd.supervisor[dep], *users]:
            kunjungan = [("project", project.id)] + [("issue", t) for t in cmd.rng.sample(tugas, k=min(3, len(tugas)))]
            for i, (jenis, ident) in enumerate(kunjungan):
                UserRecentVisit.objects.create(
                    workspace=cmd.ws,
                    project=project,
                    user=u,
                    entity_name=jenis,
                    entity_identifier=ident,
                    visited_at=cmd.now - timedelta(hours=i * 3 + cmd.rng.randint(0, 2)),
                )


def _semua_orang(cmd):
    orang = [*cmd.direktur, *cmd.manager.values(), *cmd.supervisor_user.values()]
    return orang + [u for users in cmd.staf.values() for u in users]
