# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: unduh daftar work item sebagai Excel
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Ekspor Excel dari sebuah daftar work item.

Tiga lembar: work item (dengan deskripsinya), komentar, dan riwayat perubahan.
Dua lembar terakhir hanya memuat work item yang ada di lembar pertama.

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
from django.db.models import Case, Count, F, Q, TextField, Value, When
from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify

# Third party imports
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.serializers.view import lampirkan_status_persetujuan
from plane.db.models import (
    FileAsset,
    Issue,
    IssueActivity,
    IssueAssignee,
    IssueComment,
    IssueLabel,
    ModuleIssue,
    ProjectMember,
)
from plane.utils.akses_privat import saring_tugas_privat
from plane.utils.daftar_tugas import DaftarTugas
from plane.utils.email_merek import bahasa_penerima
from plane.utils.ekspor_riwayat import FIELD_TERSEMBUNYI, merujuk_tugas, uraikan
from plane.utils.email_teks import PRIORITAS
from plane.utils.ketepatan_waktu import TANPA_TENGGAT, TEPAT_WAKTU, TERLAMBAT, anotasi_ketepatan, ketepatan
from plane.utils.paginator import OffsetPaginator
from plane.utils.teks_html import sebutan_massal, teks_dokumen

BATAS_EKSPOR = 10_000
KODE_TERLALU_BANYAK = "EXPORT_TOO_LARGE"
TIPE_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_PERAN_TAMU = 5
# Karakter yang tidak sah di XML. openpyxl menolak sebagian, sisanya merusak berkas.
_KARAKTER_TERLARANG = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
_AWAL_RUMUS = ("=", "+", "-", "@")
_KOLOM_DESKRIPSI = ("description_json", "description_html", "description_stripped", "description_binary")
_ATAS = Alignment(vertical="top")
_ATAS_BUNGKUS = Alignment(vertical="top", wrap_text=True)
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
NAMA_LEMBAR_KOMENTAR = {"id": "Komentar", "en": "Comments"}
NAMA_LEMBAR_AKTIVITAS = {"id": "Aktivitas", "en": "Activity"}
# Kata pengganti gambar dan berkas di teks deskripsi dan komentar.
KATA_SISIPAN = {"id": ("gambar", "berkas"), "en": ("image", "file")}
SISTEM = {"id": "Sistem", "en": "System"}


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
    # HTML editor jadi teks; sebutannya sudah dimuat sekaligus.
    teks: Callable[[str | None], str]


@dataclass(frozen=True)
class Kolom:
    kunci: str
    judul_id: str
    judul_en: str
    lebar: int
    nilai: Callable[[Baris, Konteks], object]
    bungkus: bool = False


@dataclass(frozen=True)
class Lembar:
    nama: str
    # (judul, lebar, bungkus teks)
    kolom: list[tuple[str, int, bool]]
    baris: list[list[object]]


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
    # Paling akhir supaya kolom lain tetap di tempatnya.
    Kolom("description", "Deskripsi", "Description", 80, lambda b, k: k.teks(b.tugas.description_html), bungkus=True),
)

# (judul id, judul en, lebar, bungkus teks)
KOLOM_KOMENTAR = (
    ("Kode", "Key", 12, False),
    ("Judul", "Title", 50, False),
    ("Penulis", "Author", 22, False),
    ("Waktu", "Date", 18, False),
    ("Komentar", "Comment", 90, True),
)
KOLOM_AKTIVITAS = (
    ("Kode", "Key", 12, False),
    ("Judul", "Title", 50, False),
    ("Oleh", "Who", 22, False),
    ("Waktu", "Date", 18, False),
    ("Perubahan", "What changed", 20, False),
    ("Dari", "From", 30, False),
    ("Menjadi", "To", 40, True),
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
        # Hanya `description_html` yang masuk berkas; bentuk lainnya bisa besar sekali kali ribuan baris.
        .defer(
            *(kolom for kolom in _KOLOM_DESKRIPSI if kolom != "description_html"),
            *(f"parent__{kolom}" for kolom in _KOLOM_DESKRIPSI),
        )
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


def _muat_komentar(ids, keanggotaan) -> list[dict]:
    """Komentar work item yang diekspor, hanya dari project yang user anggotai (seperti riwayat di aplikasi)."""
    return list(
        IssueComment.objects.filter(issue_id__in=ids, project_id__in=keanggotaan, project__archived_at__isnull=True)
        .order_by("created_at", "id")
        .values("issue_id", "comment_html", "created_at", "actor__display_name", "actor__email")
    )


def _muat_aktivitas(ids, keanggotaan) -> list[dict]:
    # Isi lama dan baru deskripsi adalah dokumen HTML utuh: tidak ditarik sama sekali.
    tanpa_dokumen = {
        nama: Case(When(field="description", then=Value("")), default=F(kolom), output_field=TextField())
        for nama, kolom in (("lama", "old_value"), ("baru", "new_value"))
    }
    return list(
        IssueActivity.objects.filter(issue_id__in=ids, project_id__in=keanggotaan, project__archived_at__isnull=True)
        .exclude(field__in=FIELD_TERSEMBUNYI)
        .annotate(**tanpa_dokumen)
        .order_by("created_at", "id")
        .values(
            "issue_id",
            "field",
            "verb",
            "lama",
            "baru",
            "old_identifier",
            "new_identifier",
            "created_at",
            "actor__display_name",
            "actor__email",
        )
    )


def _penulis(baris: dict, bahasa: str) -> str:
    return baris["actor__display_name"] or baris["actor__email"] or SISTEM[bahasa]


def susun_lembar(ids, user, slug, bahasa: str, zona: ZoneInfo) -> list[Lembar]:
    """Isi ketiga lembar untuk work item `ids`, yang sudah lolos saringan izin."""

    def terlihat(tugas):
        return saring_boleh_diekspor(tugas, user, slug)

    baris = _muat_baris(ids, user, slug)
    ids = [b.tugas.id for b in baris]
    keanggotaan = ProjectMember.objects.filter(workspace__slug=slug, member=user, is_active=True).values("project_id")
    komentar = _muat_komentar(ids, keanggotaan)
    aktivitas = _muat_aktivitas(ids, keanggotaan)

    sebutan = sebutan_massal(
        [b.tugas.description_html for b in baris] + [k["comment_html"] for k in komentar], terlihat
    )
    gambar, berkas = KATA_SISIPAN[bahasa]
    konteks = Konteks(
        bahasa=bahasa, zona=zona, teks=lambda html: teks_dokumen(html, sebutan, gambar=gambar, berkas=berkas)
    )

    rujukan = {
        ident
        for a in aktivitas
        if merujuk_tugas(a["field"])
        for ident in (a["old_identifier"], a["new_identifier"])
        if ident
    }
    rujukan_terlihat = set(terlihat(Issue.objects.filter(pk__in=rujukan)).values_list("pk", flat=True))
    nama_lampiran = {
        pk: (atribut or {}).get("name", "")
        for pk, atribut in FileAsset.all_objects.filter(
            issue_id__in=ids,
            pk__in={a["new_identifier"] for a in aktivitas if a["field"] == "attachment" and a["new_identifier"]},
        ).values_list("pk", "attributes")
    }

    # Komentar dan riwayat mengikuti urutan work item di lembar pertama, lalu waktunya.
    urutan = {ident: nomor for nomor, ident in enumerate(ids)}
    pengenal = {b.tugas.id: (_kode(b.tugas), b.tugas.name) for b in baris}

    def awal(catatan):
        return [
            *pengenal[catatan["issue_id"]],
            _penulis(catatan, bahasa),
            _waktu_lokal(catatan["created_at"], konteks),
        ]

    baris_komentar = [
        [*awal(k), konteks.teks(k["comment_html"])] for k in sorted(komentar, key=lambda k: urutan[k["issue_id"]])
    ]
    baris_aktivitas = []
    for a in sorted(aktivitas, key=lambda a: urutan[a["issue_id"]]):
        p = uraikan(a, bahasa, rujukan_terlihat, nama_lampiran)
        baris_aktivitas.append([*awal(a), p.apa, p.dari, p.menjadi])

    def judul(kolom):
        return [(k[0] if bahasa == "id" else k[1], k[2], k[3]) for k in kolom]

    return [
        Lembar(
            NAMA_LEMBAR[bahasa],
            judul([(k.judul_id, k.judul_en, k.lebar, k.bungkus) for k in KOLOM]),
            [[kolom.nilai(b, konteks) for kolom in KOLOM] for b in baris],
        ),
        Lembar(NAMA_LEMBAR_KOMENTAR[bahasa], judul(KOLOM_KOMENTAR), baris_komentar),
        Lembar(NAMA_LEMBAR_AKTIVITAS[bahasa], judul(KOLOM_AKTIVITAS), baris_aktivitas),
    ]


def _sel(lembar, nilai):
    """Satu sel. Teks selalu disimpan sebagai teks, tidak pernah sebagai rumus."""
    if isinstance(nilai, str):
        # openpyxl memotong teks di 32.767 karakter, batas satu sel Excel.
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


def susun_xlsx(daftar_lembar: list[Lembar]) -> bytes:
    buku = Workbook(write_only=True)
    for isi in daftar_lembar:
        lembar = buku.create_sheet(isi.nama)
        # Mode write-only: lebar, panel beku, dan filter harus diatur sebelum baris pertama.
        for nomor, (_, lebar, _) in enumerate(isi.kolom, start=1):
            lembar.column_dimensions[get_column_letter(nomor)].width = lebar
        lembar.freeze_panes = "A2"
        lembar.auto_filter.ref = f"A1:{get_column_letter(len(isi.kolom))}{len(isi.baris) + 1}"

        judul = []
        for teks, _, _ in isi.kolom:
            sel = _sel(lembar, teks)
            sel.font = Font(bold=True)
            judul.append(sel)
        lembar.append(judul)
        for baris in isi.baris:
            sel_baris = []
            for nilai, (_, _, bungkus) in zip(baris, isi.kolom):
                sel = _sel(lembar, nilai)
                # Rata atas: baris dengan teks panjang tetap terbaca dari judulnya.
                sel.alignment = _ATAS_BUNGKUS if bungkus else _ATAS
                sel_baris.append(sel)
            lembar.append(sel_baris)

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

    zona = ZoneInfo(request.user.user_timezone)
    isi = susun_xlsx(susun_lembar(ids, request.user, slug, bahasa_penerima(request.user), zona))
    berkas = nama_berkas(request.query_params.get("export_name"), timezone.now().astimezone(zona).date())
    respons = HttpResponse(isi, content_type=TIPE_XLSX)
    respons["Content-Disposition"] = f'attachment; filename="{berkas}"'
    respons["Cache-Control"] = "no-store"
    return respons
