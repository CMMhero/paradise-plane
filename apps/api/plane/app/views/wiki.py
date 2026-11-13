# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: API folder Wiki mandiri (KEP-94)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Pohon folder Wiki, arsip, dan tong sampah folder.

Semua jalur di `/api/workspaces/<slug>/wiki/`. Hak dihitung `PenilaiWiki`
(`plane.utils.wiki_mandiri`) dan dikirim sebagai boolean; klien tidak
menurunkan aturan sendiri. Folder unit (divisi/departemen) hanya dibuat dan
dinamai `pastikan_folder_unit`, jadi di sini ia tidak bisa diganti nama,
diarsipkan, atau dihapus.

Struktur tingkat atas (folder tanpa induk, folder General, urutan folder
teratas) tetap urusan admin. Di dalam wilayahnya, manager divisi dan supervisor
departemen mengelola sendiri (KEP-95).
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from plane.app.views.wiki_dasar import Galat, WikiAPIView, anotasi_jumlah
from plane.app.views.wiki_halaman import jumlah_halaman_per_departemen, project_per_departemen
from plane.db.models import Project, WikiFolder, WikiMaterial
from plane.utils.exception_logger import log_exception
from plane.utils.wiki_mandiri import pastikan_folder_unit

_PESAN_ADMIN = "Only a workspace admin can manage the top level of the Wiki."
_PESAN_KELOLA = "You can only manage folders in your own division or department."
_PESAN_UNIT = "This folder follows its division or department name. Rename it in God Mode."
_MAKS_NAMA = 255


def _wajib_admin(penilai):
    if not penilai.boleh_kelola_folder():
        raise Galat(_PESAN_ADMIN, status.HTTP_403_FORBIDDEN)


def _wajib_kelola(penilai, folder_id):
    if not penilai.boleh_kelola_folder(folder_id):
        raise Galat(_PESAN_KELOLA, status.HTTP_403_FORBIDDEN)


def _nama_bersih(nilai):
    nama = str(nilai or "").strip()
    if not nama or len(nama) > _MAKS_NAMA:
        raise Galat("The folder name must be 1 to 255 characters.")
    return nama


def _logo_bersih(nilai):
    if not isinstance(nilai, dict):
        raise Galat("logo_props must be an object.")
    return nilai


def _keturunan(workspace_id, folder_id):
    """Semua folder hidup di bawah `folder_id` (tanpa dirinya), per tingkat."""
    hasil, frontier, terlihat = [], [folder_id], {folder_id}
    while frontier:
        anak = list(WikiFolder.objects.filter(workspace_id=workspace_id, parent_id__in=frontier))
        frontier = [a.id for a in anak if a.id not in terlihat]
        terlihat.update(frontier)
        hasil.extend(a for a in anak if a.id in frontier)
    return hasil


class WikiAkarEndpoint(WikiAPIView):
    def get(self, request, slug):
        # Penyembuh sendiri: folder unit yang tertinggal menyusul di sini.
        # Gagal sinkron tidak boleh membuat Wiki tidak bisa dibuka.
        try:
            if pastikan_folder_unit(self.workspace.id):
                self.penilai = type(self.penilai)(request.user, self.workspace.id)
        except Exception as exc:  # noqa: BLE001
            log_exception(exc)
        folder = anotasi_jumlah(WikiFolder.objects.filter(workspace_id=self.workspace.id))
        # Dua query untuk seluruh pohon (KEP-97): peta departemen ke project, lalu
        # satu agregat halaman yang boleh dilihat. Angkanya langsung per folder
        # departemen; klien menjumlahkannya ke atas sama seperti angka materi.
        peta = project_per_departemen(self.workspace.id)
        halaman = jumlah_halaman_per_departemen(self.penilai, peta)

        # Ikon departemen = ikon project-nya, selama folder belum punya ikon sendiri.
        # Satu query untuk semua project; ikon yang dipilih tangan di folder menang.
        logo_project = {
            pid: logo
            for pid, logo in Project.objects.filter(id__in=[p for p, _ in peta.values()]).values_list(
                "id", "logo_props"
            )
            if isinstance(logo, dict) and logo.get("in_use")
        }

        def _json(f):
            dep = str(f.departemen_id) if f.departemen_id else None
            proj_id = peta[dep][0] if dep in peta else None
            data = self.folder_json(
                f,
                f._jumlah,
                jumlah_halaman=halaman.get(dep, 0) if dep else 0,
                project_id=proj_id,
            )
            if not (data["logo_props"] or {}).get("in_use") and proj_id in logo_project:
                data["logo_props"] = logo_project[proj_id]
            return data

        return Response(
            {
                "is_admin": self.penilai.admin,
                "can_manage_any": self.penilai.admin or self.penilai.punya_wilayah,
                "user_id": str(request.user.id),
                "folders": [_json(f) for f in folder],
            },
            status=status.HTTP_200_OK,
        )


class WikiFolderListEndpoint(WikiAPIView):
    def post(self, request, slug):
        nama = _nama_bersih(request.data.get("nama"))
        parent_id = request.data.get("parent_id") or None
        umum = bool(request.data.get("umum", False))
        if not parent_id:
            _wajib_admin(self.penilai)
        else:
            if umum:
                raise Galat("Only a top-level folder can be the General folder.")
            induk = self.folder_atau_404(parent_id)
            _wajib_kelola(self.penilai, induk.id)
            if induk.archived_at is not None:
                raise Galat("The parent folder is archived.")
            # Sub-topik hanya satu tingkat: induknya divisi, departemen, atau folder
            # tingkat atas. Sub-topik di dalam sub-topik tidak diizinkan.
            if induk.parent_id is not None and not induk.unit:
                raise Galat("A sub-topic cannot contain another sub-topic.")
        logo = request.data.get("logo_props")
        folder = WikiFolder(
            workspace_id=self.workspace.id,
            parent_id=parent_id,
            nama=nama,
            keterangan=str(request.data.get("keterangan") or ""),
            umum=umum,
        )
        if logo is not None:
            folder.logo_props = _logo_bersih(logo)
        folder.save(created_by_id=request.user.id)
        self.penilai.kenali(folder)
        return Response(self.folder_json(folder), status=status.HTTP_201_CREATED)


class WikiFolderEndpoint(WikiAPIView):
    def patch(self, request, slug, folder_id):
        folder = self.folder_atau_404(folder_id)
        _wajib_kelola(self.penilai, folder.id)
        data = request.data
        # General dan urutan folder teratas mengubah Wiki untuk semua orang.
        if "umum" in data or ("urutan" in data and folder.parent_id is None):
            _wajib_admin(self.penilai)
        if "nama" in data:
            if folder.unit:
                raise Galat(_PESAN_UNIT)
            folder.nama = _nama_bersih(data.get("nama"))
        if "keterangan" in data:
            folder.keterangan = str(data.get("keterangan") or "")
        if "logo_props" in data:
            folder.logo_props = _logo_bersih(data.get("logo_props"))
        if "umum" in data:
            umum = bool(data.get("umum"))
            if umum and folder.parent_id:
                raise Galat("Only a top-level folder can be the General folder.")
            folder.umum = umum
        if "urutan" in data:
            try:
                folder.urutan = float(data.get("urutan"))
            except (TypeError, ValueError):
                raise Galat("urutan must be a number.")
        folder.save()
        return Response(self.folder_json(folder), status=status.HTTP_200_OK)

    def delete(self, request, slug, folder_id):
        folder = self.folder_atau_404(folder_id)
        _wajib_kelola(self.penilai, folder.id)
        if folder.unit:
            raise Galat("A division or department folder cannot be deleted.")
        if folder.archived_at is None:
            raise Galat("Archive the folder before deleting it.")
        punya_anak = WikiFolder.objects.filter(parent_id=folder.id).exists()
        punya_materi = WikiMaterial.objects.filter(folder_id=folder.id, berkas__is_uploaded=True).exists()
        if punya_anak or punya_materi:
            raise Galat("The folder is not empty.", status.HTTP_409_CONFLICT)
        WikiFolder.objects.filter(id=folder.id).update(deleted_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)


class WikiFolderArsipEndpoint(WikiAPIView):
    def post(self, request, slug, folder_id):
        folder = self.folder_atau_404(folder_id)
        _wajib_kelola(self.penilai, folder.id)
        if folder.unit:
            raise Galat("A division or department folder cannot be archived.")
        cap = timezone.now()
        ids = [folder.id] + [f.id for f in _keturunan(self.workspace.id, folder.id)]
        # Yang sudah diarsipkan lebih dulu mempertahankan capnya sendiri.
        WikiFolder.objects.filter(id__in=ids, archived_at__isnull=True).update(archived_at=cap, updated_at=cap)
        folder.refresh_from_db()
        return Response(self.folder_json(folder), status=status.HTTP_200_OK)

    def delete(self, request, slug, folder_id):
        folder = self.folder_atau_404(folder_id)
        _wajib_kelola(self.penilai, folder.id)
        if folder.archived_at is None:
            raise Galat("The folder is not archived.")
        if folder.parent_id:
            induk = WikiFolder.objects.filter(id=folder.parent_id).first()
            if induk is not None and induk.archived_at is not None:
                raise Galat("Unarchive the parent folder first.")
        cap = folder.archived_at
        ids = [folder.id] + [f.id for f in _keturunan(self.workspace.id, folder.id) if f.archived_at == cap]
        WikiFolder.objects.filter(id__in=ids, archived_at=cap).update(archived_at=None, updated_at=timezone.now())
        folder.refresh_from_db()
        return Response(self.folder_json(folder), status=status.HTTP_200_OK)


class WikiFolderPulihkanEndpoint(WikiAPIView):
    """Pulihkan folder dari tong sampah."""

    def post(self, request, slug, folder_id):
        folder = self.folder_atau_404(folder_id, semua=True)
        # Penilai juga mengenal folder di sampah, jadi wilayahnya tetap terbaca.
        _wajib_kelola(self.penilai, folder.id)
        if folder.deleted_at is None:
            raise Galat("The folder is not in the trash.")
        if folder.parent_id:
            induk = WikiFolder.all_objects.filter(id=folder.parent_id).first()
            if induk is None or induk.deleted_at is not None:
                raise Galat("Restore the parent folder first.")
        WikiFolder.all_objects.filter(id=folder.id).update(deleted_at=None, updated_at=timezone.now())
        folder.refresh_from_db()
        return Response(self.folder_json(folder), status=status.HTTP_200_OK)
