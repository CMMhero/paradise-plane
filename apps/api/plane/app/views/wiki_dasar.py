# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: dasar API Wiki mandiri (KEP-94)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Fondasi bersama view Wiki mandiri.

Wiki bukan project lagi, jadi gerbangnya bukan `allow_permission` project
melainkan keanggotaan workspace. `WikiAPIView` menjaga itu sekali di `initial`,
membuat satu `PenilaiWiki` per permintaan, dan memberi jalan pintas
`raise Galat("...", 400)` supaya semua jawaban galat berbentuk
`{"error": "<kalimat Inggris>"}`.
"""

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.response import Response

from plane.app.views.base import BaseAPIView
from plane.db.models import Workspace, WikiFolder, WikiMaterial
from plane.utils.saklar_instance import PERM_WIKI_DELETE, PERM_WIKI_EDIT
from plane.utils.wiki_mandiri import PenilaiWiki, is_anggota_workspace


class Galat(Exception):
    def __init__(self, pesan, kode=status.HTTP_400_BAD_REQUEST):
        super().__init__(pesan)
        self.pesan = pesan
        self.kode = kode


class WikiAPIView(BaseAPIView):
    workspace = None
    penilai = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.workspace = Workspace.objects.filter(slug=kwargs.get("slug")).first()
        if self.workspace is None:
            raise Galat("Workspace not found.", status.HTTP_404_NOT_FOUND)
        if not is_anggota_workspace(request.user, self.workspace.id):
            raise Galat("You are not a member of this workspace.", status.HTTP_403_FORBIDDEN)
        self.penilai = PenilaiWiki(request.user, self.workspace.id)

    def handle_exception(self, exc):
        if isinstance(exc, Galat):
            return Response({"error": exc.pesan}, status=exc.kode)
        return super().handle_exception(exc)

    # -- pengambil objek -------------------------------------------------

    def folder_atau_404(self, folder_id, semua=False):
        manajer = WikiFolder.all_objects if semua else WikiFolder.objects
        folder = manajer.filter(id=folder_id, workspace_id=self.workspace.id).first()
        if folder is None:
            raise Galat("Folder not found.", status.HTTP_404_NOT_FOUND)
        return folder

    def materi_atau_404(self, materi_id, semua=False, harus_terunggah=True):
        manajer = WikiMaterial.all_objects if semua else WikiMaterial.objects
        materi = manajer.filter(id=materi_id, workspace_id=self.workspace.id).select_related("berkas", "folder").first()
        if materi is None or (harus_terunggah and not materi.berkas.is_uploaded):
            raise Galat("Material not found.", status.HTTP_404_NOT_FOUND)
        return materi

    # -- serialisasi -----------------------------------------------------

    def url_berkas(self, berkas_id):
        return f"/api/workspaces/{self.workspace.slug}/wiki/files/{berkas_id}/"

    def folder_json(self, f, jumlah=0, jumlah_halaman=0, project_id=None):
        """`jumlah_halaman` dan `project_id` hanya diisi pohon (`GET wiki/`): angka
        halaman departemen yang boleh dilihat, dan project departemen folder itu."""
        return {
            "id": str(f.id),
            "parent_id": str(f.parent_id) if f.parent_id else None,
            "nama": f.nama,
            "keterangan": f.keterangan,
            "isi_lama_html": f.isi_lama_html,
            "logo_props": f.logo_props,
            "urutan": f.urutan,
            "divisi_id": str(f.divisi_id) if f.divisi_id else None,
            "departemen_id": str(f.departemen_id) if f.departemen_id else None,
            "umum": f.umum,
            "archived_at": f.archived_at,
            "created_by": str(f.created_by_id) if f.created_by_id else None,
            "created_at": f.created_at,
            "jumlah_materi": jumlah,
            "jumlah_halaman": jumlah_halaman,
            "project_id": str(project_id) if project_id else None,
            "can_upload": f.archived_at is None and self.penilai.boleh_unggah(f.id),
            "can_manage": self.penilai.boleh_kelola_folder(f.id),
        }

    def materi_json(self, m):
        atribut = m.berkas.attributes or {}
        nama = atribut.get("name") or m.judul or "Unnamed"
        return {
            "id": str(m.id),
            "folder_id": str(m.folder_id),
            "judul": m.judul or nama,
            "name": nama,
            "type": atribut.get("type") or "application/octet-stream",
            "size": m.berkas.size,
            "url": self.url_berkas(m.berkas_id),
            "created_by": str(m.created_by_id) if m.created_by_id else None,
            "created_at": m.created_at,
            "can_manage": self.penilai.boleh_kelola_materi(m, PERM_WIKI_EDIT),
            "can_delete": self.penilai.boleh_kelola_materi(m, PERM_WIKI_DELETE),
            "has_preview": m.pratinjau_id is not None,
        }

    def jejak(self, folder_id, peta=None):
        """Jalur akar sampai folder: [{id, nama}]. `peta` = {id: (parent_id, nama)}
        supaya daftar banyak baris tidak membaca ulang."""
        if peta is None:
            peta = {
                str(i): (p, n)
                for i, p, n in WikiFolder.objects.filter(workspace_id=self.workspace.id).values_list(
                    "id", "parent_id", "nama"
                )
            }
        hasil, sekarang, langkah = [], str(folder_id), 0
        while sekarang in peta and langkah < 50:
            induk, nama = peta[sekarang]
            hasil.append({"id": sekarang, "nama": nama})
            sekarang = str(induk) if induk else ""
            langkah += 1
        hasil.reverse()
        return hasil


def anotasi_jumlah(qs):
    """Hitung materi terunggah, hidup, langsung di tiap folder (satu query)."""
    return qs.annotate(
        _jumlah=Count(
            "materi",
            filter=Q(
                materi__deleted_at__isnull=True,
                materi__berkas__is_uploaded=True,
                materi__berkas__is_deleted=False,
            ),
        )
    )
