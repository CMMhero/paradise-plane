# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: mengindeks isi materi Wiki yang sudah ada
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.core.management.base import BaseCommand

from plane.bgtasks.wiki_indeks_task import indeks_satu
from plane.db.models import WikiMaterial
from plane.utils.exception_logger import log_exception


class Command(BaseCommand):
    help = (
        "Baca isi materi Wiki yang belum diindeks supaya bisa dicari. Dijalankan sekali "
        "sesudah migrasi 0172; materi baru diindeks otomatis saat diunggah."
    )

    def add_arguments(self, parser):
        parser.add_argument("--semua", action="store_true", help="Indeks ulang juga yang sudah pernah diindeks.")
        parser.add_argument("--workspace", help="Batasi ke satu workspace (slug).")

    def handle(self, *args, **opsi):
        materi = WikiMaterial.objects.filter(berkas__is_uploaded=True, berkas__is_deleted=False)
        if not opsi["semua"]:
            materi = materi.filter(diindeks_pada__isnull=True)
        if opsi["workspace"]:
            materi = materi.filter(workspace__slug=opsi["workspace"])
        materi = materi.select_related("berkas", "pratinjau").order_by("created_at")

        selesai = gagal = dilewati = 0
        for m in materi.iterator(chunk_size=50):
            try:
                if indeks_satu(m):
                    selesai += 1
                else:
                    dilewati += 1  # menunggu konversi PDF
            except Exception as e:  # noqa: BLE001 - satu berkas rusak tidak menghentikan sisanya
                gagal += 1
                log_exception(e)
        self.stdout.write(self.style.SUCCESS(f"Diindeks {selesai}, menunggu konversi {dilewati}, gagal {gagal}."))
