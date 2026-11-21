# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: bentuk API aturan God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Bentuk JSON registri untuk GET /api/instances/rules/ dan `paradise_rules`
di /api/instances/, plus adaptor baca-saja atas registri lama."""

from plane.utils.aturan.baca import _ambil, efektif
from plane.utils.aturan.grup import GRUP
from plane.utils.aturan.jenis import TINGGI, Rule, ke_json

SUMBER_REGISTRI = "registry"
SUMBER_LAMA = "legacy"


def _registri() -> dict[str, Rule]:
    from plane.utils.aturan import REGISTRI

    return REGISTRI


def deskripsi(rule: Rule, baris: dict) -> dict:
    """Satu butir `rules` untuk aturan registri."""
    nilai = efektif(rule, baris)
    return {
        "key": rule.key,
        "source": SUMBER_REGISTRI,
        "kind": rule.kind,
        "value": ke_json(rule, nilai),
        "default": ke_json(rule, rule.default),
        "changed": nilai != rule.default,
        "label": rule.label,
        "help": rule.help,
        "group": rule.group,
        "area": rule.area,
        "risk": rule.risk,
        "applies": rule.applies,
        "web": rule.web,
        "kep": rule.kep,
        "min": rule.min,
        "max": rule.max,
        "max_length": rule.max_length,
        "choices": [{"value": v, "label": lbl} for v, lbl in rule.choices] or None,
        "ordered": rule.ordered,
        "store": "member_default" if rule.disimpan_di_bawaan_member else "instance",
        # Bagian untuk POST /api/instances/members/defaults/apply/ ("Apply to existing members").
        "apply_section": rule.member_default.split(".")[0] if rule.disimpan_di_bawaan_member else None,
    }


def daftar_lama() -> list:
    """Setelan registri lama (/api/instances/settings/), baca-saja di layar Rules.

    Diubah tetap di tab masing-masing; di sini hanya supaya satu layar menunjukkan
    SEMUA aturan dan mana yang sudah bergeser dari bawaan.
    """
    from plane.utils.setelan_instance import daftar_setelan

    hasil = []
    for d in daftar_setelan():
        hasil.append(
            {
                "key": d["key"],
                "source": SUMBER_LAMA,
                "kind": d["kind"],
                "value": d["value"],
                "default": d["default"],
                "changed": d["value"] != d["default"],
                "label": None,
                "help": None,
                "group": None,
                "area": None,
                "risk": TINGGI if d["sensitive"] else "low",
                "applies": None,
                "web": False,
                "kep": None,
                "min": d["min"],
                "max": d["max"],
                "max_length": None,
                "choices": [{"value": v, "label": str(v)} for v in d["choices"]] if d["choices"] else None,
                "ordered": False,
                "store": "instance",
                "apply_section": None,
            }
        )
    return hasil


def daftar_aturan(dengan_lama: bool = True) -> dict:
    """Balasan GET /api/instances/rules/. Selalu dibaca segar, bukan dari potret."""
    from plane.utils.setelan_instance import FRASA_KONFIRMASI

    baris = _ambil()
    aturan = [deskripsi(r, baris) for r in _registri().values()]
    return {
        "groups": [{"id": gid, "label": label, "description": ket} for gid, (label, ket) in GRUP.items()],
        "rules": aturan + (daftar_lama() if dengan_lama else []),
        "confirm_phrase": FRASA_KONFIRMASI,
    }


def nilai_web() -> dict:
    """`paradise_rules` di /api/instances/: hanya aturan `web=True`, nilai saja."""
    return {r.key: ke_json(r, efektif(r)) for r in _registri().values() if r.web}
