# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Pasang kembali workspace hasil `export_workspace` di instance lain.

    python manage.py import_workspace /tmp/acme.json.gz            # uji kering
    python manage.py import_workspace /tmp/acme.json.gz --terapkan

UJI KERING ADALAH BAWAANNYA, dan itu disengaja. Perintah ini menulis ribuan
baris ke database yang mungkin sudah berisi, dan satu-satunya cara aman
menjalankannya pertama kali adalah melihat dulu apa yang akan terjadi.

DUA PENOLAKAN YANG SENGAJA KERAS

  1. Slug workspace sudah ada di database tujuan. Menimpanya berarti mencampur
     dua organisasi yang kebetulan bernama sama.
  2. Ada surel pengguna yang sudah ada di tujuan dengan UUID BERBEDA. UUID
     dipertahankan supaya seluruh FK di ribuan baris lain tetap menunjuk ke
     orang yang benar; kalau UUID-nya bentrok, satu-satunya cara melanjutkan
     adalah memetakan ulang identitas, dan itu keputusan manusia, bukan
     keputusan skrip.

Keduanya diperiksa SEBELUM satu baris pun ditulis.
"""

import gzip
import json
from pathlib import Path

from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from plane.db.management.commands.export_workspace import _nama_aset
from plane.db.models import User, Workspace
from plane.utils.workspace_transfer import unggah_aset


class Command(BaseCommand):
    help = "Impor workspace dari berkas hasil export_workspace"

    def add_arguments(self, parser):
        parser.add_argument("berkas")
        parser.add_argument(
            "--terapkan",
            action="store_true",
            help="Tulis sungguhan. Tanpa ini hanya uji kering.",
        )
        parser.add_argument(
            "--assets",
            default=None,
            help="Tar objek penyimpanan. Bawaannya dicari bersebelahan dengan berkas baris.",
        )
        parser.add_argument(
            "--no-assets",
            action="store_true",
            help="Lewati objek penyimpanan.",
        )

    def handle(self, *args, **opsi):
        try:
            with gzip.open(opsi["berkas"], "rt", encoding="utf-8") as f:
                amplop = json.load(f)
        except OSError as e:
            raise CommandError(f"Tidak bisa membaca {opsi['berkas']}: {e}")

        if amplop.get("format") != 1:
            raise CommandError(f"Format berkas {amplop.get('format')} tidak dikenali.")

        slug = amplop["workspace_slug"]
        objek = amplop["objects"]
        terapkan = opsi["terapkan"]

        self.stdout.write("=" * 70)
        self.stdout.write(
            f"Impor workspace '{slug}'   " + ("[TERAPKAN]" if terapkan else "[UJI KERING]")
        )
        self.stdout.write("=" * 70)
        self.stdout.write(f"Diekspor  : {amplop.get('exported_at')}")
        self.stdout.write(f"Baris     : {len(objek)} dari {len(amplop.get('counts', {}))} model")
        self.stdout.write(f"Aset      : {len(amplop.get('assets', []))} objek penyimpanan")

        # --- Penolakan 1: slug sudah dipakai ---------------------------------
        if Workspace.objects.filter(slug=slug).exists():
            raise CommandError(
                f"BERHENTI. Workspace '{slug}' sudah ada di database ini. "
                "Impor tidak pernah menimpa workspace yang sudah ada."
            )

        # --- Penolakan 2: identitas bentrok ----------------------------------
        masuk = {
            o["pk"]: o["fields"].get("email")
            for o in objek
            if o["model"] == "db.user" and o["fields"].get("email")
        }
        bentrok = []
        if masuk:
            ada = User.objects.filter(email__in=list(masuk.values())).values_list("id", "email")
            per_surel = {surel: str(uid) for uid, surel in ada}
            for pk, surel in masuk.items():
                lama = per_surel.get(surel)
                if lama is not None and lama != str(pk):
                    bentrok.append(f"{surel} (di sini {lama}, di berkas {pk})")

        self.stdout.write(f"Pengguna  : {len(masuk)} di berkas, {len(bentrok)} bentrok")
        if bentrok:
            raise CommandError(
                "BERHENTI. Surel berikut sudah ada di database ini dengan UUID berbeda, "
                "jadi FK di baris lain akan menunjuk ke orang yang salah:\n  "
                + "\n  ".join(bentrok)
            )

        # Objeknya dicari bersebelahan kalau tidak disebut. Operator yang menyalin
        # satu berkas dan lupa berkas satunya adalah kejadian yang sudah pasti
        # terjadi; menemukannya sendiri lebih baik daripada menuntut diingat.
        tar_aset = None
        if not opsi["no_assets"]:
            calon = Path(opsi["assets"]) if opsi["assets"] else _nama_aset(opsi["berkas"])
            if Path(calon).exists():
                tar_aset = Path(calon)
            elif amplop.get("assets"):
                raise CommandError(
                    f"BERHENTI. Berkas ini menyebut {len(amplop['assets'])} objek "
                    f"penyimpanan, tapi {calon} tidak ada. "
                    "Salin berkas objeknya juga, atau jalankan dengan --no-assets kalau "
                    "memang sengaja tidak ikut."
                )
        self.stdout.write(f"Objek     : {tar_aset if tar_aset else 'tidak ikut'}")

        if not terapkan:
            self.stdout.write("")
            for label, n in sorted(
                amplop.get("counts", {}).items(), key=lambda x: -x[1]
            )[:10]:
                self.stdout.write(f"    {n:>8}  {label}")
            self.stdout.write("")
            self.stdout.write("UJI KERING, tidak ada yang ditulis.")
            self.stdout.write("Jalankan ulang dengan --terapkan untuk menerapkan.")
            return

        # --- Objek DULU, baru baris -------------------------------------------
        #
        # Urutannya disengaja. Kalau unggahan objek gagal di tengah, tidak ada
        # satu baris pun yang tertulis dan instance ini tetap bersih. Kalau
        # urutannya dibalik, kegagalan unggah meninggalkan baris yang terlihat
        # utuh dengan berkas yang tidak akan pernah terbuka, dan itu baru
        # ketahuan oleh pemakainya.
        #
        # Objek tanpa baris tidak berbahaya: ia tidak terlihat di mana pun.
        if tar_aset is not None:
            self.stdout.write(f"Mengunggah objek dari {tar_aset} ...")
            hasil = unggah_aset(str(tar_aset), log=self.stdout.write)
            self.stdout.write(f"  {hasil['diunggah']} objek terunggah")

        # --- Penulisan -------------------------------------------------------
        #
        # Pemeriksaan constraint DITUNDA selama transaksi ini. Tanpa itu urutan
        # penulisan harus tepat secara topologis, dan itu mustahil dijamin untuk
        # 127 model dengan rujukan melingkar seperti Page.parent yang menunjuk
        # dirinya sendiri. Django menyatakan FK-nya DEFERRABLE, jadi seluruh
        # pemeriksaan tetap terjadi, hanya di akhir transaksi.
        ditulis = 0
        with transaction.atomic():
            with connection.constraint_checks_disabled():
                for obj in serializers.deserialize("python", objek):
                    # `save()` milik DeserializedObject, bukan milik model, jadi
                    # BaseModel.save() tidak ikut jalan dan created_by tidak akan
                    # ditolkan seperti yang terjadi di shell dan Celery.
                    obj.save()
                    ditulis += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"SELESAI. {ditulis} baris ditulis."))
        if amplop.get("assets") and tar_aset is None:
            self.stdout.write(
                self.style.WARNING(
                    f"  {len(amplop['assets'])} objek penyimpanan TIDAK ikut karena "
                    "--no-assets. Instance ini belum siap diserahkan: berkasnya akan "
                    "muncul di daftar tanpa bisa dibuka."
                )
            )
