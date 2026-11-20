# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: cabang dan Direktur Cabang (P29)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Baris penempatan dengan cabang yang sudah diurai jadi divisi-divisinya.

Direktur Cabang memimpin SEMUA divisi di cabangnya, persis seperti manager
memimpin satu divisi, hanya di jenjang yang lebih tinggi. Karena itu satu baris
`JabatanOrganisasi(cabang=X, tingkat=33)` dibaca resolver sebagai satu baris
divisi `(33, None, divisi)` untuk tiap divisi hidup di cabang X. Aturan yang
sudah ada untuk baris divisi manager ke atas (`_tingkat_lokal`,
`project_penempatan`, `ditempatkan_ids`) langsung berlaku tanpa cabang baru:
jangkauan project, wewenang menyetujui, menugaskan, bawahan, dan akses privat.

Penguraian terjadi saat DIBACA, bukan disalin ke baris divisi saat ditulis.
Divisi yang dipindah masuk atau keluar cabang langsung mengubah jangkauan
direktur cabangnya (signal `Divisi` menyinkronkan ulang workspace), tanpa baris
turunan yang bisa basi.

Cabang tanpa divisi tetap menyumbang satu baris tanpa tempat, supaya jenjang
orangnya tetap terbaca 33.
"""

from plane.db.models import Divisi, JabatanOrganisasi


def divisi_per_cabang(workspace_id, cabang_ids=None) -> dict:
    """{cabang_id: [divisi_id]} untuk divisi hidup di workspace ini."""
    qs = Divisi.objects.filter(workspace_id=workspace_id, cabang_id__isnull=False)
    if cabang_ids is not None:
        qs = qs.filter(cabang_id__in=list(cabang_ids))
    hasil = {}
    for div_id, cab_id in qs.values_list("id", "cabang_id"):
        hasil.setdefault(cab_id, []).append(div_id)
    return hasil


def baris_penempatan(workspace_id, member_id=None) -> list:
    """[(member_id, tingkat, departemen_id, divisi_id)] dengan baris cabang diurai.

    Satu kueri, ditambah satu kalau ada baris cabang.
    """
    qs = JabatanOrganisasi.objects.filter(workspace_id=workspace_id)
    if member_id is not None:
        qs = qs.filter(member_id=member_id)
    mentah = list(qs.values_list("member_id", "tingkat", "departemen_id", "divisi_id", "cabang_id"))
    cabang_ids = {cab for *_, cab in mentah if cab}
    divisi = divisi_per_cabang(workspace_id, cabang_ids) if cabang_ids else {}
    hasil = []
    for uid, tingkat, dep, div, cab in mentah:
        if cab:
            hasil.extend((uid, tingkat, None, d) for d in divisi.get(cab, ()))
            if not divisi.get(cab):
                hasil.append((uid, tingkat, None, None))
        else:
            hasil.append((uid, tingkat, dep, div))
    return hasil
