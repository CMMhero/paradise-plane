# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Bungkus satu workspace jadi satu berkas, untuk dipindahkan ke instance lain.

    python manage.py export_workspace acme --out /tmp/acme.json.gz

Yang dihasilkan berisi barisnya, BUKAN berkasnya. Objek penyimpanan disebutkan
di bagian `assets` sebagai daftar kunci, dan penyalinannya dikerjakan operator
dengan alat penyimpanan biasa. Lihat plane/utils/workspace_transfer.py.
"""

import gzip
import json
from pathlib import Path

from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from plane.db.models import Workspace
from plane.utils.workspace_transfer import klasifikasi, kumpulkan, manifes_aset, unduh_aset

FORMAT = 1


def _nama_aset(keluar):
    """`acme.json.gz` -> `acme-assets.tar.gz`, bersebelahan supaya tidak terpisah.

    Dua berkas hasil satu perintah yang namanya tidak berhubungan adalah dua
    berkas yang suatu saat dipindahkan sendiri-sendiri, dan yang tertinggal
    selalu yang besar.
    """
    p = Path(keluar)
    nama = p.name
    for akhiran in (".json.gz", ".json", ".gz"):
        if nama.endswith(akhiran):
            nama = nama[: -len(akhiran)]
            break
    return str(p.with_name(nama + "-assets.tar.gz"))


class Command(BaseCommand):
    help = "Ekspor satu workspace beserta seluruh barisnya ke satu berkas"

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("--out", required=True, help="Tujuan berkas .json.gz")
        parser.add_argument(
            "--assets",
            default=None,
            help="Tujuan tar objek penyimpanan. Bawaannya diturunkan dari --out.",
        )
        parser.add_argument(
            "--no-assets",
            action="store_true",
            help="Lewati objek penyimpanan, hasilkan barisnya saja.",
        )

    def handle(self, *args, **opsi):
        workspace = Workspace.objects.filter(
            slug=opsi["slug"], deleted_at__isnull=True
        ).first()
        if workspace is None:
            raise CommandError(f"Workspace '{opsi['slug']}' tidak ada.")

        kelas = klasifikasi()
        if kelas["tidak_dikenal"]:
            raise CommandError(
                "Ada model yang belum diputuskan nasibnya: "
                + ", ".join(kelas["tidak_dikenal"])
            )

        objek = []
        jumlah = {}
        for label, qs in kumpulkan(workspace):
            # `.iterator()` sengaja TIDAK dipakai: serializer butuh melihat
            # querysetnya utuh dan workspace gratis memang kecil. Batas atas yang
            # diketahui: workspace raksasa akan memuat seluruh barisnya ke memori
            # sekaligus. Kalau itu jadi masalah, potong per model di sini, bukan
            # di pemanggil.
            baris = serializers.serialize("python", qs)
            if baris:
                objek.extend(baris)
                jumlah[label] = len(baris)

        aset = manifes_aset(workspace)
        amplop = {
            "format": FORMAT,
            "workspace_slug": workspace.slug,
            "workspace_name": workspace.name,
            "workspace_id": str(workspace.id),
            "exported_at": timezone.now().isoformat(),
            "counts": jumlah,
            "assets": aset,
            "objects": objek,
        }

        with gzip.open(opsi["out"], "wt", encoding="utf-8") as f:
            json.dump(amplop, f, default=str)

        self.stdout.write(f"Workspace : {workspace.slug} ({workspace.name})")
        self.stdout.write(f"Model     : {len(jumlah)} berisi, {sum(jumlah.values())} baris")
        self.stdout.write(f"Aset      : {len(aset)} objek penyimpanan DISEBUT, tidak disalin")
        self.stdout.write(f"Berkas    : {opsi['out']}")
        if aset and not opsi["no_assets"]:
            # Objeknya ikut diunduh secara BAWAAN, bukan lewat saklar opsional.
            # Ekspor yang secara bawaan menghasilkan setengah pemindahan adalah
            # ekspor yang setengahnya akan terlupa, dan yang terlupa itu justru
            # bagian yang baru ketahuan oleh pemakai akhir.
            tujuan_aset = Path(opsi["assets"] or _nama_aset(opsi["out"]))
            self.stdout.write("")
            self.stdout.write(f"Mengunduh {len(aset)} objek penyimpanan ke {tujuan_aset} ...")
            hasil = unduh_aset(aset, str(tujuan_aset), log=self.stdout.write)
            self.stdout.write(
                f"  {hasil['disalin']} objek, {hasil['bytes'] / (1024 * 1024):.1f} MiB"
            )
            if hasil["hilang"]:
                self.stdout.write(
                    self.style.WARNING(
                        f"  {len(hasil['hilang'])} objek hilang di penyimpanan asal dan "
                        "TIDAK ikut. Barisnya tetap ikut, jadi di tujuan ia akan muncul "
                        "di daftar tanpa bisa dibuka. Periksa sebelum menyerahkan."
                    )
                )
        elif aset:
            self.stdout.write(
                self.style.WARNING(
                    f"  --no-assets: {len(aset)} objek TIDAK ikut. Pemindahan ini belum utuh."
                )
            )
        for label, n in sorted(jumlah.items(), key=lambda x: -x[1])[:10]:
            self.stdout.write(f"    {n:>8}  {label}")
