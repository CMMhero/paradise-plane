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
from django.contrib.postgres.search import TrigramWordSimilarity
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from plane.app.views.asset.v2 import allowed_mime_types
from plane.app.views.wiki_dasar import Galat, WikiAPIView
from plane.app.views.wiki_halaman import _DasarHalaman
from plane.bgtasks.storage_metadata_task import get_asset_object_metadata
from plane.bgtasks.wiki_indeks_task import indeks_materi
from plane.db.models import FileAsset, WikiFolder, WikiMaterial
from plane.settings.storage import S3Storage
from plane.utils.exception_logger import log_exception
from plane.utils.path_validator import sanitize_filename
from plane.utils.plan_limits import batas_ukuran_unggahan, batas_unggah_byte
from plane.utils.saklar_instance import PERM_WIKI_DELETE, PERM_WIKI_EDIT
from plane.utils.wiki_cari import MIN_TOKEN_MIRIP, ambang_mirip, cuplikan, pecah_kueri, skor_judul
from plane.utils.wiki_pratinjau import (  # noqa: F401 - jenis_pratinjau juga diimpor tes
    BERKAS_ZIP_MAKS_BYTE,
    CSV_MAKS_BYTE,
    TEKS_MAKS_BYTE,
    baca_csv,
    baca_docx,
    baca_teks,
    baca_xlsx,
    jenis_pratinjau,
    tebak_mime,
)

_ENTITAS = FileAsset.EntityTypeContext


def _penyimpanan_server():
    """Klien S3 untuk BACA/TULIS dari dalam server (pratinjau, konversi).

    Tanpa `request` supaya memakai alamat internal (`AWS_S3_ENDPOINT_URL`).
    `S3Storage(request=request)` sengaja mengarah ke alamat yang dilihat
    PERAMBAN (host permintaan atau `MINIO_PUBLIC_ENDPOINT_URL`), yang benar
    untuk menandatangani URL tetapi tidak terjangkau dari dalam kontainer API:
    pratinjau teks/CSV/Office gagal dengan "could not be read".
    """
    return S3Storage()


def _indeks_nanti(materi_id):
    """Jadwalkan pembacaan isi materi. Antrean mati tidak boleh menggagalkan unggah:
    materinya tetap bisa dicari lewat judul, dan `manage.py wiki_indeks_ulang` menyusul."""
    try:
        indeks_materi.delay(str(materi_id))
    except Exception as e:  # noqa: BLE001
        log_exception(e)


_MAKS_JUDUL = 255
_MAKS_HASIL_CARI = 50
_MAKS_KANDIDAT_CARI = 200
_MIN_KUERI = 2


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
        tipe = request.data.get("type") or "application/octet-stream"
        # Berkas teks (.txt, .md, .csv) tidak punya tanda tangan biner, jadi
        # klien sering mengirim tipe kosong. Tebak dari ekstensi, jangan menolak.
        if tipe == "application/octet-stream":
            tipe = tebak_mime(nama)
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
        _indeks_nanti(materi.id)
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
        # Satu PATCH bisa mengganti judul, memindahkan folder, atau keduanya.
        ubah = []
        if "judul" in request.data or "folder_id" not in request.data:
            judul = str(request.data.get("judul") or "").strip()
            if not judul or len(judul) > _MAKS_JUDUL:
                raise Galat("The title must be 1 to 255 characters.")
            materi.judul = judul
            ubah.append("judul")
        pindah = "folder_id" in request.data
        if pindah:
            tujuan = self._tujuan_pindah(request, materi)
            if tujuan is not None:
                materi.folder = tujuan
                ubah.append("folder")
        with transaction.atomic():
            materi.save(update_fields=[*ubah, "updated_at"])
            if "folder" in ubah:
                # Berkas mencatat folder asalnya; ikut dipindah supaya konsisten.
                FileAsset.objects.filter(id=materi.berkas_id).update(entity_identifier=str(materi.folder_id))
        return Response(self.materi_json(materi), status=status.HTTP_200_OK)

    def _tujuan_pindah(self, request, materi):
        """Folder tujuan yang sah, atau None bila sama dengan folder sekarang.

        Memindah = hak mengubah materi ini DAN hak mengunggah ke folder tujuan.
        Dua-duanya dari `PenilaiWiki`, jadi seret-lepas tidak punya aturan sendiri.
        """
        try:
            folder_id = uuid.UUID(str(request.data.get("folder_id")))
        except ValueError:
            raise Galat("folder_id must be a folder id.")
        if folder_id == materi.folder_id:
            return None
        tujuan = self.folder_atau_404(folder_id)
        if tujuan.archived_at is not None:
            raise Galat("This folder is archived.")
        if not self.penilai.boleh_unggah(tujuan.id):
            raise Galat("You are not allowed to move materials into this folder.", status.HTTP_403_FORBIDDEN)
        return tujuan

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

        penyimpanan = _penyimpanan_server()
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
        # Word lama, PowerPoint, dan OpenDocument baru bisa dibaca isinya dari PDF ini.
        _indeks_nanti(materi.id)
        return pratinjau, None

    def _ambil(self, request, berkas, maks):
        """Baca paling banyak `maks` byte pertama. (bytes, terpotong, alasan)."""
        penyimpanan = _penyimpanan_server()
        try:
            objek = penyimpanan.s3_client.get_object(
                Bucket=penyimpanan.aws_storage_bucket_name,
                Key=berkas.asset.name,
                Range=f"bytes=0-{maks}",
            )
            isi = objek["Body"].read(maks + 1)
        except Exception as e:  # noqa: BLE001
            log_exception(e)
            return None, False, "the file could not be read from storage"
        return isi[:maks], len(isi) > maks, None

    def _baca_isi(self, request, materi, jenis):
        """Isi pratinjau yang dibaca server, atau (None, alasan).

        Dibatasi ukuran: berkas zip (xlsx, docx) harus dibaca utuh untuk diurai,
        jadi yang melebihi batas ditolak dengan alasan, bukan dipotong.
        """
        berkas = materi.berkas
        nama = (berkas.attributes or {}).get("name") or ""
        tidak_terbaca = "the file could not be read as " + ("text" if jenis in ("text", "markdown", "csv") else jenis)

        if jenis in ("xlsx", "docx"):
            data, terpotong, alasan = self._ambil(request, berkas, BERKAS_ZIP_MAKS_BYTE)
            if data is None:
                return None, alasan
            if terpotong:
                return None, "the file is too large to preview"
            isi = baca_xlsx(data) if jenis == "xlsx" else baca_docx(data)
            if not isi:
                return None, tidak_terbaca
            return {"kind": "table" if jenis == "xlsx" else "document", **isi}, None

        maks = CSV_MAKS_BYTE if jenis == "csv" else TEKS_MAKS_BYTE
        data, terpotong, alasan = self._ambil(request, berkas, maks)
        if data is None:
            return None, alasan
        if jenis == "csv":
            isi = baca_csv(data, nama, terpotong)
            if isi is None:
                # Bukan CSV yang sah: tampilkan sebagai teks biasa kalau memang teks.
                isi = baca_teks(data, terpotong)
                return ({"kind": "text", **isi}, None) if isi else (None, tidak_terbaca)
            return {"kind": "table", **isi}, None
        isi = baca_teks(data, terpotong)
        return ({"kind": jenis, **isi}, None) if isi else (None, tidak_terbaca)

    def get(self, request, slug, materi_id):
        materi = self.materi_atau_404(materi_id)
        tipe = (materi.berkas.attributes or {}).get("type") or ""
        nama = (materi.berkas.attributes or {}).get("name") or ""
        jenis = jenis_pratinjau(tipe, nama)
        berkas = self.materi_json(materi)
        unduh = self.url_berkas(materi.berkas_id)
        sebaris = f"{unduh}?disposition=inline"

        if jenis in ("text", "markdown", "csv", "xlsx"):
            isi, alasan = self._baca_isi(request, materi, jenis)
            if isi is None:
                return Response(
                    {**berkas, "kind": "none", "url": None, "download_url": unduh, "reason": alasan},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {**berkas, "url": sebaris, "download_url": unduh, **isi},
                status=status.HTTP_200_OK,
            )

        if jenis not in ("konversi", "docx"):
            return Response(
                {**berkas, "kind": jenis, "url": sebaris, "download_url": unduh},
                status=status.HTTP_200_OK,
            )

        # Word: PDF hasil konversi lebih setia (gambar, tata letak). Kalau layanan
        # konversi mati atau gagal, jatuh ke tampilan sederhana yang dibaca server.
        pratinjau, alasan = self._tersimpan(materi), None
        if pratinjau is None:
            pratinjau, alasan = self._konversi(request, materi)
        if pratinjau is None and jenis == "docx":
            isi, alasan_baca = self._baca_isi(request, materi, "docx")
            if isi is not None:
                return Response(
                    {**berkas, "url": sebaris, "download_url": unduh, "fallback": True, **isi},
                    status=status.HTTP_200_OK,
                )
            alasan = alasan_baca or alasan
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


class WikiCariEndpoint(_DasarHalaman):
    """Cari materi (judul, nama berkas, ISI dokumen) dan halaman departemen.

    Tiap kata kueri harus cocok di salah satu tempat, persis atau mirip
    (pg_trgm, jadi salah ketik satu-dua huruf tetap ketemu). Urutan: judul yang
    paling cocok dulu, lalu yang hanya cocok di isi, lalu yang terbaru.

    Jawaban: `{"materials": [...], "pages": [...]}`. Tiap hasil membawa
    `cuplikan` (potongan isi di sekitar kata yang cocok) dan `sorot` (kata-kata
    itu persis seperti tertulis di isi, untuk disorot klien). Halaman disaring
    dengan izin yang sama seperti daftar halaman di folder departemen.
    """

    def get(self, request, slug):
        kueri = (request.query_params.get("q") or "").strip()
        tokens = pecah_kueri(kueri)
        if len(kueri) < _MIN_KUERI or not tokens:
            return Response({"materials": [], "pages": []}, status=status.HTTP_200_OK)
        with ambang_mirip():
            materi = self._cari_materi(kueri, tokens)
            halaman = self.cari_halaman(tokens)
        return Response({"materials": materi, "pages": halaman}, status=status.HTTP_200_OK)

    def _cari_materi(self, kueri, tokens):
        cocok = Q()
        for kata in tokens:
            satu = (
                Q(judul__icontains=kata) | Q(berkas__attributes__name__icontains=kata) | Q(isi_teks__icontains=kata)
            )
            if len(kata) >= MIN_TOKEN_MIRIP:
                satu |= Q(judul__kata_mirip=kata) | Q(isi_teks__kata_mirip=kata)
            cocok &= satu
        kandidat = list(
            WikiMaterial.objects.filter(
                cocok, workspace_id=self.workspace.id, berkas__is_uploaded=True, berkas__is_deleted=False
            )
            .select_related("berkas")
            # Isi bisa 100 ribu karakter per baris; hanya hasil teratas yang dibaca di bawah.
            .defer("isi_teks")
            .annotate(mirip=TrigramWordSimilarity(kueri, "judul"))
            .order_by("-mirip", "-created_at")[:_MAKS_KANDIDAT_CARI]
        )
        def _skor(m):
            return skor_judul(tokens, f"{m.judul} {(m.berkas.attributes or {}).get('name', '')}")

        urut = sorted(kandidat, key=_skor, reverse=True)[:_MAKS_HASIL_CARI]
        isi = dict(WikiMaterial.objects.filter(id__in=[m.id for m in urut]).values_list("id", "isi_teks"))
        peta = {
            str(i): (p, n)
            for i, p, n in WikiFolder.objects.filter(workspace_id=self.workspace.id).values_list(
                "id", "parent_id", "nama"
            )
        }
        hasil = []
        for m in urut:
            potongan, sorot = cuplikan(isi.get(m.id, ""), tokens)
            hasil.append(
                {**self.materi_json(m), "jejak": self.jejak(m.folder_id, peta), "cuplikan": potongan, "sorot": sorot}
            )
        return hasil


class WikiSampahEndpoint(WikiAPIView):
    """Admin melihat semua yang terhapus; pengelola (KEP-95) semua yang terhapus
    di wilayahnya; yang lain hanya materi unggahannya.

    `?folder=<id>` (KEP-97, tab Materials departemen) mempersempit jawaban ke
    folder itu dan semua yang ada di bawahnya. Hak tidak berubah: saringan ini
    hanya memotong, tidak pernah menambah.
    """

    def _akar(self, request):
        nilai = request.query_params.get("folder")
        if not nilai:
            return None
        try:
            akar_id = uuid.UUID(str(nilai))
        except ValueError:
            raise Galat("folder must be a folder id.")
        return self.folder_atau_404(akar_id, semua=True).id

    def get(self, request, slug):
        penilai = self.penilai
        akar = self._akar(request)

        def dalam_akar(folder_id):
            return akar is None or penilai.di_bawah(folder_id, akar)

        folders = []
        if penilai.admin or penilai.punya_wilayah:
            folders = [
                {**self.folder_json(f), "deleted_at": f.deleted_at}
                for f in WikiFolder.all_objects.filter(
                    workspace_id=self.workspace.id, deleted_at__isnull=False
                ).order_by("-deleted_at")
                if penilai.mengelola(f.id) and dalam_akar(f.id)
            ]
        materi = WikiMaterial.all_objects.filter(
            workspace_id=self.workspace.id, deleted_at__isnull=False, berkas__is_uploaded=True
        ).select_related("berkas")
        if not penilai.admin:
            if penilai.punya_wilayah:
                materi = [m for m in materi if m.created_by_id == request.user.id or penilai.mengelola(m.folder_id)]
            else:
                materi = materi.filter(created_by_id=request.user.id)
        terurut = sorted((m for m in materi if dalam_akar(m.folder_id)), key=lambda m: m.deleted_at, reverse=True)
        return Response(
            {
                "folders": folders,
                "materials": [{**self.materi_json(m), "deleted_at": m.deleted_at} for m in terurut],
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
