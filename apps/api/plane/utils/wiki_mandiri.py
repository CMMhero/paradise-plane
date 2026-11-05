# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: hak & sinkron Wiki mandiri (KEP-94)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu sumber aturan Wiki sesudah ia lepas dari project.

Matriks hak (KEP-51 dibawa utuh, sumbernya kini penempatan organisasi):

    baca                semua anggota aktif workspace
    unggah ke folder    admin Wiki, atau orang yang ditempatkan di unit folder itu
    ubah/hapus materi   pengunggahnya, admin Wiki, atau aturan God Mode (KEP-85)
    struktur folder     admin Wiki saja

"Unit folder" = folder terdekat ke atas yang punya `departemen`, `divisi`, atau
`umum`. Folder tanpa unit di jalurnya (sisa lama) hanya bisa diisi admin.

Admin Wiki = Super Admin atau admin workspace (role 20). Direktur menjangkau
semua unit; manager menjangkau divisinya dan semua departemen di dalamnya.
"""

from plane.db.models.hierarki import TINGKAT_DIREKTUR

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
        from plane.db.penempatan import penempatan_sekarang  # noqa: PLC0415

        self.user = user
        self.workspace_id = workspace_id
        self.anonim = user is None or getattr(user, "is_anonymous", True)
        self.admin = (not self.anonim) and is_wiki_admin(user, workspace_id)
        self.anggota = (not self.anonim) and is_anggota_workspace(user, workspace_id, _ROLE_MEMBER)
        if self.anonim:
            self.tingkat, self.departemen, self.divisi = None, set(), set()
        else:
            self.tingkat, self.departemen, self.divisi = penempatan_sekarang(workspace_id, user.id)
        # Departemen yang dijangkau lewat divisi yang ia pimpin.
        self.departemen_jangkau = set(self.departemen) | {
            str(d) for d in Departemen.objects.filter(divisi_id__in=list(self.divisi)).values_list("id", flat=True)
        }
        # Divisi yang ia sentuh: dipimpin, atau tempat salah satu departemennya.
        self.divisi_jangkau = set(self.divisi) | {
            str(v) for v in Departemen.objects.filter(id__in=list(self.departemen)).values_list("divisi_id", flat=True)
        }
        self._folder = {
            str(f["id"]): f
            for f in WikiFolder.objects.filter(workspace_id=workspace_id).values(
                "id", "parent_id", "divisi_id", "departemen_id", "umum"
            )
        }

    @property
    def direktur(self):
        return self.tingkat is not None and self.tingkat >= TINGKAT_DIREKTUR

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
        if self.admin:
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
        return self.admin

    def boleh_kelola_materi(self, materi, kunci=None):
        """`materi` = WikiMaterial. `kunci` = PERM_WIKI_EDIT (bawaan) / PERM_WIKI_DELETE."""
        from plane.utils.izin_sumber import PenilaiIzin  # noqa: PLC0415
        from plane.utils.saklar_instance import PERM_WIKI_EDIT  # noqa: PLC0415

        if self.anonim:
            return False
        if materi.created_by_id and materi.created_by_id == self.user.id:
            return True
        if self.admin:
            return True
        if not hasattr(self, "_izin"):
            self._izin = PenilaiIzin(self.user, self.workspace_id)
        # Tanpa project: "setiap anggota" berarti setiap anggota workspace.
        return self._izin.boleh(kunci or PERM_WIKI_EDIT, project_id=None, pemilik_id=materi.created_by_id)


def pastikan_folder_unit(workspace_id):
    """Tiap Divisi dan Departemen aktif punya foldernya, bernama sama, dan folder
    departemen berada di bawah folder divisinya. Dipanggil setiap struktur
    organisasi berubah. Folder unit yang unitnya dihapus TIDAK dihapus: isinya
    tetap ada, foldernya kehilangan unit dan hanya bisa diisi admin."""
    from django.db import transaction  # noqa: PLC0415

    from plane.db.models import Departemen, Divisi, WikiFolder  # noqa: PLC0415

    with transaction.atomic():
        folder_divisi = {}
        for divisi in Divisi.objects.filter(workspace_id=workspace_id):
            f = WikiFolder.objects.filter(divisi=divisi).first()
            if f is None:
                f = WikiFolder.objects.create(workspace_id=workspace_id, nama=divisi.nama, divisi=divisi)
            elif f.nama != divisi.nama or f.parent_id is not None:
                WikiFolder.objects.filter(pk=f.pk).update(nama=divisi.nama, parent=None)
            folder_divisi[divisi.id] = f

        for dep in Departemen.objects.filter(workspace_id=workspace_id):
            induk = folder_divisi.get(dep.divisi_id)
            induk_id = induk.id if induk else None
            f = WikiFolder.objects.filter(departemen=dep).first()
            if f is None:
                WikiFolder.objects.create(workspace_id=workspace_id, nama=dep.nama, departemen=dep, parent_id=induk_id)
            elif f.nama != dep.nama or f.parent_id != induk_id:
                WikiFolder.objects.filter(pk=f.pk).update(nama=dep.nama, parent_id=induk_id)
