# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: penemuan aturan per area
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Mengumpulkan `ATURAN` dari setiap `area_<nama>.py` di paket ini.

Tidak ada daftar modul yang harus disunting: berkas area baru ditemukan sendiri
(pindai nama modul), jadi agen yang bekerja paralel di area berbeda tidak pernah
menyentuh berkas yang sama. Kunci kembar, topik asing, atau kunci yang masih
dimiliki registri lama menggagalkan impor, bukan diam-diam menimpa.
"""

import dataclasses
import importlib
import pkgutil
from pathlib import Path

from plane.utils.aturan.grup import GRUP
from plane.utils.aturan.jenis import Rule

AWALAN_AREA = "area_"


def _modul_area() -> list[str]:
    folder = str(Path(__file__).resolve().parent)
    return sorted(m.name for m in pkgutil.iter_modules([folder]) if m.name.startswith(AWALAN_AREA))


def kumpulkan() -> dict[str, Rule]:
    """{kunci: Rule} dari semua modul area, urutan: nama modul, lalu urutan di `ATURAN`."""
    hasil: dict[str, Rule] = {}
    for nama in _modul_area():
        modul = importlib.import_module(f"plane.utils.aturan.{nama}")
        aturan = getattr(modul, "ATURAN", None)
        if not isinstance(aturan, tuple):
            raise TypeError(f"{nama}.ATURAN harus tuple Rule")
        area = nama[len(AWALAN_AREA) :]
        for rule in aturan:
            if not isinstance(rule, Rule):
                raise TypeError(f"{nama}.ATURAN berisi {rule!r}, bukan Rule")
            if rule.key in hasil:
                raise ValueError(f"Kunci aturan {rule.key} dideklarasikan dua kali ({hasil[rule.key].area}, {area})")
            if rule.group not in GRUP:
                raise ValueError(f"Aturan {rule.key}: grup {rule.group!r} tidak ada di aturan/grup.py")
            hasil[rule.key] = dataclasses.replace(rule, area=area)
    return hasil
