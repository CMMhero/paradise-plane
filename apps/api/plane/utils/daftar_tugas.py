# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: bentuk bersama daftar tugas dan ekspornya
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from dataclasses import dataclass

from django.db.models import QuerySet


@dataclass(frozen=True)
class DaftarTugas:
    """Cakupan, saringan, dan urutan satu daftar tugas.

    Endpoint daftar dan ekspor Excel membaca hasil method `susun_daftar` yang sama,
    jadi ekspor tidak bisa menyimpang dari daftarnya.
    """

    tersaring: QuerySet
    """Baris yang lolos, tanpa anotasi. Untuk hitungan dan nilai grup."""
    terurut: QuerySet
    """Baris yang sama dengan anotasi daftar dan anotasi urutan."""
    urutan: str
    """Kunci urutan untuk paginator (`-` di depan berarti menurun)."""
    filters: dict
    """Saringan lama (`issue_filters`) yang dipakai."""
