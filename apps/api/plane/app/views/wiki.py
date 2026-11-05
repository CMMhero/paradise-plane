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
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from plane.app.views.wiki_dasar import Galat, WikiAPIView, anotasi_jumlah
from plane.db.models import WikiFolder, WikiMaterial

_PESAN_ADMIN = "Only a workspace admin can manage the Wiki structure."
_PESAN_UNIT = "This folder follows its division or department name. Rename it in God Mode."
_MAKS_NAMA = 255


def _wajib_admin(penilai):
    if not penilai.boleh_kelola_folder():
        raise Galat(_PESAN_ADMIN, status.HTTP_403_FORBIDDEN)


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
        folder = anotasi_jumlah(WikiFolder.objects.filter(workspace_id=self.workspace.id))
        return Response(
            {
                "is_admin": self.penilai.admin,
                "user_id": str(request.user.id),
                "folders": [self.folder_json(f, f._jumlah) for f in folder],
            },
            status=status.HTTP_200_OK,
        )


class WikiFolderListEndpoint(WikiAPIView):
    def post(self, request, slug):
        _wajib_admin(self.penilai)
        nama = _nama_bersih(request.data.get("nama"))
        parent_id = request.data.get("parent_id") or None
        umum = bool(request.data.get("umum", False))
        if parent_id:
            if umum:
                raise Galat("Only a top-level folder can be the General folder.")
            induk = self.folder_atau_404(parent_id)
            if induk.archived_at is not None:
                raise Galat("The parent folder is archived.")
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
        return Response(self.folder_json(folder), status=status.HTTP_201_CREATED)


class WikiFolderEndpoint(WikiAPIView):
    def patch(self, request, slug, folder_id):
        _wajib_admin(self.penilai)
        folder = self.folder_atau_404(folder_id)
        data = request.data
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
        _wajib_admin(self.penilai)
        folder = self.folder_atau_404(folder_id)
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
        _wajib_admin(self.penilai)
        folder = self.folder_atau_404(folder_id)
        if folder.unit:
            raise Galat("A division or department folder cannot be archived.")
        cap = timezone.now()
        ids = [folder.id] + [f.id for f in _keturunan(self.workspace.id, folder.id)]
        # Yang sudah diarsipkan lebih dulu mempertahankan capnya sendiri.
        WikiFolder.objects.filter(id__in=ids, archived_at__isnull=True).update(archived_at=cap, updated_at=cap)
        folder.refresh_from_db()
        return Response(self.folder_json(folder), status=status.HTTP_200_OK)

    def delete(self, request, slug, folder_id):
        _wajib_admin(self.penilai)
        folder = self.folder_atau_404(folder_id)
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
        _wajib_admin(self.penilai)
        folder = self.folder_atau_404(folder_id, semua=True)
        if folder.deleted_at is None:
            raise Galat("The folder is not in the trash.")
        if folder.parent_id:
            induk = WikiFolder.all_objects.filter(id=folder.parent_id).first()
            if induk is None or induk.deleted_at is not None:
                raise Galat("Restore the parent folder first.")
        WikiFolder.all_objects.filter(id=folder.id).update(deleted_at=None, updated_at=timezone.now())
        folder.refresh_from_db()
        return Response(self.folder_json(folder), status=status.HTTP_200_OK)
