# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Materi Wiki
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Materi Wiki: satu berkas yang berdiri sendiri di dalam sebuah Topik.

Ini perbaikan atas rancangan sebelumnya yang menjadikan Materi sebuah halaman
yang orang ketik isinya, lalu berkasnya disisipkan lewat slash command. Yang
diminta pemilik instance bukan itu: "saya maunya dia ada materi yang memang
sudah di-upload oleh user tersebut di dalamnya", dan berkas itu dibuka langsung
di peramban untuk dibaca atau ditonton.

Bedanya bukan soal tampilan, melainkan soal MODEL, dan akibatnya menjalar:
selama Materi berupa halaman, nama, ukuran, dan tipe berkasnya tersimpan di
dalam binary Yjs sehingga kartu tidak bisa menyebut "PDF, 4,2 MB" tanpa membuka
dokumennya, dan menambah materi selalu dua langkah lewat editor.

Sebagai `FileAsset` semuanya jadi kolom sungguhan, dan mengunggah kembali jadi
satu langkah: pilih berkas.

Izinnya sengaja TIDAK dibuat baru. Materi menempel ke halaman Topik lewat FK
`page`, dan resolver ACL yang sudah ada menelusuri naik dari situ ke folder
Divisi. Jadi siapa boleh mengunggah dan siapa boleh menghapus dijawab aturan
yang sama persis dengan halaman.
"""

# Python imports
import io

# Django imports
from django.conf import settings
from django.db.models import Q

# Third party imports
import requests
from rest_framework import status
from rest_framework.response import Response

# Module imports
from ..base import BaseAPIView
from plane.app.permissions import allow_permission, ROLE
from plane.db.models import FileAsset, Page
from plane.settings.storage import S3Storage
from plane.utils.exception_logger import log_exception
from plane.utils.wiki_access import (
    can_edit_wiki_page,
    can_manage_wiki_material,
    can_manage_wiki_page,
    is_wiki_governed,
)

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

# Tipe yang HARUS dikonversi dulu. Tidak ada peramban yang bisa membuka
# ketiganya, dan itu satu-satunya alasan konversi ini ada.
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


def _jenis_pratinjau(mime):
    """Bagaimana sebuah berkas harus ditampilkan, dilihat dari tipenya saja."""
    if mime == "video/x-matroska":
        # Lolos `video/` tapi tidak ada peramban yang memutarnya. Pemutar hitam
        # yang diam saja lebih membingungkan daripada tombol unduh yang jujur.
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


def _materi_json(asset, user):
    attributes = asset.attributes or {}
    nama = attributes.get("name") or "Tanpa nama"
    pengunggah = asset.created_by
    return {
        "id": str(asset.id),
        # Topik tempat materi ini berada, supaya penampilnya punya jalan pulang
        # tanpa permintaan kedua.
        "topic_id": str(asset.page_id) if asset.page_id else None,
        # Judul yang bisa disunting, terpisah dari nama berkasnya. Berkas nyata
        # sering bernama "SOP_final_v3(1).pdf", dan itu bukan judul yang layak
        # dibaca 83 orang di halaman daftar.
        "title": attributes.get("title") or nama,
        "name": nama,
        "type": attributes.get("type") or "application/octet-stream",
        "size": asset.size,
        "kind": _jenis_pratinjau(attributes.get("type") or ""),
        "created_at": asset.created_at,
        "uploaded_by": (
            {
                "id": str(pengunggah.id),
                "display_name": pengunggah.display_name,
                "avatar_url": pengunggah.avatar_url,
            }
            if pengunggah
            else None
        ),
        # Dihitung server, bukan ditebak klien. Satu sumber kebenaran.
        "can_manage": can_manage_wiki_material(user, asset),
    }


def _materi_queryset(slug, project_id, page_id=None):
    qs = FileAsset.objects.filter(
        workspace__slug=slug,
        project_id=project_id,
        entity_type=FileAsset.EntityTypeContext.WIKI_MATERIAL,
        is_deleted=False,
        is_uploaded=True,
    ).select_related("created_by")
    if page_id is not None:
        qs = qs.filter(page_id=page_id)
    return qs


class WikiTopicMaterialEndpoint(BaseAPIView):
    """Daftar materi sebuah Topik.

    Satu permintaan mengembalikan seluruh materi berikut bendera `can_manage`
    per baris, jadi tombol hapus di kartu tidak perlu menebak dan tidak perlu
    menyalin aturan izin ke TypeScript.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id, page_id):
        page = Page.objects.filter(
            id=page_id, workspace__slug=slug, project_pages__project_id=project_id
        ).first()
        if page is None:
            return Response({"error": "Topik tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        materi = [_materi_json(a, request.user) for a in _materi_queryset(slug, project_id, page_id)]
        return Response(
            {
                "materials": materi,
                # Boleh menaruh materi baru di Topik ini. Dijawab di sini supaya
                # klien tidak perlu memanggil endpoint izin kedua hanya untuk
                # memutuskan satu tombol.
                "can_upload": (
                    can_edit_wiki_page(request.user, page) if is_wiki_governed(project_id) else True
                ),
            },
            status=status.HTTP_200_OK,
        )


class WikiFolderEndpoint(BaseAPIView):
    """Ganti nama dan ikon folder Divisi atau Topik.

    Kenapa endpoint sendiri, bukan PATCH halaman biasa: judul halaman yang
    SEBENARNYA hidup di binary Yjs, dan server Live mendorongnya balik ke
    database. Mengganti nama lewat PATCH polos akan tampak berhasil, lalu nama
    lama muncul lagi begitu halamannya dibuka. Itu jenis bug yang membuat orang
    berhenti percaya pada seluruh fitur.

    Jadi di sini `description_binary` dan `description_json` sekalian
    dikosongkan. Server Live membangun ulang dokumennya dari `description_html`
    plus `name` yang baru ketika binary-nya kosong
    (`apps/live/src/extensions/database.ts`), sehingga nama barunya bertahan.

    Aman untuk folder: isinya cuma penampung, dan `description_html` memang
    selalu disinkronkan server Live. JANGAN pakai jalur ini untuk halaman yang
    isinya tulisan sungguhan.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def patch(self, request, slug, project_id, page_id):
        page = Page.objects.filter(
            id=page_id, workspace__slug=slug, project_pages__project_id=project_id
        ).first()
        if page is None:
            return Response({"error": "Folder tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        if not can_manage_wiki_page(request.user, page):
            return Response(
                {
                    "error": "Hanya pembuatnya, kepala divisi pemilik folder, "
                    "atau Super Admin yang boleh mengubah folder ini."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        diubah = []
        nama = request.data.get("name")
        if nama is not None:
            nama = str(nama).strip()
            if not nama:
                return Response(
                    {"error": "Nama folder tidak boleh kosong."}, status=status.HTTP_400_BAD_REQUEST
                )
            page.name = nama[:255]
            diubah.append("name")
            # Kosongkan Yjs supaya judul barunya tidak ditimpa balik.
            page.description_binary = b""
            page.description_json = {}
            diubah += ["description_binary", "description_json"]

        logo = request.data.get("logo_props")
        if logo is not None:
            if not isinstance(logo, dict):
                return Response(
                    {"error": "logo_props harus berupa objek."}, status=status.HTTP_400_BAD_REQUEST
                )
            page.logo_props = logo
            diubah.append("logo_props")

        if not diubah:
            return Response({"error": "Tidak ada yang diubah."}, status=status.HTTP_400_BAD_REQUEST)

        # `.save()` penuh, BUKAN `.update()`: `Page.save()` menghitung ulang
        # `description_stripped`, dan melewatinya meninggalkan indeks pencarian
        # yang menunjuk isi lama.
        page.save()
        return Response(
            {"id": str(page.id), "name": page.name, "logo_props": page.logo_props},
            status=status.HTTP_200_OK,
        )


class WikiMaterialSearchEndpoint(BaseAPIView):
    """Cari materi di seluruh Wiki, bukan cuma di Topik yang sedang dibuka.

    Kotak "Cari materi..." tidak akan berguna kalau ia hanya menyaring kartu
    yang kebetulan sedang di layar. Orang mencari karena BELUM tahu materinya
    ada di divisi mana, dan itu justru pertanyaan yang paling sering dibawa ke
    Wiki.

    Dicocokkan ke judul dan nama berkasnya. Isi dokumennya TIDAK dicari, dan
    jangan pernah menjanjikan sebaliknya: tidak ada satu pun jalur di aplikasi
    ini yang membaca teks di dalam PDF.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id):
        kueri = (request.query_params.get("q") or "").strip()
        if len(kueri) < 2:
            return Response({"materials": []}, status=status.HTTP_200_OK)

        cocok = _materi_queryset(slug, project_id).filter(
            Q(attributes__title__icontains=kueri) | Q(attributes__name__icontains=kueri)
        )[:50]

        # Jejak "Divisi > Topik" diambil sekali untuk semua baris, bukan satu
        # query per kartu. Tanpa jejaknya, hasil pencarian cuma daftar nama
        # berkas tanpa memberi tahu orang harus ke mana untuk menemukannya lagi.
        page_ids = {a.page_id for a in cocok if a.page_id}
        halaman = {p.id: p for p in Page.objects.filter(id__in=page_ids).select_related("parent")}

        hasil = []
        for a in cocok:
            topik = halaman.get(a.page_id)
            jejak = [x for x in [getattr(topik, "parent", None), topik] if x is not None]
            hasil.append(
                {
                    **_materi_json(a, request.user),
                    "breadcrumb": [x.name for x in jejak],
                }
            )

        return Response({"materials": hasil}, status=status.HTTP_200_OK)


class WikiMaterialEndpoint(BaseAPIView):
    """Ganti judul sebuah materi.

    Sengaja hanya judul. Mengganti BERKASNYA berarti diam-diam menukar isi
    materi yang sudah dibaca orang, dan itu harus terlihat sebagai unggahan
    baru, bukan suntingan.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def patch(self, request, slug, project_id, asset_id):
        asset = _materi_queryset(slug, project_id).filter(id=asset_id).first()
        if asset is None:
            return Response({"error": "Materi tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        if not can_manage_wiki_material(request.user, asset):
            return Response(
                {
                    "error": "Hanya pengunggahnya, kepala divisi pemilik folder, "
                    "atau Super Admin yang boleh mengubah materi ini."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        judul = (request.data.get("title") or "").strip()
        if not judul:
            return Response({"error": "Judul tidak boleh kosong."}, status=status.HTTP_400_BAD_REQUEST)

        asset.attributes = {**(asset.attributes or {}), "title": judul[:255]}
        asset.save(update_fields=["attributes"])
        return Response(_materi_json(asset, request.user), status=status.HTTP_200_OK)


class WikiMaterialPreviewEndpoint(BaseAPIView):
    """Beri klien satu alamat yang siap dirender, apa pun tipe berkasnya.

    Untuk berkas yang memang bisa dibuka peramban, jawabannya alamat berkas itu
    sendiri. Untuk Word, Excel, dan PowerPoint, TIDAK ADA peramban yang sanggup
    membukanya, jadi berkasnya dikonversi lebih dulu jadi PDF lewat LibreOffice
    (Gotenberg), lalu hasilnya disimpan sebagai aset turunan dan dipakai ulang.

    Konversi dipilih daripada memasang tiga pustaka perender di sisi peramban
    karena satu mekanisme mengalahkan tiga: hasilnya memakai penampil PDF yang
    SUDAH terbukti jalan di produksi, kesetiaan rendernya LibreOffice, dan nol
    kilobyte tambahan di bundel yang diunduh 83 orang. Untuk PowerPoint memang
    tidak ada pilihan lain yang layak.
    """

    def _pratinjau_tersimpan(self, asset):
        return (
            FileAsset.objects.filter(
                workspace_id=asset.workspace_id,
                project_id=asset.project_id,
                entity_type=FileAsset.EntityTypeContext.WIKI_MATERIAL_PREVIEW,
                entity_identifier=str(asset.id),
                is_deleted=False,
                is_uploaded=True,
            )
            .order_by("-created_at")
            .first()
        )

    def _konversi(self, request, asset):
        """Ambil berkasnya, kirim ke LibreOffice, simpan PDF-nya. None kalau gagal."""
        alamat = getattr(settings, "GOTENBERG_URL", "") or ""
        if not alamat:
            return None, "konversi belum dinyalakan di server ini"

        batas = getattr(settings, "WIKI_PREVIEW_MAX_BYTES", 52428800)
        if asset.size and asset.size > batas:
            return None, "berkasnya terlalu besar untuk dikonversi"

        storage = S3Storage(request=request)
        try:
            objek = storage.s3_client.get_object(
                Bucket=storage.aws_storage_bucket_name, Key=asset.asset.name
            )
            isi = objek["Body"].read()
        except Exception as e:  # noqa: BLE001
            log_exception(e)
            return None, "berkasnya tidak bisa dibaca dari penyimpanan"

        nama = (asset.attributes or {}).get("name") or "materi"
        try:
            jawaban = requests.post(
                f"{alamat.rstrip('/')}/forms/libreoffice/convert",
                files={"files": (nama, io.BytesIO(isi), (asset.attributes or {}).get("type"))},
                timeout=getattr(settings, "WIKI_PREVIEW_TIMEOUT", 120),
            )
        except requests.RequestException as e:
            log_exception(e)
            return None, "layanan konversi tidak bisa dihubungi"

        if jawaban.status_code != 200 or not jawaban.content:
            return None, f"konversi gagal (status {jawaban.status_code})"

        kunci = f"{asset.workspace_id}/pratinjau-{asset.id}.pdf"
        if not storage.upload_file(io.BytesIO(jawaban.content), kunci, content_type="application/pdf"):
            return None, "hasil konversi gagal disimpan"

        pratinjau = FileAsset.objects.create(
            attributes={"name": f"{nama}.pdf", "type": "application/pdf", "size": len(jawaban.content)},
            asset=kunci,
            size=len(jawaban.content),
            workspace_id=asset.workspace_id,
            project_id=asset.project_id,
            page_id=asset.page_id,
            created_by=asset.created_by,
            entity_type=FileAsset.EntityTypeContext.WIKI_MATERIAL_PREVIEW,
            entity_identifier=str(asset.id),
            is_uploaded=True,
        )
        return pratinjau, None

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id, asset_id):
        asset = _materi_queryset(slug, project_id).filter(id=asset_id).first()
        if asset is None:
            return Response({"error": "Materi tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        jenis = _jenis_pratinjau((asset.attributes or {}).get("type") or "")
        berkas = _materi_json(asset, request.user)
        unduh = f"/api/assets/v2/workspaces/{slug}/projects/{project_id}/{asset.id}/"

        if jenis != "konversi":
            return Response(
                {
                    **berkas,
                    "kind": jenis,
                    "url": f"{unduh}?disposition=inline",
                    "download_url": unduh,
                },
                status=status.HTTP_200_OK,
            )

        pratinjau = self._pratinjau_tersimpan(asset)
        alasan = None
        if pratinjau is None:
            pratinjau, alasan = self._konversi(request, asset)

        if pratinjau is None:
            # Jangan pura-pura bisa. Kartu unduh yang menyebutkan alasannya jauh
            # lebih berguna daripada bingkai kosong yang tidak pernah memuat.
            return Response(
                {**berkas, "kind": "none", "url": None, "download_url": unduh, "reason": alasan},
                status=status.HTTP_200_OK,
            )

        pratinjau_url = f"/api/assets/v2/workspaces/{slug}/projects/{project_id}/{pratinjau.id}/"
        return Response(
            {
                **berkas,
                "kind": "pdf",
                "url": f"{pratinjau_url}?disposition=inline",
                "download_url": unduh,
                "converted": True,
            },
            status=status.HTTP_200_OK,
        )
