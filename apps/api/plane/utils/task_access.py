# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan kepemilikan tugas
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Siapa boleh membuang dan siapa boleh menggeser tenggat sebuah tugas.

Aturan ini berlaku di SELURUH project, yang sekarang maupun yang dibuat nanti,
dan datang dari pemilik instance:

    hapus tugas        pembuatnya, Super Admin, atau admin project
                       (gerbang hierarki aktif: sama dengan hak UBAH, yaitu
                       pembuat/assignee atau atasannya, plus Super Admin)
    arsipkan tugas     sama dengan hapus
    ganti Due Date     HANYA pembuatnya atau Super Admin
    ubah apa pun       gerbang hierarki aktif: pembuat/assignee, atasan dari
                       assignee-nya, atau Super Admin (KEP-25). Berlaku juga
                       di sub-sumber lewat `KepemilikanTugasMixin` di bawah.
    komentar           bebas untuk semua anggota

Dua baris pertama dan baris ketiga sengaja BERBEDA, dan itu bukan
ketidakkonsistenan. Menghapus tugas adalah urusan beres-beres papan, jadi kepala
divisi ikut dipercaya. Menggeser tenggat adalah mengubah janji kepada orang
lain, dan itu hanya boleh dilakukan yang membuat janjinya.

Kenapa satu berkas sendiri: aturan ini harus dijawab sama persis di lapisan API
aplikasi, di API token, dan nanti di tampilan. Satu aturan yang disalin ke tiga
tempat cepat atau lambat jadi tiga aturan.
"""

from plane.db.superadmin import is_super_admin

_ROLE_ADMIN = 20


def _admin_project(user, slug, project_id):
    from plane.db.models import ProjectMember

    return ProjectMember.objects.filter(
        member=user,
        workspace__slug=slug,
        project_id=project_id,
        role=_ROLE_ADMIN,
        is_active=True,
    ).exists()


def bisa_hapus_tugas(user, issue, slug, project_id):
    """Boleh menghapus atau mengarsipkan tugas ini.

    Arsip disamakan dengan hapus dengan sengaja: mengarsipkan tugas
    menyembunyikannya dari SEMUA papan, jadi kalau hapus dikunci sementara arsip
    dibiarkan bebas, orang yang di-assign tetap bisa membuat tugas orang lain
    lenyap dari pandangan, hanya lewat pintu yang namanya berbeda.
    """
    if user is None or getattr(user, "is_anonymous", True):
        return False
    if is_super_admin(user):
        return True

    # Gerbang hierarki aktif: hapus/arsip ikut aturan UBAH (`galat_ubah_tugas`),
    # yaitu pembuat/assignee tugas itu sendiri, atau atasannya. Admin project
    # TIDAK lagi cukup: di kantor ini hampir semua staf berperan admin project,
    # jadi jalur itu membuat staf bisa menghapus tugas orang lain.
    from plane.utils.hierarki import galat_ubah_tugas, gerbang_aktif  # noqa: PLC0415

    if gerbang_aktif():
        return galat_ubah_tugas(project_id, issue, actor=user) is None

    if issue.created_by_id == user.id:
        return True
    return _admin_project(user, slug, project_id)


def bisa_ganti_tenggat(user, issue):
    """Boleh menggeser Due Date tugas ini.

    Sengaja LEBIH KETAT daripada hak hapus: admin project tidak termasuk.
    Tenggat adalah janji yang dibuat seseorang, dan menggesernya diam-diam dari
    atas adalah persis hal yang ingin dicegah pemilik instance.
    """
    if user is None or getattr(user, "is_anonymous", True):
        return False
    return issue.created_by_id == user.id or is_super_admin(user)


def bisa_ganti_tenggat_intake(user, issue, penanggung_jawab=False):
    """Boleh mengatur Due Date selama tugasnya MASIH di antrean intake.

    Keputusan user 2026-10-29: triage adalah tempat tenggat dijanjikan pertama
    kali, jadi penanggung jawab intake (admin project / admin workspace) ikut
    boleh mengaturnya — bukan hanya pembuat. Tanpa ini, tugas yang datang dari
    orang lain (atau dari divisi lain, yang tersimpan dengan `created_by` NULL)
    tidak akan pernah bisa diberi tenggat oleh siapa pun.

    Pengecualian ini HANYA berlaku di pintu intake. Begitu tugas diterima ke
    papan, berlaku kembali aturan biasa: hanya pembuatnya atau Super Admin.
    """
    if user is None or getattr(user, "is_anonymous", True):
        return False
    if penanggung_jawab:
        return True
    return bisa_ganti_tenggat(user, issue)


def _tanggal(nilai):
    """Normalkan tanggal ke bentuk `YYYY-MM-DD` supaya bisa dibandingkan.

    Klien mengirim tanggal sebagai teks, kadang berikut jamnya, sementara di
    database ia `DateField`. Tanpa penormalan, "2026-08-25" dan
    "2026-08-25T00:00:00Z" akan terlihat berbeda dan setiap penyimpanan biasa
    dituduh mengubah tenggat.
    """
    if nilai in (None, ""):
        return None
    teks = str(nilai)
    return teks[:10]


def tenggat_diubah(issue, data):
    """True hanya kalau permintaan ini benar-benar MENGUBAH Due Date.

    Ini bukan kerapian, ini penentu benar atau salahnya seluruh aturan. Beberapa
    layar mengirim ulang seluruh isi formulir saat menyimpan, termasuk tenggat
    yang tidak disentuh. Menolak berdasarkan "ada target_date di payload" akan
    membuat orang yang di-assign tidak bisa menyimpan apa pun, padahal yang ia
    ubah cuma prioritas.
    """
    if "target_date" not in data:
        return False
    return _tanggal(data.get("target_date")) != _tanggal(issue.target_date)


# --------------------------------------------------------------------------
# Kepemilikan edit di SUB-SUMBER tugas (KEP-25, dikuatkan 2026-11-02)
# --------------------------------------------------------------------------
#
# PATCH tugasnya sendiri sudah dijaga `galat_ubah_tugas` di view + serializer.
# Tapi tugas punya belasan pintu tulis lain: tautan, lampiran, relasi,
# sub-issue, cycle, module, worklog, versi deskripsi, property value, dan
# seret tanggal di Gantt/kalender (`issue-dates`). Tanpa penjaga di sana, orang
# yang tidak terlibat tetap bisa "mengedit" tugas orang lain lewat pintu samping
# -- persis keluhan user 2 Nov: "masih bisa edit punya orang lain di detail".
#
# Satu penjaga di base view (`initial()`), bukan per endpoint: penjaga per
# endpoint pasti ada yang terlewat. Bentuknya mewarisi `KunciPersetujuanMixin`
# (a5ff1b36b4) yang dulu mengunci semua jalur yang sama.

_METODE_TULIS = ("POST", "PUT", "PATCH", "DELETE")

# Segmen URL yang TETAP terbuka untuk semua anggota:
# - percakapan (komentar, reaksi, langganan): melihat boleh, bertanya juga boleh;
# - antrean persetujuan: atasan memutuskan lewat jalurnya sendiri;
# - intake: triage punya aturannya sendiri (KEP-36, serializer intake);
# - hapus/arsip massal: sudah MENYARING per baris lalu mengaku berapa yang
#   dilewati. Menolak seluruh permintaan di sini akan mengganti pengakuan itu
#   dengan 403 buta.
_JALUR_BEBAS = (
    "/comments/",
    "/reactions/",
    "/issue-subscribers/",
    "/subscribe/",
    "persetujuan-penugasan",
    "intake-issues",
    "inbox-issues",
    "bulk-delete-issues",
    "bulk-archive-issues",
)
# Kunci body yang membawa id tugas lain yang ikut disentuh.
_KUNCI_ISI = ("issues", "issue_ids", "sub_issue_ids")


def _uuid_saja(nilai):
    import uuid  # noqa: PLC0415

    hasil = []
    for v in nilai if isinstance(nilai, (list, tuple)) else [nilai]:
        if isinstance(v, dict):
            v = v.get("id") or v.get("issue")
        try:
            hasil.append(uuid.UUID(str(v)))
        except (TypeError, ValueError, AttributeError):
            continue
    return hasil


def tugas_disentuh_request(request, kwargs):
    """Id tugas yang disentuh request tulis: `issue_id` di URL + isi body.

    `pk` sengaja TIDAK dibaca: di rute tugas ia tugasnya sendiri (PATCH dijaga
    view + serializer, arsip/hapus dijaga `bisa_hapus_tugas`), dan di rute lain
    ia id komentar/tautan/label yang bukan tugas.
    """
    ids = _uuid_saja(kwargs.get("issue_id"))
    data = getattr(request, "data", None)
    if hasattr(data, "get"):
        for kunci in _KUNCI_ISI:
            if kunci in data:
                ids += _uuid_saja(data.get(kunci))
        if isinstance(data.get("updates"), list):  # issue-dates (seret Gantt/kalender)
            ids += _uuid_saja(data.get("updates"))
    return list(dict.fromkeys(ids))


def galat_ubah_tugas_ids(issue_ids, actor):
    """Pesan galat pertama kalau actor tak boleh mengubah salah satu tugas, atau None."""
    from plane.utils.hierarki import galat_ubah_tugas, gerbang_aktif  # noqa: PLC0415

    if not issue_ids or not gerbang_aktif():
        return None
    if actor is None:
        return "Pelaku perubahan tidak diketahui, jadi perubahan ini tidak dapat diverifikasi."
    if is_super_admin(actor):
        return None

    from plane.db.models import Issue  # noqa: PLC0415

    # Tugas yang tidak ada dibiarkan: endpoint-nya sendiri yang menjawab 404.
    for issue in Issue.objects.filter(id__in=issue_ids):
        galat = galat_ubah_tugas(issue.project_id, issue, actor=actor)
        if galat:
            return galat
    return None


class KepemilikanTugasMixin:
    """Tolak tulis ke sub-sumber tugas yang bukan milik pelaku (atau bawahannya)."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method not in _METODE_TULIS:
            return
        if any(seg in request.path for seg in _JALUR_BEBAS):
            return
        ids = tugas_disentuh_request(request, kwargs)
        if not ids:
            return
        actor = request.user if getattr(request.user, "is_authenticated", False) else None
        galat = galat_ubah_tugas_ids(ids, actor)
        if galat:
            from rest_framework.exceptions import PermissionDenied  # noqa: PLC0415

            # Kunci `error`, sama dengan galat 403 lain di app ini (toast klien membacanya).
            raise PermissionDenied({"error": galat})
