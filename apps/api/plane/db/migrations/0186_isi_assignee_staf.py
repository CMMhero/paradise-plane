# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: isi assignee tugas buatan staf (2.11)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tugas buatan staf yang belum punya assignee diberi assignee: pembuatnya.

Keputusan product owner. Aturan pilih lengkap ada di `plane.utils.isi_assignee_staf`.
Tidak atomik dan idempoten: tiap batch di-commit sendiri, menjalankannya ulang
tidak menambah apa pun. Mundur = tidak melakukan apa pun (baris yang sudah
terisi tidak bisa dibedakan dari yang diisi pengguna).
"""

from django.db import migrations

from plane.utils.isi_assignee_staf import isi_assignee_staf, ringkas

# Satu-satunya tempat yang diubah saat digabung dengan cabang yang membawa 0185.
MIGRASI_SEBELUMNYA = "0184_cabang"


def _isi(apps, schema_editor):
    hasil = isi_assignee_staf(apps.get_model, apply=True)
    print(f"\n  isi_assignee_staf: {ringkas(hasil)}")


class Migration(migrations.Migration):
    atomic = False

    dependencies = [("db", MIGRASI_SEBELUMNYA)]

    operations = [migrations.RunPython(_isi, migrations.RunPython.noop)]
