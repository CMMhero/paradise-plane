# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: peran per tempat (KEP-93)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# KEP-93 (5 Nov 2026): tidak ada "manager departemen". Baris departemen membawa
# PERAN orang itu di departemen tersebut (Staf/Supervisor). Untuk tiap manager
# (jenjang 30, bukan direktur) yang punya baris departemen:
#
# - departemen di dalam divisi yang ia pimpin: barisnya dicabut (divisinya sudah
#   menjangkau departemen itu, baris ini cuma "manager departemen");
# - departemen di divisi lain: perannya jadi Supervisor (jenjang terdekat yang
#   ada di departemen, dan yang tidak mengurangi wewenangnya atas staf di sana);
# - manager tanpa divisi: jenjang Manager-nya dipindah ke satu baris tanpa tempat,
#   supaya turunnya baris departemen tidak menurunkan orangnya.
#
# Akses project tidak perlu disinkron ulang: Supervisor dan Manager sama-sama
# role 20, dan departemen yang dicabut tetap dijangkau lewat divisinya.

from django.db import migrations
from django.utils import timezone

MANAGER = 30
DIREKTUR = 40
SUPERVISOR = 20


def maju(apps, schema_editor):
    Jabatan = apps.get_model("db", "JabatanOrganisasi")
    Departemen = apps.get_model("db", "Departemen")
    induk = dict(Departemen.objects.values_list("id", "divisi_id"))
    kini = timezone.now()

    per_orang = {}
    for b in Jabatan.objects.filter(deleted_at__isnull=True):
        per_orang.setdefault((b.workspace_id, b.member_id), []).append(b)

    for (workspace_id, member_id), baris in per_orang.items():
        puncak = max(b.tingkat for b in baris)
        if not (MANAGER <= puncak < DIREKTUR):
            continue
        dep_baris = [b for b in baris if b.departemen_id]
        if not dep_baris:
            continue
        divisi = {b.divisi_id for b in baris if b.divisi_id}
        for b in dep_baris:
            if induk.get(b.departemen_id) in divisi:
                Jabatan.objects.filter(pk=b.pk).update(deleted_at=kini, updated_at=kini)
            elif b.tingkat > SUPERVISOR:
                Jabatan.objects.filter(pk=b.pk).update(tingkat=SUPERVISOR, updated_at=kini)
        tanpa_tempat = [b for b in baris if not b.departemen_id and not b.divisi_id]
        if divisi:
            continue
        if tanpa_tempat:
            Jabatan.objects.filter(pk=tanpa_tempat[0].pk).update(tingkat=puncak, updated_at=kini)
        else:
            Jabatan.objects.create(
                workspace_id=workspace_id,
                member_id=member_id,
                tingkat=puncak,
                sumber="kep-93",
                catatan="Jenjang manager dipindah dari baris departemen (KEP-93).",
            )


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0168_selaraskan_pilihan_zona_waktu"),
    ]

    operations = [
        migrations.RunPython(maju, migrations.RunPython.noop),
    ]
