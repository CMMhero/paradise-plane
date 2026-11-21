# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: menulis aturan God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Menulis dan mengembalikan nilai aturan. Dipanggil HANYA dari endpoint
/api/instances/rules/ (yang memeriksa frasa dan mencatat audit)."""

from django.db import transaction

from plane.utils.aturan.baca import _ambil, efektif, segarkan
from plane.utils.aturan.jenis import TINGGI, NilaiTidakSah, Rule, ke_json, ke_teks, normalkan

KATEGORI = "PARADISE"


def _registri() -> dict[str, Rule]:
    from plane.utils.aturan import REGISTRI

    return REGISTRI


def validasi(nilai: dict) -> tuple[dict, dict]:
    """({kunci: nilai kanonik}, {kunci: pesan galat}) untuk badan PATCH."""
    from plane.utils.setelan_instance import dikenal

    baru, galat = {}, {}
    for kunci, mentah in nilai.items():
        rule = _registri().get(kunci)
        if rule is None:
            galat[kunci] = "This setting is changed on its own tab." if dikenal(kunci) else "Unknown rule."
            continue
        try:
            baru[kunci] = normalkan(rule, mentah)
        except NilaiTidakSah as e:
            galat[kunci] = str(e)
    return baru, galat


def perubahan(baru: dict) -> list[tuple[Rule, object, object]]:
    """[(rule, lama, baru)] yang BENAR-BENAR berubah dibanding nilai yang berlaku (dibaca segar)."""
    baris = _ambil()
    hasil = []
    for kunci, nilai in baru.items():
        rule = _registri()[kunci]
        lama = efektif(rule, baris)
        if lama != nilai:
            hasil.append((rule, lama, nilai))
    return hasil


def butuh_frasa(daftar: list) -> list[str]:
    """Kunci berisiko tinggi di antara perubahan: hanya boleh dengan frasa konfirmasi."""
    return sorted(rule.key for rule, _, _ in daftar if rule.risk == TINGGI)


def _tulis_bawaan_member(isi: dict) -> None:
    """{rule: nilai} ke PARADISE_BAWAAN_MEMBER lewat pembaca/penulisnya sendiri."""
    if not isi:
        return
    from plane.utils.bawaan_member import baca_bawaan, simpan_bawaan

    bawaan = baca_bawaan()
    for rule, nilai in isi.items():
        bagian, kolom = rule.member_default.split(".")
        bawaan.setdefault(bagian, {})[kolom] = ke_json(rule, nilai)
    simpan_bawaan(bawaan)


def terapkan(daftar: list, kembalikan: bool = False, catat=None) -> None:
    """Tulis setiap (rule, lama, baru) dalam satu transaksi, lalu `catat(rule, lama, baru, pk)`.

    `kembalikan=True` (Reset to default): baris InstanceConfiguration dihapus,
    jadi aturan ikut `default` kode termasuk kalau default itu kelak berubah.
    """
    from plane.license.models import InstanceConfiguration

    with transaction.atomic():
        bawaan_member = {}
        for rule, lama, baru in daftar:
            pk = rule.key
            if rule.disimpan_di_bawaan_member:
                bawaan_member[rule] = baru
            elif kembalikan:
                # Hapus sungguhan: baris soft-delete tetap memegang kunci unik `key`.
                InstanceConfiguration.objects.filter(key=rule.key).delete(soft=False)
            else:
                baris, _ = InstanceConfiguration.objects.get_or_create(
                    key=rule.key, defaults={"category": KATEGORI, "is_encrypted": False}
                )
                baris.value = ke_teks(rule, baru)
                baris.save(update_fields=["value", "updated_at"])
                pk = str(baris.pk)
            if catat is not None:
                catat(rule, lama, baru, pk)
        _tulis_bawaan_member(bawaan_member)
    segarkan()
