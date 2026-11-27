# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: unduh daftar work item sebagai Excel
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Ekspor Excel dari sebuah daftar work item.

Baris ekspor = baris daftar (`DaftarTugas`) yang JUGA lolos `saring_boleh_diekspor`.
Saringan kedua hanya bisa membuang baris, jadi ekspor selalu subset daftarnya.

Jumlah kueri tetap, berapa pun barisnya.
"""

# Python imports
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from zoneinfo import ZoneInfo

# Django imports
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify

# Third party imports
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.serializers.view import lampirkan_status_persetujuan
from plane.db.models import Issue, IssueAssignee, IssueLabel, ModuleIssue, ProjectMember
from plane.utils.akses_privat import saring_tugas_privat
from plane.utils.daftar_tugas import DaftarTugas
from plane.utils.email_merek import bahasa_penerima
from plane.utils.email_teks import PRIORITAS
from plane.utils.ketepatan_waktu import TANPA_TENGGAT, TEPAT_WAKTU, TERLAMBAT, anotasi_ketepatan, ketepatan
from plane.utils.paginator import OffsetPaginator

BATAS_EKSPOR = 10_000
KODE_TERLALU_BANYAK = "EXPORT_TOO_LARGE"
TIPE_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_PERAN_TAMU = 5
# Karakter yang tidak sah di XML. openpyxl menolak sebagian, sisanya merusak berkas.
_KARAKTER_TERLARANG = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
_AWAL_RUMUS = ("=", "+", "-", "@")
_KOLOM_DESKRIPSI = ("description_json", "description_html", "description_stripped", "description_binary")
_FORMAT_TANGGAL = "yyyy-mm-dd"
_FORMAT_WAKTU = "yyyy-mm-dd hh:mm"

GRUP_STATUS = {
    "id": {
        "backlog": "Backlog",
        "unstarted": "Belum dimulai",
        "started": "Berjalan",
        "completed": "Selesai",
        "cancelled": "Dibatalkan",
    },
    "en": {
        "backlog": "Backlog",
        "unstarted": "Unstarted",
        "started": "Started",
        "completed": "Completed",
        "cancelled": "Cancelled",
    },
}
PERSETUJUAN = {
    "id": {"menunggu": "Menunggu persetujuan", "disetujui": "Disetujui", "ditolak": "Ditolak"},
    "en": {"menunggu": "Awaiting approval", "disetujui": "Approved", "ditolak": "Rejected"},
}
KETEPATAN = {
    "id": {TEPAT_WAKTU: "Tepat waktu", TERLAMBAT: "Terlambat", TANPA_TENGGAT: "Tanpa tenggat"},
    "en": {TEPAT_WAKTU: "On time", TERLAMBAT: "Late", TANPA_TENGGAT: "No due date"},
}
NAMA_LEMBAR = {"id": "Item kerja", "en": "Work items"}


class TerlaluBanyak(Exception):
    pass


@dataclass(frozen=True)
class Baris:
    """Satu work item beserta semua yang butuh kueri sendiri."""

    tugas: Issue
    penanggung_jawab: list[str]
    label: list[str]
    modul: list[str]
    induk: str
    sub_tugas: int


@dataclass(frozen=True)
class Konteks:
    bahasa: str
    zona: ZoneInfo


@dataclass(frozen=True)
class Kolom:
    kunci: str
    judul_id: str
    judul_en: str
    lebar: int
    nilai: Callable[[Baris, Konteks], object]


def _kode(tugas):
    return f"{tugas.project.identifier}-{tugas.sequence_id}"


def _nama(user):
    return (user.display_name or user.email) if user else ""


def _waktu_lokal(nilai: datetime | None, k: Konteks) -> datetime | None:
    # Excel tidak mengenal zona waktu: kirim jam dinding di zona user.
    return nilai.astimezone(k.zona).replace(tzinfo=None) if nilai else None


def _ketepatan(b: Baris, k: Konteks) -> str:
    """Hanya untuk tugas selesai, aturan yang sama dengan laporan selesai (KEP-62)."""
    tugas = b.tugas
    if not tugas.state or tugas.state.group != "completed" or not tugas.completed_at:
        return ""
    # `tanggal_selesai` dan `tenggat_efektif` dihitung SQL (`anotasi_ketepatan`):
    # membaca zona kantor per baris berarti satu kueri per baris.
    return KETEPATAN[k.bahasa][ketepatan(tugas.tanggal_selesai, tugas.tenggat_efektif)]


def _estimasi(b: Baris, k: Konteks) -> str:
    poin = b.tugas.estimate_point
    return poin.value if poin and poin.deleted_at is None else ""


# Urutan di sini = urutan kolom di berkas.
KOLOM: tuple[Kolom, ...] = (
    Kolom("key", "Kode", "Key", 12, lambda b, k: _kode(b.tugas)),
    Kolom("title", "Judul", "Title", 60, lambda b, k: b.tugas.name),
    Kolom("department", "Departemen", "Department", 28, lambda b, k: b.tugas.project.name),
    Kolom("state", "Status", "State", 18, lambda b, k: b.tugas.state.name if b.tugas.state else ""),
    Kolom(
        "state_group",
        "Grup status",
        "State group",
        16,
        lambda b, k: GRUP_STATUS[k.bahasa].get(b.tugas.state.group, "") if b.tugas.state else "",
    ),
    Kolom("priority", "Prioritas", "Priority", 14, lambda b, k: PRIORITAS[k.bahasa].get(b.tugas.priority, "")),
    Kolom("assignees", "Penanggung jawab", "Assignees", 30, lambda b, k: ", ".join(b.penanggung_jawab)),
    Kolom("created_by", "Dibuat oleh", "Created by", 22, lambda b, k: _nama(b.tugas.created_by)),
    Kolom("start_date", "Tanggal mulai", "Start date", 14, lambda b, k: b.tugas.start_date),
    Kolom("due_date", "Tenggat", "Due date", 14, lambda b, k: b.tugas.target_date),
    Kolom("completed_at", "Selesai pada", "Completed at", 18, lambda b, k: _waktu_lokal(b.tugas.completed_at, k)),
    Kolom(
        "approval_status",
        "Status persetujuan",
        "Approval status",
        22,
        lambda b, k: PERSETUJUAN[k.bahasa].get(b.tugas.approval_status_terbaru, ""),
    ),
    Kolom("timeliness", "Ketepatan", "Timeliness", 14, _ketepatan),
    Kolom("labels", "Label", "Labels", 24, lambda b, k: ", ".join(b.label)),
    Kolom("modules", "Modul", "Modules", 24, lambda b, k: ", ".join(b.modul)),
    Kolom("parent", "Induk", "Parent", 12, lambda b, k: b.induk),
    Kolom("sub_items", "Sub-tugas", "Sub-items", 11, lambda b, k: b.sub_tugas),
    Kolom("estimate", "Estimasi", "Estimate", 11, _estimasi),
    Kolom("created_at", "Dibuat", "Created", 18, lambda b, k: _waktu_lokal(b.tugas.created_at, k)),
    Kolom("updated_at", "Diperbarui", "Updated", 18, lambda b, k: _waktu_lokal(b.tugas.updated_at, k)),
)


def saring_boleh_diekspor(tugas, user, slug):
    """Bagian dari queryset `tugas` yang boleh masuk berkas `user`, apa pun daftar asalnya.

    Hanya project yang ia anggotai aktif, tanpa tugas privat yang tak boleh ia
    lihat, dan di project tempat ia tamu tanpa `guest_view_all_features` hanya
    buatannya sendiri. Daftar profil tidak menyaring yang terakhir itu.
    """
    keanggotaan = ProjectMember.objects.filter(workspace__slug=slug, member=user, is_active=True)
    tamu_terbatas = keanggotaan.filter(role=_PERAN_TAMU, project__guest_view_all_features=False)
    tugas = tugas.filter(project_id__in=keanggotaan.values("project_id")).exclude(
        Q(project_id__in=tamu_terbatas.values("project_id")) & ~Q(created_by=user)
    )
    return saring_tugas_privat(tugas, user)


def _id_berurutan(daftar: DaftarTugas, user, slug):
    """Id baris ekspor dalam urutan daftar, tanpa kembar.

    Saringan relasi (dua assignee, dua label) bisa mengembalikan satu tugas dua kali.
    """
    # Syaratnya ditempel ke kueri daftar, bukan `pk__in=<subkueri tugas>`, supaya
    # tabel tugas tidak digabung dengan dirinya sendiri atas ribuan baris.
    terurut = saring_boleh_diekspor(daftar.terurut, user, slug)
    terurut = OffsetPaginator(terurut, order_by=daftar.urutan).ordered_queryset()
    ids = list(dict.fromkeys(terurut.prefetch_related(None).values_list("pk", flat=True)))
    if len(ids) > BATAS_EKSPOR:
        raise TerlaluBanyak
    return ids


def _kumpulkan(pasangan):
    """[(issue_id, nama)] -> {issue_id: [nama]}"""
    hasil = {}
    for issue_id, nama in pasangan:
        hasil.setdefault(issue_id, []).append(nama)
    return hasil


def _muat_baris(ids, user, slug) -> list[Baris]:
    tugas = (
        Issue.issue_objects.select_related("project", "state", "estimate_point", "created_by", "parent__project")
        # Isi deskripsi tidak masuk berkas dan bisa besar sekali kali ribuan baris.
        .defer(*(awalan + kolom for awalan in ("", "parent__") for kolom in _KOLOM_DESKRIPSI))
        .annotate(**anotasi_ketepatan())
        .in_bulk(ids)
    )
    # Id yang hilang di antara dua kueri (dihapus saat mengunduh) dilewati.
    urut = lampirkan_status_persetujuan(tugas[i] for i in ids if i in tugas)

    # Manajer bawaan ketiga model ini membuang baris penghubung yang sudah dihapus.
    penanggung_jawab = _kumpulkan(
        (issue_id, nama or email)
        for issue_id, nama, email in IssueAssignee.objects.filter(issue_id__in=ids)
        .order_by("assignee__display_name", "assignee_id")
        .values_list("issue_id", "assignee__display_name", "assignee__email")
    )
    label = _kumpulkan(
        IssueLabel.objects.filter(issue_id__in=ids, label__deleted_at__isnull=True)
        .order_by("label__name", "label_id")
        .values_list("issue_id", "label__name")
    )
    modul = _kumpulkan(
        ModuleIssue.objects.filter(issue_id__in=ids, module__deleted_at__isnull=True, module__archived_at__isnull=True)
        .order_by("module__name", "module_id")
        .values_list("issue_id", "module__name")
    )
    sub_tugas = dict(
        Issue.issue_objects.filter(parent_id__in=ids)
        .order_by()
        .values("parent_id")
        .annotate(jumlah=Count("id"))
        .values_list("parent_id", "jumlah")
    )
    # Kode induk hanya untuk induk yang boleh dilihat user.
    induk = Issue.issue_objects.filter(pk__in={t.parent_id for t in urut if t.parent_id})
    induk_terlihat = set(saring_boleh_diekspor(induk, user, slug).values_list("pk", flat=True))

    return [
        Baris(
            tugas=t,
            penanggung_jawab=penanggung_jawab.get(t.id, []),
            label=label.get(t.id, []),
            modul=modul.get(t.id, []),
            induk=_kode(t.parent) if t.parent_id in induk_terlihat else "",
            sub_tugas=sub_tugas.get(t.id, 0),
        )
        for t in urut
    ]


def _sel(lembar, nilai):
    """Satu sel. Teks selalu disimpan sebagai teks, tidak pernah sebagai rumus."""
    if isinstance(nilai, str):
        teks = _KARAKTER_TERLARANG.sub("", nilai)
        sel = WriteOnlyCell(lembar, value=teks)
        sel.data_type = "s"
        # Seperti mengetik apostrof di Excel, tanpa apostrof yang terlihat:
        # sel tetap teks walau user menyuntingnya.
        if teks.startswith(_AWAL_RUMUS):
            sel.quotePrefix = True
        return sel
    sel = WriteOnlyCell(lembar, value=nilai)
    if isinstance(nilai, datetime):
        sel.number_format = _FORMAT_WAKTU
    elif isinstance(nilai, date):
        sel.number_format = _FORMAT_TANGGAL
    return sel


def susun_xlsx(baris: list[Baris], konteks: Konteks) -> bytes:
    buku = Workbook(write_only=True)
    lembar = buku.create_sheet(NAMA_LEMBAR[konteks.bahasa])
    # Mode write-only: lebar, panel beku, dan filter harus diatur sebelum baris pertama.
    for nomor, kolom in enumerate(KOLOM, start=1):
        lembar.column_dimensions[get_column_letter(nomor)].width = kolom.lebar
    lembar.freeze_panes = "A2"
    lembar.auto_filter.ref = f"A1:{get_column_letter(len(KOLOM))}{len(baris) + 1}"

    judul = []
    for kolom in KOLOM:
        sel = _sel(lembar, kolom.judul_id if konteks.bahasa == "id" else kolom.judul_en)
        sel.font = Font(bold=True)
        judul.append(sel)
    lembar.append(judul)
    for b in baris:
        lembar.append([_sel(lembar, kolom.nilai(b, konteks)) for kolom in KOLOM])

    keluaran = BytesIO()
    buku.save(keluaran)
    return keluaran.getvalue()


def nama_berkas(nama, hari: date) -> str:
    """`<nama>-work-items-YYYY-MM-DD.xlsx`, hanya huruf, angka, dan tanda hubung."""
    awalan = slugify(nama or "")[:60].strip("-_")
    return "-".join(filter(None, [awalan, "work-items", hari.isoformat()])) + ".xlsx"


def unduh_xlsx(request, slug, daftar: DaftarTugas):
    """Respons unduhan .xlsx untuk `daftar`. `?export_name=` menjadi awalan nama berkas."""
    try:
        ids = _id_berurutan(daftar, request.user, slug)
    except TerlaluBanyak:
        return Response(
            {
                "error": (
                    f"This list has more than {BATAS_EKSPOR} work items. Narrow it with filters, then export again."
                ),
                "code": KODE_TERLALU_BANYAK,
                "limit": BATAS_EKSPOR,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    konteks = Konteks(bahasa=bahasa_penerima(request.user), zona=ZoneInfo(request.user.user_timezone))
    isi = susun_xlsx(_muat_baris(ids, request.user, slug), konteks)
    berkas = nama_berkas(request.query_params.get("export_name"), timezone.now().astimezone(konteks.zona).date())
    respons = HttpResponse(isi, content_type=TIPE_XLSX)
    respons["Content-Disposition"] = f'attachment; filename="{berkas}"'
    respons["Cache-Control"] = "no-store"
    return respons
