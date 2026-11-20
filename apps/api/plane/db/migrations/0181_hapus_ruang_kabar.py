# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: hapus ruang kabar "Paradise"
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Hapus permanen setiap ruang kabar pribadi `kabar:<user_id>` beserta isinya.

Permintaan user (program 2.9): ruang "Paradise" tidak dipakai lagi, kartu yang
dulu masuk ke sana kini tidak dikirim ke obrolan sama sekali, dan isinya boleh
dihapus.

Yang ikut terhapus, dari yang paling dalam: reaksi pesan (CASCADE), lampiran
obrolan (`FileAsset` CHAT_ATTACHMENT, terikat lewat `entity_identifier` tanpa FK),
pesan, langganan, lalu ruangnya. Sematan dan penanda baca adalah kolom di pesan
dan langganan, jadi ikut terhapus bersama barisnya.

Berbatch dan tidak atomik: tiap batch di-commit sendiri, jadi tabel besar tidak
menahan satu transaksi raksasa, dan migrasi yang terputus cukup dijalankan ulang
untuk melanjutkan. `_base_manager` dipakai supaya baris yang sudah dihapus lunak
ikut hilang dan penghapusannya permanen, baik dengan model historis maupun model
asli (uji memanggil fungsi ini langsung). Mundur = tidak melakukan apa pun.
"""

from django.db import migrations

AWALAN_KABAR = "kabar:"
BATCH_RUANG = 200
BATCH_PESAN = 2000
LAMPIRAN_OBROLAN = "CHAT_ATTACHMENT"


def hapus_ruang_kabar(apps, schema_editor):
    Ruang = apps.get_model("db", "Ruang")
    PesanLangsung = apps.get_model("db", "PesanLangsung")
    Langganan = apps.get_model("db", "Langganan")
    FileAsset = apps.get_model("db", "FileAsset")

    while True:
        ruang_ids = list(
            Ruang._base_manager.filter(kunci_sistem__startswith=AWALAN_KABAR).values_list("id", flat=True)[:BATCH_RUANG]
        )
        if not ruang_ids:
            return
        while True:
            pesan_ids = list(
                PesanLangsung._base_manager.filter(ruang_id__in=ruang_ids).values_list("id", flat=True)[:BATCH_PESAN]
            )
            if not pesan_ids:
                break
            FileAsset._base_manager.filter(
                entity_type=LAMPIRAN_OBROLAN, entity_identifier__in=[str(i) for i in pesan_ids]
            ).delete()
            PesanLangsung._base_manager.filter(id__in=pesan_ids).delete()
        Langganan._base_manager.filter(ruang_id__in=ruang_ids).delete()
        Ruang._base_manager.filter(id__in=ruang_ids).delete()


class Migration(migrations.Migration):
    atomic = False

    dependencies = [("db", "0180_kanal_penulis")]

    operations = [migrations.RunPython(hapus_ruang_kabar, migrations.RunPython.noop)]
