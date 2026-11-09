# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: hak & sinkron Wiki mandiri (KEP-94)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu sumber aturan Wiki sesudah ia lepas dari project.

Matriks hak (KEP-51 dibawa utuh, sumbernya kini penempatan organisasi):

    baca                semua anggota aktif workspace
    unggah ke folder    admin Wiki, atau orang yang ditempatkan di unit folder itu
    ubah/hapus materi   pengunggahnya, pengelola folder, admin Wiki, atau aturan God Mode (KEP-85)
    struktur folder     admin Wiki; pengelola folder di dalam wilayahnya (KEP-95)

"Unit folder" = folder terdekat ke atas yang punya `departemen`, `divisi`, atau
`umum`. Folder tanpa unit di jalurnya (sisa lama) hanya bisa diisi admin.

Admin Wiki = Super Admin atau admin workspace (role 20). Direktur menjangkau
semua unit; manager menjangkau divisinya dan semua departemen di dalamnya.

Pengelola folder (KEP-95, 6 Nov 2026): manager divisi mengelola folder divisinya
dan semua yang ada di bawahnya (termasuk folder departemen), supervisor
mengelola folder departemen tempat ia berperan Supervisor (KEP-93: peran per
tempat). "Mengelola" = buat sub-folder, ubah, arsip, hapus, pulihkan dari
sampah, dan ubah/hapus materi siapa pun di wilayah itu. Nama folder unit tetap
mengikuti God Mode, folder tingkat atas tetap urusan admin.

Direktur (KEP-95, diperluas 6 Nov 2026) mengelola SEMUA folder divisi dan
departemen beserta isinya, dengan kuasa yang sama dengan manager divisi, di
mana saja. General dan folder tanpa unit tetap urusan admin.
"""

from django.db.models import Q

from plane.db.models.hierarki import TINGKAT_DIREKTUR, TINGKAT_SUPERVISOR

_MAX_DEPTH = 50
_ROLE_MEMBER = 15


def is_wiki_admin(user, workspace_id):
    from plane.utils.wiki_access import is_wiki_admin as _asli  # noqa: PLC0415

    return _asli(user, workspace_id=workspace_id)


def is_anggota_workspace(user, workspace_id, role_min=5):
    from plane.db.models import WorkspaceMember  # noqa: PLC0415

    if user is None or getattr(user, "is_anonymous", True):
        return False
    return WorkspaceMember.objects.filter(
        workspace_id=workspace_id, member=user, is_active=True, role__gte=role_min
    ).exists()


class PenilaiWiki:
    """Menilai hak satu orang di satu workspace. Dibuat sekali per permintaan:
    penempatan, peta induk folder, dan status admin dibaca sekali."""

    def __init__(self, user, workspace_id):
        from plane.db.models import Departemen, WikiFolder  # noqa: PLC0415
        from plane.db.penempatan import peran_departemen_sekarang, penempatan_sekarang  # noqa: PLC0415

        self.user = user
        self.workspace_id = workspace_id
        self.anonim = user is None or getattr(user, "is_anonymous", True)
        self.admin = (not self.anonim) and is_wiki_admin(user, workspace_id)
        self.anggota = (not self.anonim) and is_anggota_workspace(user, workspace_id, _ROLE_MEMBER)
        if self.anonim:
            self.tingkat, self.departemen, self.divisi = None, set(), set()
            peran = {}
        else:
            self.tingkat, self.departemen, self.divisi = penempatan_sekarang(workspace_id, user.id)
            peran = peran_departemen_sekarang(workspace_id, user.id)
        # Wilayah kelola (KEP-95). Baris divisi ditulis `setel_penempatan` hanya
        # untuk manager ke atas, tapi jenjangnya tetap diperiksa di sini supaya
        # baris lama sebelum KEP-76 tidak diam-diam memberi hak kelola.
        self.divisi_pimpin = set()
        if self.divisi:
            from plane.db.models import JabatanOrganisasi  # noqa: PLC0415
            from plane.db.models.hierarki import TINGKAT_MANAGER  # noqa: PLC0415

            self.divisi_pimpin = {
                str(v)
                for v in JabatanOrganisasi.objects.filter(
                    workspace_id=workspace_id,
                    member_id=user.id,
                    divisi_id__isnull=False,
                    tingkat__gte=TINGKAT_MANAGER,
                ).values_list("divisi_id", flat=True)
            }
        self.departemen_awasi = {d for d, t in peran.items() if t is not None and t >= TINGKAT_SUPERVISOR}
        # Departemen yang dijangkau lewat divisi yang ia pimpin.
        self.departemen_jangkau = set(self.departemen) | {
            str(d) for d in Departemen.objects.filter(divisi_id__in=list(self.divisi)).values_list("id", flat=True)
        }
        # Divisi yang ia sentuh: dipimpin, atau tempat salah satu departemennya.
        self.divisi_jangkau = set(self.divisi) | {
            str(v) for v in Departemen.objects.filter(id__in=list(self.departemen)).values_list("divisi_id", flat=True)
        }
        # `all_objects`: folder di tong sampah ikut, supaya pengelola bisa
        # menilai (dan memulihkan) isi sampah di wilayahnya. Folder hidup tidak
        # pernah punya induk terhapus (hapus menuntut folder kosong), jadi ini
        # tidak mengubah hasil penilaian folder hidup.
        self._folder = {
            str(f["id"]): f
            for f in WikiFolder.all_objects.filter(workspace_id=workspace_id).values(
                "id", "parent_id", "divisi_id", "departemen_id", "umum"
            )
        }

    @property
    def direktur(self):
        return self.tingkat is not None and self.tingkat >= TINGKAT_DIREKTUR

    @property
    def punya_wilayah(self):
        """Mengelola setidaknya satu folder di luar hak admin."""
        return self.direktur or bool(self.divisi_pimpin or self.departemen_awasi)

    def kenali(self, folder):
        """Masukkan folder yang baru dibuat di permintaan ini ke peta induk."""
        self._folder[str(folder.id)] = {
            "id": folder.id,
            "parent_id": folder.parent_id,
            "divisi_id": folder.divisi_id,
            "departemen_id": folder.departemen_id,
            "umum": folder.umum,
        }

    def _jalur(self, folder_id):
        """Folder ini lalu induk-induknya sampai akar (simpul dict)."""
        sekarang = self._folder.get(str(folder_id)) if folder_id else None
        langkah = 0
        while sekarang is not None and langkah < _MAX_DEPTH:
            yield sekarang
            induk = sekarang["parent_id"]
            sekarang = self._folder.get(str(induk)) if induk else None
            langkah += 1

    def di_bawah(self, folder_id, akar_id):
        """Folder ini sama dengan `akar_id` atau ada di bawahnya (folder di sampah ikut)."""
        akar = str(akar_id)
        return any(str(simpul["id"]) == akar for simpul in self._jalur(folder_id))

    def mengelola(self, folder_id):
        """Folder ini ada di wilayah kelolanya: di bawah (atau sama dengan) folder
        divisi yang ia pimpin, folder departemen tempat ia Supervisor, atau
        (direktur) folder divisi/departemen mana pun."""
        if self.anonim or not folder_id:
            return False
        if self.admin:
            return True
        if not self.punya_wilayah:
            return False
        for simpul in self._jalur(folder_id):
            if self.direktur and (simpul["divisi_id"] or simpul["departemen_id"]):
                return True
            if simpul["divisi_id"] and str(simpul["divisi_id"]) in self.divisi_pimpin:
                return True
            if simpul["departemen_id"] and str(simpul["departemen_id"]) in self.departemen_awasi:
                return True
        return False

    def boleh_lihat_halaman_privat(self, departemen_id, divisi_id):
        """Halaman privat project departemen (KEP-95): anggota departemen itu
        (peran apa pun), manager divisinya, direktur, dan admin (Super Admin)."""
        if self.anonim:
            return False
        if self.admin or self.direktur:
            return True
        if departemen_id and str(departemen_id) in self.departemen:
            return True
        return bool(divisi_id) and str(divisi_id) in self.divisi_pimpin

    def unit(self, folder_id):
        """Simpul pertama ke atas yang menentukan hak unggah, atau None."""
        sekarang = self._folder.get(str(folder_id))
        langkah = 0
        while sekarang is not None and langkah < _MAX_DEPTH:
            if sekarang["departemen_id"] or sekarang["divisi_id"] or sekarang["umum"]:
                return sekarang
            induk = sekarang["parent_id"]
            sekarang = self._folder.get(str(induk)) if induk else None
            langkah += 1
        return None

    def boleh_unggah(self, folder_id):
        if self.anonim:
            return False
        if self.admin or self.mengelola(folder_id):
            return True
        unit = self.unit(folder_id)
        if unit is None:
            return False
        if unit["umum"]:
            return self.anggota
        if self.direktur:
            return True
        if unit["departemen_id"]:
            return str(unit["departemen_id"]) in self.departemen_jangkau
        return str(unit["divisi_id"]) in self.divisi_jangkau

    def boleh_kelola_folder(self, folder_id=None):
        """Tanpa `folder_id` = struktur tingkat atas, hanya admin."""
        if folder_id is None:
            return self.admin
        return self.mengelola(folder_id)

    def boleh_kelola_materi(self, materi, kunci=None):
        """`materi` = WikiMaterial. `kunci` = PERM_WIKI_EDIT (bawaan) / PERM_WIKI_DELETE."""
        from plane.utils.izin_sumber import PenilaiIzin  # noqa: PLC0415
        from plane.utils.saklar_instance import PERM_WIKI_EDIT  # noqa: PLC0415

        if self.anonim:
            return False
        if materi.created_by_id and materi.created_by_id == self.user.id:
            return True
        if self.admin or self.mengelola(materi.folder_id):
            return True
        if not hasattr(self, "_izin"):
            self._izin = PenilaiIzin(self.user, self.workspace_id)
        # Tanpa project: "setiap anggota" berarti setiap anggota workspace.
        return self._izin.boleh(kunci or PERM_WIKI_EDIT, project_id=None, pemilik_id=materi.created_by_id)


def pengawas_halaman_privat(user, project_id):
    """Boleh membuka halaman PRIVAT orang lain di project ini (KEP-95, 6 Nov 2026).

    Sengaja lebih sempit dari `PenilaiWiki.boleh_lihat_halaman_privat`: anggota
    departemen biasa TIDAK ikut, karena di dalam project halaman privat tetap
    milik pemiliknya. Yang lolos hanya admin Wiki (Super Admin / admin
    workspace), direktur, dan manager divisi tempat departemen project ini.
    Project di luar departemen mana pun: hanya admin Wiki dan direktur.
    """
    from plane.db.models import DepartemenProject, JabatanOrganisasi, Project  # noqa: PLC0415
    from plane.db.models.hierarki import TINGKAT_MANAGER  # noqa: PLC0415
    from plane.db.penempatan import penempatan_sekarang  # noqa: PLC0415

    if user is None or getattr(user, "is_anonymous", True) or not project_id:
        return False
    workspace_id = Project.objects.filter(pk=project_id).values_list("workspace_id", flat=True).first()
    if workspace_id is None:
        return False
    if is_wiki_admin(user, workspace_id):
        return True
    tingkat, _, _ = penempatan_sekarang(workspace_id, user.id)
    if tingkat is not None and tingkat >= TINGKAT_DIREKTUR:
        return True
    divisi_id = (
        DepartemenProject.objects.filter(project_id=project_id, departemen__deleted_at__isnull=True)
        .values_list("departemen__divisi_id", flat=True)
        .first()
    )
    if not divisi_id:
        return False
    return JabatanOrganisasi.objects.filter(
        workspace_id=workspace_id, member_id=user.id, divisi_id=divisi_id, tingkat__gte=TINGKAT_MANAGER
    ).exists()


def pastikan_folder_unit(workspace_id):
    """Tiap Divisi dan Departemen aktif punya foldernya, bernama sama, dan folder
    departemen berada di bawah folder divisinya. Dipanggil setiap struktur
    organisasi berubah. Folder unit yang unitnya dihapus TIDAK dihapus: isinya
    tetap ada, foldernya kehilangan unit dan hanya bisa diisi admin.

    Idempoten dan murah: tiga baca, tulis hanya untuk yang berbeda. Karena itu
    ia juga dipanggil setiap pohon Wiki dibaca (KEP-95), supaya folder yang
    tertinggal karena sinkron God Mode gagal (galatnya cuma dicatat) atau unit
    yang dibuat lewat jalur lain menyusul sendiri. Mengembalikan jumlah folder
    yang dibuat atau diubah."""
    from django.db import transaction  # noqa: PLC0415

    from plane.db.models import Departemen, Divisi, WikiFolder  # noqa: PLC0415

    divisi = list(Divisi.objects.filter(workspace_id=workspace_id).values_list("id", "nama"))
    departemen = list(Departemen.objects.filter(workspace_id=workspace_id).values_list("id", "nama", "divisi_id"))
    if not divisi and not departemen:
        return 0
    ada_div, ada_dep = {}, {}
    for fid, div_id, dep_id, nama, parent_id in (
        WikiFolder.objects.filter(workspace_id=workspace_id)
        .filter(Q(divisi__isnull=False) | Q(departemen__isnull=False))
        .values_list("id", "divisi_id", "departemen_id", "nama", "parent_id")
    ):
        if div_id:
            ada_div.setdefault(div_id, (fid, nama, parent_id))
        else:
            ada_dep.setdefault(dep_id, (fid, nama, parent_id))

    berubah = 0
    with transaction.atomic():
        folder_divisi = {}
        for div_id, nama in divisi:
            lama = ada_div.get(div_id)
            if lama is None:
                folder_divisi[div_id] = WikiFolder.objects.create(
                    workspace_id=workspace_id, nama=nama, divisi_id=div_id
                ).id
                berubah += 1
                continue
            fid, nama_lama, parent_id = lama
            if nama_lama != nama or parent_id is not None:
                WikiFolder.objects.filter(pk=fid).update(nama=nama, parent=None)
                berubah += 1
            folder_divisi[div_id] = fid

        for dep_id, nama, div_id in departemen:
            induk_id = folder_divisi.get(div_id)
            lama = ada_dep.get(dep_id)
            if lama is None:
                WikiFolder.objects.create(
                    workspace_id=workspace_id, nama=nama, departemen_id=dep_id, parent_id=induk_id
                )
                berubah += 1
            elif lama[1] != nama or lama[2] != induk_id:
                WikiFolder.objects.filter(pk=lama[0]).update(nama=nama, parent_id=induk_id)
                berubah += 1
    return berubah
