# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: registri aturan God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu registri bertipe untuk setiap aturan yang diatur Super Admin di God Mode.

Cara pakai (lihat paradise/aturan-godmode.md untuk langkah lengkap):

    from plane.utils import aturan

    if aturan.get_bool("SOME_RULE"): ...
    ambang = aturan.get_int("APPROVER_MIN_LEVEL")

Aturan DIDEKLARASIKAN di `area_<nama>.py` (tuple `ATURAN`) dan ditemukan sendiri,
jadi menambah aturan tidak pernah menyunting berkas ini. Nilainya tersimpan di
`InstanceConfiguration` dengan kunci yang sama (atau di PARADISE_BAWAAN_MEMBER
untuk bawaan tampilan), diubah lewat /api/instances/rules/ dengan audit.

Registri lama (`SAKLAR_BAWAAN`, `SETELAN_ANGKA`/`SETELAN_PILIHAN`, `SETELAN_TEKS`)
tetap berdiri sendiri dengan pembaca lamanya; layar God Mode menampilkannya lewat
adaptor baca-saja (`daftar_lama`). Satu kunci tidak boleh ada di dua registri.
"""

from plane.utils.aturan.baca import (
    CACHE_DETIK,
    efektif,
    get,
    get_bool,
    get_choice,
    get_int,
    get_list,
    segarkan,
)
from plane.utils.aturan.grup import GRUP
from plane.utils.aturan.jenis import (
    BOOL,
    CHOICE,
    INT,
    KEY_LIST,
    LEVEL,
    LIVE,
    NEXT_RUN,
    RESTART,
    TEXT,
    NilaiTidakSah,
    Rule,
    ke_json,
    ke_teks,
    normalkan,
)
from plane.utils.aturan.registri import kumpulkan


def _pastikan_tidak_bentrok(registri: dict) -> None:
    from plane.utils.setelan_instance import dikenal

    bentrok = sorted(k for k in registri if dikenal(k) or k == "PARADISE_BAWAAN_MEMBER")
    if bentrok:
        raise ValueError(f"Kunci aturan sudah dimiliki registri lama: {', '.join(bentrok)}")


REGISTRI: dict[str, Rule] = kumpulkan()
_pastikan_tidak_bentrok(REGISTRI)

__all__ = [
    "BOOL",
    "CACHE_DETIK",
    "CHOICE",
    "GRUP",
    "INT",
    "KEY_LIST",
    "LEVEL",
    "LIVE",
    "NEXT_RUN",
    "REGISTRI",
    "RESTART",
    "TEXT",
    "NilaiTidakSah",
    "Rule",
    "efektif",
    "get",
    "get_bool",
    "get_choice",
    "get_int",
    "get_list",
    "ke_json",
    "ke_teks",
    "normalkan",
    "segarkan",
]
