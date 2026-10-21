# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os

from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse

# Arsip Corresponding Source, disalin ke image oleh Dockerfile.api.
#
# ⚠️ BASE_DIR di sini adalah `/code/plane`, BUKAN `/code`. Nilainya diturunkan
# dua tingkat dari `plane/settings/common.py`, jadi ia menunjuk paket `plane`
# itu sendiri. `static-assets/` juga tinggal di situ, jadi arsip ini mengikuti
# kebiasaan yang sudah ada. Kalau Dockerfile menyalinnya ke `/code`, endpoint
# ini akan menjawab 503 padahal berkasnya ada.
CORRESPONDING_SOURCE_PATH = os.path.join(
    settings.BASE_DIR, "agpl-source", "corresponding-source.tar.gz"
)


def health_check(request):
    return JsonResponse({"status": "OK"})


def robots_txt(request):
    return HttpResponse("User-agent: *\nDisallow: /", content_type="text/plain")


def corresponding_source(request):
    """Tawaran kode sumber yang diwajibkan AGPL-3.0 pasal 13.

    Pasal 13 mewajibkan setiap pengguna yang mengakses perangkat lunak ini lewat
    jaringan ditawari Corresponding Source versi yang SEDANG BERJALAN, gratis,
    lewat cara yang lazim untuk menyalin perangkat lunak. Berkas ini dibuat CI
    dengan `git archive` dari commit yang sama dengan image, jadi isinya cocok
    dengan yang dijalankan, bukan sekadar cabang terbaru.

    SENGAJA tanpa autentikasi. Kewajibannya melekat pada "semua pengguna yang
    berinteraksi lewat jaringan", dan mengunci tawaran ini di balik login akan
    mengeluarkan sebagian dari mereka. Isinya memang sudah AGPL, tidak ada
    rahasia di dalamnya: berkas .env tidak pernah terlacak git sehingga tidak
    pernah ikut ke dalam arsip.
    """
    if not os.path.exists(CORRESPONDING_SOURCE_PATH):
        # Jangan berpura-pura. Kalau arsipnya tidak ada, deployment ini TIDAK
        # patuh pasal 13, dan menjawab 404 kosong menyembunyikan fakta itu dari
        # orang yang berhak menerimanya.
        return HttpResponse(
            "Arsip kode sumber tidak tersedia di deployment ini.\n\n"
            "Perangkat lunak ini berlisensi GNU AGPL-3.0-only, dan pasal 13 "
            "memberi Anda hak menerima kode sumber lengkap versi yang sedang "
            "berjalan. Laporkan alamat halaman ini kepada administrator "
            "instance agar arsipnya disediakan.\n",
            content_type="text/plain; charset=utf-8",
            status=503,
        )

    return FileResponse(
        open(CORRESPONDING_SOURCE_PATH, "rb"),
        as_attachment=True,
        filename="corresponding-source.tar.gz",
        content_type="application/gzip",
    )
