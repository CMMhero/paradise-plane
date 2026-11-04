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
from plane.utils.saklar_instance import (
    DUE_DATE_CHANGE_RULE,
    HAPUS_PEMBUAT_SAJA,
    HAPUS_YANG_BOLEH_UBAH,
    TASK_DELETE_RULE,
    TENGGAT_PLUS_ADMIN_PROJECT,
    TENGGAT_YANG_BOLEH_UBAH,
    setelan_angka,
)

_ROLE_ADMIN = 20

# KEP-83: dua baris pertama tabel di atas sekarang bisa diatur Super Admin di
# God Mode (TASK_DELETE_RULE, DUE_DATE_CHANGE_RULE). Bawaan keduanya (0) adalah
# persis tabel di atas; arti tiap pilihan ada di plane/utils/saklar_instance.py.


class AturanTugas:
    """Aturan kepemilikan yang dibaca SEKALI untuk satu permintaan.

    Endpoint massal (hapus/arsip/geser tanggal banyak tugas) memanggil
    `bisa_hapus_tugas` / `bisa_ganti_tenggat` per tugas. Tanpa ini tiap panggilan
    membaca ulang TASK_DELETE_RULE, DUE_DATE_CHANGE_RULE, gerbang hierarki, status
    Super Admin, dan peran admin project dari database. Di sini semuanya dibaca
    sekali (lazily) lalu dipakai untuk semua tugas. Aturannya tidak berubah:
    tanpa `aturan`, setiap fungsi membuat satu yang baru, persis perilaku lama.
    """

    def __init__(self, user):
        self.user = user
        self._nilai = {}
        self._admin_ids = None

    def _sekali(self, kunci, baca):
        if kunci not in self._nilai:
            self._nilai[kunci] = baca()
        return self._nilai[kunci]

    @property
    def super_admin(self):
        return self._sekali("super_admin", lambda: is_super_admin(self.user))

    @property
    def hapus(self):
        return self._sekali("hapus", lambda: setelan_angka(TASK_DELETE_RULE))

    @property
    def tenggat(self):
        return self._sekali("tenggat", lambda: setelan_angka(DUE_DATE_CHANGE_RULE))

    @property
    def gerbang(self):
        from plane.utils.hierarki import gerbang_aktif  # noqa: PLC0415

        return self._sekali("gerbang", gerbang_aktif)

    def admin_project(self, project_id, slug=None):
        """Apakah user admin aktif di project ini. Satu kueri untuk semua project.

        `slug` diisi = project itu juga harus milik workspace tersebut, sama dengan
        saringan `workspace__slug` pemeriksaan admin project sebelum KEP-83.
        """
        if self._admin_ids is None:
            from plane.db.models import ProjectMember  # noqa: PLC0415

            self._admin_ids = {
                str(pid): ws
                for pid, ws in ProjectMember.objects.filter(
                    member=self.user, role=_ROLE_ADMIN, is_active=True
                ).values_list("project_id", "workspace__slug")
            }
        ws = self._admin_ids.get(str(project_id))
        return ws is not None and (slug is None or ws == slug)


def _aturan(user, aturan):
    return aturan if aturan is not None and aturan.user == user else AturanTugas(user)


def _boleh_ubah(user, issue, project_id, aturan=None):
    """Hak UBAH tugas: gerbang hierarki menyala = `galat_ubah_tugas`; mati = setiap anggota.

    Gerbang mati berarti tidak ada kunci edit per tugas: izin project di view
    (anggota, bukan tamu) yang sudah menjaga pintunya.
    """
    from plane.utils.hierarki import galat_ubah_tugas  # noqa: PLC0415

    if not _aturan(user, aturan).gerbang:
        return True
    return galat_ubah_tugas(project_id, issue, actor=user) is None


def bisa_hapus_tugas(user, issue, slug, project_id, aturan=None):
    """Boleh menghapus atau mengarsipkan tugas ini.

    Arsip disamakan dengan hapus dengan sengaja: mengarsipkan tugas
    menyembunyikannya dari SEMUA papan, jadi kalau hapus dikunci sementara arsip
    dibiarkan bebas, orang yang di-assign tetap bisa membuat tugas orang lain
    lenyap dari pandangan, hanya lewat pintu yang namanya berbeda.

    `aturan`: `AturanTugas` milik permintaan ini (endpoint massal), supaya setelan,
    gerbang, dan peran dibaca sekali. Kosong = dibaca sekarang.
    """
    if user is None or getattr(user, "is_anonymous", True):
        return False
    aturan = _aturan(user, aturan)
    if aturan.super_admin:
        return True

    if aturan.hapus == HAPUS_PEMBUAT_SAJA:
        return issue.created_by_id == user.id
    if aturan.hapus == HAPUS_YANG_BOLEH_UBAH:
        return _boleh_ubah(user, issue, project_id, aturan)

    # HAPUS_ATURAN_HARI_INI (bawaan). Gerbang hierarki aktif: hapus/arsip ikut aturan UBAH (`galat_ubah_tugas`),
    # yaitu pembuat/assignee tugas itu sendiri, atau atasannya. Admin project
    # TIDAK lagi cukup: di kantor ini hampir semua staf berperan admin project,
    # jadi jalur itu membuat staf bisa menghapus tugas orang lain.
    from plane.utils.hierarki import galat_ubah_tugas  # noqa: PLC0415

    if aturan.gerbang:
        return galat_ubah_tugas(project_id, issue, actor=user) is None

    if issue.created_by_id == user.id:
        return True
    return aturan.admin_project(project_id, slug)


def bisa_ganti_tenggat(user, issue, aturan=None):
    """Boleh menggeser Due Date tugas ini.

    Sengaja LEBIH KETAT daripada hak hapus: admin project tidak termasuk.
    Tenggat adalah janji yang dibuat seseorang, dan menggesernya diam-diam dari
    atas adalah persis hal yang ingin dicegah pemilik instance.
    """
    if user is None or getattr(user, "is_anonymous", True):
        return False
    if issue.created_by_id == user.id:
        return True
    aturan = _aturan(user, aturan)
    if aturan.super_admin:
        return True
    # KEP-83: bawaan (TENGGAT_PEMBUAT_SAJA) berhenti di atas, persis aturan lama.
    if aturan.tenggat == TENGGAT_PLUS_ADMIN_PROJECT:
        return aturan.admin_project(issue.project_id)
    if aturan.tenggat == TENGGAT_YANG_BOLEH_UBAH:
        return _boleh_ubah(user, issue, issue.project_id, aturan)
    return False


def pesan_tolak_tenggat(aturan=None):
    """Pesan 403 untuk tenggat yang tidak boleh digeser, sesuai aturan yang berlaku."""
    aturan = aturan.tenggat if aturan is not None else setelan_angka(DUE_DATE_CHANGE_RULE)
    if aturan == TENGGAT_PLUS_ADMIN_PROJECT:
        return (
            "Tenggat hanya bisa diubah oleh yang membuat tugas ini, admin project, "
            "atau Super Admin. Hubungi pembuatnya kalau tanggalnya perlu digeser."
        )
    if aturan == TENGGAT_YANG_BOLEH_UBAH:
        return "Anda tidak dapat mengubah tugas ini, jadi tenggatnya juga tidak dapat digeser."
    return (
        "Tenggat hanya bisa diubah oleh yang membuat tugas ini, "
        "atau Super Admin. Hubungi pembuatnya kalau tanggalnya perlu digeser."
    )


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
