# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: API materi & berkas Wiki mandiri (KEP-94)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Materi Wiki: unggah, daftar, ubah judul, hapus, pratinjau, cari, tong sampah.

Satu materi = satu `WikiMaterial` + satu `FileAsset` (entity WIKI_MATERIAL,
tanpa project dan tanpa page). Id materi sama dengan id berkasnya. Berkas
disajikan lewat `wiki/files/<id>/` yang hanya meminta keanggotaan workspace.
"""

import io
import uuid

import requests
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from plane.app.views.asset.v2 import allowed_mime_types
from plane.app.views.wiki_dasar import Galat, WikiAPIView
from plane.bgtasks.storage_metadata_task import get_asset_object_metadata
from plane.db.models import FileAsset, WikiFolder, WikiMaterial
from plane.settings.storage import S3Storage
from plane.utils.exception_logger import log_exception
from plane.utils.path_validator import sanitize_filename
from plane.utils.plan_limits import batas_ukuran_unggahan, batas_unggah_byte
from plane.utils.saklar_instance import PERM_WIKI_DELETE, PERM_WIKI_EDIT

_ENTITAS = FileAsset.EntityTypeContext
_MAKS_JUDUL = 255
_MAKS_HASIL_CARI = 50
_MIN_KUERI = 2

# Tipe yang peramban sanggup tampilkan sendiri, tanpa konversi apa pun.
_PRATINJAU_TEKS = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "text/css",
    "text/javascript",
    "text/xml",
    "application/xml",
    "application/json",
}

# Tipe yang HARUS dikonversi dulu: tidak ada peramban yang bisa membukanya.
_PERLU_KONVERSI = {
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/rtf",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.presentation",
}


def jenis_pratinjau(mime):
    """Bagaimana sebuah berkas ditampilkan, dilihat dari tipenya saja."""
    if mime == "video/x-matroska":
        return "none"
    if mime in _PERLU_KONVERSI:
        return "konversi"
    if mime == "application/pdf":
        return "pdf"
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("audio/"):
        return "audio"
    if mime in _PRATINJAU_TEKS:
        return "text"
    return "none"


class WikiMateriFolderEndpoint(WikiAPIView):
    """Daftar dan unggah materi di satu folder."""

    def get(self, request, slug, folder_id):
        folder = self.folder_atau_404(folder_id)
        materi = WikiMaterial.objects.filter(
            folder_id=folder.id, berkas__is_uploaded=True, berkas__is_deleted=False
        ).select_related("berkas")
        return Response(
            {
                "can_upload": folder.archived_at is None and self.penilai.boleh_unggah(folder.id),
                "materials": [self.materi_json(m) for m in materi.order_by("-created_at")],
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, slug, folder_id):
        folder = self.folder_atau_404(folder_id)
        if folder.archived_at is not None:
            raise Galat("This folder is archived.")
        if not self.penilai.boleh_unggah(folder.id):
            raise Galat("You are not allowed to upload to this folder.", status.HTTP_403_FORBIDDEN)

        nama = sanitize_filename(request.data.get("name")) or "unnamed"
        tipe = request.data.get("type", "application/octet-stream")
        try:
            ukuran = int(request.data.get("size", batas_unggah_byte()))
        except (TypeError, ValueError):
            raise Galat("size must be a number.")
        if tipe not in allowed_mime_types("WIKI_MATERIAL"):
            raise Galat(f"Invalid file type '{tipe}'.")
        # Kuota tingkatan ditegakkan di sini, sama seperti titik unggah lain.
        ukuran = batas_ukuran_unggahan(slug, ukuran)

        kunci = f"{self.workspace.id}/{uuid.uuid4().hex}-{nama}"
        with transaction.atomic():
            berkas = FileAsset.objects.create(
                attributes={"name": nama, "type": tipe, "size": ukuran},
                asset=kunci,
                size=ukuran,
                workspace=self.workspace,
                created_by=request.user,
                entity_type=_ENTITAS.WIKI_MATERIAL,
                entity_identifier=str(folder.id),
            )
            materi = WikiMaterial(
                id=berkas.id,
                workspace=self.workspace,
                folder=folder,
                berkas=berkas,
                judul=nama[:_MAKS_JUDUL],
            )
            materi.save(created_by_id=request.user.id)

        penyimpanan = S3Storage(request=request)
        upload_data = penyimpanan.generate_presigned_post(object_name=kunci, file_type=tipe, file_size=ukuran)
        return Response(
            {"upload_data": upload_data, "material": self.materi_json(materi)},
            status=status.HTTP_200_OK,
        )


class WikiMateriTerunggahEndpoint(WikiAPIView):
    def post(self, request, slug, materi_id):
        materi = self.materi_atau_404(materi_id, harus_terunggah=False)
        if materi.created_by_id != request.user.id:
            raise Galat("Only the uploader can confirm this upload.", status.HTTP_403_FORBIDDEN)
        berkas = materi.berkas
        if not berkas.storage_metadata:
            get_asset_object_metadata.delay(asset_id=str(berkas.id))
        berkas.is_uploaded = True
        berkas.save(update_fields=["is_uploaded"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class WikiMateriEndpoint(WikiAPIView):
    def get(self, request, slug, materi_id):
        materi = self.materi_atau_404(materi_id)
        return Response(
            {**self.materi_json(materi), "jejak": self.jejak(materi.folder_id)},
            status=status.HTTP_200_OK,
        )

    def patch(self, request, slug, materi_id):
        materi = self.materi_atau_404(materi_id)
        if not self.penilai.boleh_kelola_materi(materi, PERM_WIKI_EDIT):
            raise Galat("You are not allowed to change this material.", status.HTTP_403_FORBIDDEN)
        judul = str(request.data.get("judul") or "").strip()
        if not judul or len(judul) > _MAKS_JUDUL:
            raise Galat("The title must be 1 to 255 characters.")
        materi.judul = judul
        materi.save(update_fields=["judul", "updated_at"])
        return Response(self.materi_json(materi), status=status.HTTP_200_OK)

    def delete(self, request, slug, materi_id):
        materi = self.materi_atau_404(materi_id)
        if not self.penilai.boleh_kelola_materi(materi, PERM_WIKI_DELETE):
            raise Galat("You are not allowed to delete this material.", status.HTTP_403_FORBIDDEN)
        sekarang = timezone.now()
        with transaction.atomic():
            # `.update()`, bukan `.delete()`: soft delete model menyeret task
            # kaskade yang tidak diperlukan untuk satu baris.
            WikiMaterial.objects.filter(id=materi.id).update(deleted_at=sekarang, updated_at=sekarang)
            FileAsset.objects.filter(id=materi.berkas_id).update(is_deleted=True, deleted_at=sekarang)
        return Response(status=status.HTTP_204_NO_CONTENT)


class WikiPratinjauEndpoint(WikiAPIView):
    """Satu alamat yang siap dirender apa pun tipe berkasnya. Word, Excel, dan
    PowerPoint dikonversi ke PDF lewat Gotenberg, hasilnya disimpan di
    `WikiMaterial.pratinjau` dan dipakai ulang."""

    def _tersimpan(self, materi):
        if materi.pratinjau_id is None:
            return None
        pr = materi.pratinjau
        return pr if pr.is_uploaded and not pr.is_deleted else None

    def _konversi(self, request, materi):
        """Ambil berkasnya, kirim ke LibreOffice, simpan PDF-nya. (aset, alasan)."""
        alamat = getattr(settings, "GOTENBERG_URL", "") or ""
        if not alamat:
            return None, "conversion is not enabled on this server"
        asal = materi.berkas
        batas = getattr(settings, "WIKI_PREVIEW_MAX_BYTES", 52428800)
        if asal.size and asal.size > batas:
            return None, "the file is too large to convert"

        penyimpanan = S3Storage(request=request)
        try:
            objek = penyimpanan.s3_client.get_object(Bucket=penyimpanan.aws_storage_bucket_name, Key=asal.asset.name)
            isi = objek["Body"].read()
        except Exception as e:  # noqa: BLE001
            log_exception(e)
            return None, "the file could not be read from storage"

        nama = (asal.attributes or {}).get("name") or "material"
        try:
            jawaban = requests.post(
                f"{alamat.rstrip('/')}/forms/libreoffice/convert",
                files={"files": (nama, io.BytesIO(isi), (asal.attributes or {}).get("type"))},
                timeout=getattr(settings, "WIKI_PREVIEW_TIMEOUT", 120),
            )
        except requests.RequestException as e:
            log_exception(e)
            return None, "the conversion service could not be reached"
        if jawaban.status_code != 200 or not jawaban.content:
            return None, f"conversion failed (status {jawaban.status_code})"

        kunci = f"{asal.workspace_id}/pratinjau-{asal.id}.pdf"
        if not penyimpanan.upload_file(io.BytesIO(jawaban.content), kunci, content_type="application/pdf"):
            return None, "the converted file could not be saved"

        pratinjau = FileAsset.objects.create(
            attributes={"name": f"{nama}.pdf", "type": "application/pdf", "size": len(jawaban.content)},
            asset=kunci,
            size=len(jawaban.content),
            workspace_id=asal.workspace_id,
            created_by=asal.created_by,
            entity_type=_ENTITAS.WIKI_MATERIAL_PREVIEW,
            entity_identifier=str(materi.id),
            is_uploaded=True,
        )
        WikiMaterial.objects.filter(id=materi.id).update(pratinjau=pratinjau)
        return pratinjau, None

    def get(self, request, slug, materi_id):
        materi = self.materi_atau_404(materi_id)
        jenis = jenis_pratinjau((materi.berkas.attributes or {}).get("type") or "")
        berkas = self.materi_json(materi)
        unduh = self.url_berkas(materi.berkas_id)

        if jenis != "konversi":
            return Response(
                {**berkas, "kind": jenis, "url": f"{unduh}?disposition=inline", "download_url": unduh},
                status=status.HTTP_200_OK,
            )

        pratinjau, alasan = self._tersimpan(materi), None
        if pratinjau is None:
            pratinjau, alasan = self._konversi(request, materi)
        if pratinjau is None:
            return Response(
                {**berkas, "kind": "none", "url": None, "download_url": unduh, "reason": alasan},
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                **berkas,
                "kind": "pdf",
                "url": f"{self.url_berkas(pratinjau.id)}?disposition=inline",
                "download_url": unduh,
                "converted": True,
            },
            status=status.HTTP_200_OK,
        )


class WikiBerkasEndpoint(WikiAPIView):
    """302 ke URL presigned. Cukup anggota workspace; tidak ada gerbang project."""

    def get(self, request, slug, asset_id):
        berkas = FileAsset.objects.filter(
            id=asset_id,
            workspace_id=self.workspace.id,
            entity_type__in=[_ENTITAS.WIKI_MATERIAL, _ENTITAS.WIKI_MATERIAL_PREVIEW],
            is_uploaded=True,
            is_deleted=False,
        ).first()
        if berkas is None:
            raise Galat("The requested file could not be found.", status.HTTP_404_NOT_FOUND)
        if berkas.entity_type == _ENTITAS.WIKI_MATERIAL:
            hidup = WikiMaterial.objects.filter(berkas_id=berkas.id).exists()
        else:
            hidup = WikiMaterial.objects.filter(pratinjau_id=berkas.id).exists()
        if not hidup:
            raise Galat("The requested file could not be found.", status.HTTP_404_NOT_FOUND)

        disposisi = "inline" if request.query_params.get("disposition") == "inline" else "attachment"
        penyimpanan = S3Storage(request=request)
        url = penyimpanan.generate_presigned_url(
            object_name=berkas.asset.name,
            disposition=disposisi,
            filename=(berkas.attributes or {}).get("name"),
        )
        return HttpResponseRedirect(url)


class WikiCariEndpoint(WikiAPIView):
    """Cari judul atau nama berkas. Isi dokumen TIDAK dicari."""

    def get(self, request, slug):
        kueri = (request.query_params.get("q") or "").strip()
        if len(kueri) < _MIN_KUERI:
            return Response([], status=status.HTTP_200_OK)
        cocok = list(
            WikiMaterial.objects.filter(
                workspace_id=self.workspace.id, berkas__is_uploaded=True, berkas__is_deleted=False
            )
            .filter(Q(judul__icontains=kueri) | Q(berkas__attributes__name__icontains=kueri))
            .select_related("berkas")
            .order_by("-created_at")[:_MAKS_HASIL_CARI]
        )
        peta = {
            str(i): (p, n)
            for i, p, n in WikiFolder.objects.filter(workspace_id=self.workspace.id).values_list(
                "id", "parent_id", "nama"
            )
        }
        return Response(
            [{**self.materi_json(m), "jejak": self.jejak(m.folder_id, peta)} for m in cocok],
            status=status.HTTP_200_OK,
        )


class WikiSampahEndpoint(WikiAPIView):
    """Admin melihat semua yang terhapus; yang lain hanya materi unggahannya."""

    def get(self, request, slug):
        folders = []
        if self.penilai.admin:
            folders = [
                {**self.folder_json(f), "deleted_at": f.deleted_at}
                for f in WikiFolder.all_objects.filter(
                    workspace_id=self.workspace.id, deleted_at__isnull=False
                ).order_by("-deleted_at")
            ]
        materi = WikiMaterial.all_objects.filter(
            workspace_id=self.workspace.id, deleted_at__isnull=False, berkas__is_uploaded=True
        ).select_related("berkas")
        if not self.penilai.admin:
            materi = materi.filter(created_by_id=request.user.id)
        return Response(
            {
                "folders": folders,
                "materials": [
                    {**self.materi_json(m), "deleted_at": m.deleted_at} for m in materi.order_by("-deleted_at")
                ],
            },
            status=status.HTTP_200_OK,
        )


class WikiMateriPulihkanEndpoint(WikiAPIView):
    def post(self, request, slug, materi_id):
        materi = self.materi_atau_404(materi_id, semua=True)
        if materi.deleted_at is None:
            raise Galat("The material is not in the trash.")
        if not self.penilai.boleh_kelola_materi(materi, PERM_WIKI_DELETE):
            raise Galat("You are not allowed to restore this material.", status.HTTP_403_FORBIDDEN)
        if materi.folder.deleted_at is not None:
            raise Galat("Restore the folder first.")
        with transaction.atomic():
            WikiMaterial.all_objects.filter(id=materi.id).update(deleted_at=None, updated_at=timezone.now())
            FileAsset.all_objects.filter(id=materi.berkas_id).update(is_deleted=False, deleted_at=None)
        materi.refresh_from_db()
        return Response(self.materi_json(materi), status=status.HTTP_200_OK)
