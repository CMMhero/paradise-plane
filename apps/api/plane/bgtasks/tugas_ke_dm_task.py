# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: penugasan dikirim sebagai DM
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Begitu seseorang diberi tugas, rinciannya masuk ke DM antara pemberi dan penerima.

Kenapa ini bukan pengulangan dari pemberitahuan yang sudah ada: kartu
pemberitahuan menyampaikan bahwa SESUATU terjadi, lalu hilang tujuh detik
kemudian. Yang ditanyakan orang keesokan harinya bukan itu, melainkan "tenggatnya
kapan" dan "yang diminta persisnya apa". DM tidak hilang, bisa digulung ulang,
bisa dibalas, dan sudah jadi tempat kedua orang itu bicara.

Ditulis dari SATU corong: `issue_activities_task` memanggilnya sesudah aktivitas
tersimpan, jadi jalur apa pun yang menambahkan penerima tugas ikut terlayani,
termasuk API token, tugas berulang, dan penugasan dari layar mana pun.
"""

import os

from celery import shared_task
from django.conf import settings

from plane.db.models import Issue, PesanLangsung, Ruang, User, WorkspaceMember
from plane.utils.chat_ruang import ruang_dm
from plane.utils.exception_logger import log_exception
from plane.utils.obrolan_siaran import siarkan

# Saklar pemadam. Bawaannya MENYALA, berbeda dengan ENABLE_CHAT_EMAIL yang
# bawaannya mati: yang ini menulis ke dalam aplikasi, bukan mengirim email ke
# kotak masuk orang, dan pemilik instance memang memintanya hidup. Yang tersedia
# cuma jalan keluarnya, kalau suatu saat dirasa terlalu berisik:
# `ENABLE_TUGAS_KE_DM=0` di `apps/api/.env` lalu `docker compose up -d`
# (restart saja TIDAK cukup, env file hanya dibaca ulang saat container dibuat
# ulang).
def _aktif() -> bool:
    return os.environ.get("ENABLE_TUGAS_KE_DM", "1") == "1"


BULAN = (
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
)

PRIORITAS = {
    "urgent": "Mendesak",
    "high": "Tinggi",
    "medium": "Sedang",
    "low": "Rendah",
    "none": "Belum diatur",
}

# Deskripsi tugas bisa berhalaman-halaman. Yang dibutuhkan di DM cuma cukup untuk
# tahu ini soal apa; sisanya ada satu klik jauhnya lewat tautan di bawahnya.
BATAS_DESKRIPSI = 600

# Judul juga dipotong, dan ini bukan kehati-hatian berlebihan. Judul work item
# boleh sampai 255 karakter dan boleh berisi enter; sekali ada yang menempelkan
# satu paragraf ke kolom judul, seluruh rincian di bawahnya terdorong keluar
# layar ponsel dan pesan penugasan berubah jadi dinding teks.
BATAS_JUDUL = 120

# Daftar label bisa panjang tanpa batas. Beberapa label pertama sudah cukup
# memberi konteks; selebihnya ada di halaman tugasnya.
BATAS_LABEL = 120


def _tanggal(nilai) -> str:
    """`2026-08-25` jadi `25 Agustus 2026`.

    Ditulis panjang, bukan angka semua: tugas ini dibaca orang gudang dan orang
    produksi di layar ponsel, dan "08-09" terbaca sebagai dua tanggal berbeda
    tergantung siapa yang membacanya.
    """
    if not nilai:
        return ""
    return f"{nilai.day} {BULAN[nilai.month - 1]} {nilai.year}"


def _potong(teks: str, batas: int) -> str:
    rapi = " ".join(str(teks or "").split())
    return f"{rapi[: batas - 1]}…" if len(rapi) > batas else rapi


def _base_url() -> str:
    """Alamat aplikasi untuk tautan balik.

    Diambil dari environment dan bukan ditebak, sama seperti email pengingat
    tenggat. Kalau kosong, tautannya sengaja TIDAK dikarang: pesan tanpa tautan
    masih berguna, pesan dengan tautan yang salah membuat orang mengira tugasnya
    hilang.
    """
    return (settings.APP_BASE_URL or os.environ.get("WEB_URL") or "").rstrip("/")


def susun_pesan(
    *,
    kode: str,
    judul: str,
    nama_project: str = "",
    prioritas: str = "",
    status: str = "",
    tenggat=None,
    mulai=None,
    label: str = "",
    deskripsi: str = "",
    tautan: str = "",
) -> str:
    """Susun isi DM penugasan.

    Murni supaya bisa diuji tanpa database: yang paling gampang rusak dari fitur
    ini bukan pengirimannya, melainkan barisnya. Baris kosong seperti
    "Tenggat: -" mengajari orang untuk berhenti membaca isi pesannya, jadi yang
    tidak terisi memang TIDAK ditulis sama sekali.
    """
    # Judulnya ikut dirapikan, bukan cuma dipotong: enter di dalam judul membuat
    # baris kode tugas pecah jadi dua dan rincian di bawahnya terlihat seperti
    # bagian dari judulnya.
    nama = _potong(judul, BATAS_JUDUL)
    baris = ["📋 Tugas baru untuk Anda", "", f"{kode} · {nama}" if kode else nama]

    rincian = [
        ("Project", _potong(nama_project, BATAS_JUDUL)),
        ("Prioritas", PRIORITAS.get(prioritas, "") if prioritas else ""),
        ("Status", status),
        ("Tenggat", _tanggal(tenggat)),
        ("Mulai", _tanggal(mulai)),
        ("Label", _potong(label, BATAS_LABEL)),
    ]
    terisi = [f"{nama}: {nilai}" for nama, nilai in rincian if nilai]
    if terisi:
        baris.append("")
        baris.extend(terisi)

    ringkas = _potong(deskripsi, BATAS_DESKRIPSI)
    if ringkas:
        baris.extend(["", "Deskripsi:", ringkas])

    if tautan:
        baris.extend(["", tautan])

    return "\n".join(baris)


def _isi_untuk(issue) -> str:
    kode = f"{issue.project.identifier}-{issue.sequence_id}" if issue.project_id else ""
    url = _base_url()
    return susun_pesan(
        kode=kode,
        judul=issue.name,
        nama_project=issue.project.name if issue.project_id else "",
        prioritas=issue.priority or "",
        status=issue.state.name if issue.state_id else "",
        tenggat=issue.target_date,
        mulai=issue.start_date,
        label=", ".join(sorted(lbl.name for lbl in issue.labels.all())),
        deskripsi=issue.description_stripped or "",
        tautan=(
            f"{url}/{issue.workspace.slug}/projects/{issue.project_id}/issues/{issue.id}" if url else ""
        ),
    )


def penerima_baru(aktivitas) -> list:
    """Siapa yang BARU ditambahkan sebagai penerima tugas, dari aktivitas tersimpan.

    Yang dibaca aktivitas, bukan payload permintaan. Payload berisi SELURUH
    daftar penerima setiap kali tugas disimpan, jadi menyaring dari sana berarti
    mengirim ulang rincian yang sama kepada orang yang sudah lama memegang tugas
    itu, tiap kali ada yang sekadar mengubah prioritasnya. Aktivitas hanya lahir
    untuk penerima yang benar-benar baru.

    `new_identifier` yang terisi itulah pembedanya: penerima yang DILEPAS juga
    menghasilkan baris `field="assignees"`, tapi id-nya ada di `old_identifier`.
    """
    return [
        str(a.new_identifier)
        for a in (aktivitas or [])
        if getattr(a, "field", None) == "assignees" and getattr(a, "new_identifier", None)
    ]


@shared_task
def kirim_tugas_ke_dm(issue_id, actor_id, penerima_ids):
    """Kirim rincian tugas ke DM tiap penerima yang baru ditambahkan."""
    if not _aktif() or not actor_id or not penerima_ids:
        return

    try:
        issue = (
            Issue.objects.select_related("project", "state", "workspace")
            .prefetch_related("labels")
            .filter(pk=issue_id)
            .first()
        )
        if issue is None:
            return

        # Menugaskan sesuatu kepada diri sendiri tidak perlu dikabarkan lewat
        # pesan kepada diri sendiri.
        tujuan = {str(p) for p in penerima_ids} - {str(actor_id)}
        if not tujuan:
            return

        # Hanya anggota workspace yang aktif. Penerima tugas yang sudah keluar
        # dari workspace masih bisa tercatat di baris IssueAssignee lama, dan
        # membuatkan ruang DM untuknya berarti membuat percakapan yang tidak
        # akan pernah dibuka siapa pun.
        aktif = set(
            WorkspaceMember.objects.filter(
                workspace_id=issue.workspace_id, member_id__in=tujuan, is_active=True
            ).values_list("member_id", flat=True)
        )
        if not aktif:
            return

        isi = _isi_untuk(issue)
        pengirim = User.objects.filter(pk=actor_id).first()
        if pengirim is None:
            return

        for penerima_id in aktif:
            ruang = ruang_dm(issue.workspace_id, actor_id, penerima_id)
            pesan = PesanLangsung.objects.create(
                workspace_id=issue.workspace_id,
                ruang=ruang,
                pengirim=pengirim,
                penerima_id=penerima_id,
                isi=isi,
            )
            # Denormalisasi yang membuat daftar percakapan bisa diurutkan tanpa
            # subquery, sama seperti jalur kirim biasa.
            Ruang.objects.filter(id=ruang.id).update(pesan_terakhir_pada=pesan.created_at)
            # Yang sedang membuka ruang ini melihatnya seketika. Ditaruh SESUDAH
            # pesan tersimpan: siaran yang mendahului commit membuat peramban
            # menarik ulang lalu tidak menemukan apa-apa.
            siarkan(ruang.id, "pesan", actor_id)
    except Exception as e:
        # Ditelan dan dicatat. Tugasnya sendiri sudah tersimpan dan
        # pemberitahuannya sudah jalan; gagal mengirim salinannya ke DM bukan
        # alasan untuk membuat Celery mengulang seluruh rantai aktivitas.
        log_exception(e)
    return
