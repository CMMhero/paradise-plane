# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pembaca aturan God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Membaca nilai aturan yang berlaku, dengan cache per proses yang pendek.

Kenapa cache per proses, bukan cache Redis atau kueri per panggilan:

- Aturan dibaca di jalur panas (`calon_penyetuju` dipanggil per calon, per baris
  antrean). `saklar_aktif` lama = satu kueri per panggilan; Redis tetap satu
  perjalanan jaringan per panggilan. Potret di memori = nol perjalanan.
- Satu kueri mengambil SEMUA baris registri sekaligus, jadi membaca sepuluh aturan
  dalam satu permintaan tetap satu kueri.
- Harga: proses lain (worker gunicorn lain, Celery) melihat perubahan paling
  lambat CACHE_DETIK kemudian. Proses yang menulis (endpoint God Mode) langsung
  membuang potretnya lewat sinyal `post_save`/`post_delete` InstanceConfiguration,
  jadi "applies: live" = berlaku dalam 5 detik di setiap proses.

Nilai rusak di database (ditulis tangan, versi lama) jatuh ke `default`, tidak
pernah melempar galat: task Celery tidak boleh mati karena satu baris aneh.
"""

import json
import logging
import time

from django.db.models.signals import post_delete, post_save

from plane.utils.aturan.jenis import BOOL, CHOICE, INT, KEY_LIST, LEVEL, NilaiTidakSah, Rule, normalkan

logger = logging.getLogger("plane.api")

CACHE_DETIK = 5.0
KUNCI_BAWAAN_MEMBER = "PARADISE_BAWAAN_MEMBER"

_potret: tuple[float, dict] | None = None


def segarkan(*args, **kwargs) -> None:
    """Buang potret proses ini. Juga dipakai sebagai penerima sinyal."""
    global _potret
    _potret = None


# Pengirim malas ("app_label.Model"): modul ini boleh dimuat sebelum app siap.
post_save.connect(segarkan, sender="license.InstanceConfiguration", dispatch_uid="aturan_segarkan_simpan")
post_delete.connect(segarkan, sender="license.InstanceConfiguration", dispatch_uid="aturan_segarkan_hapus")


def _registri() -> dict[str, Rule]:
    from plane.utils.aturan import REGISTRI

    return REGISTRI


def _kunci_tersimpan() -> list[str]:
    kunci = [r.key for r in _registri().values() if not r.disimpan_di_bawaan_member]
    if any(r.disimpan_di_bawaan_member for r in _registri().values()):
        kunci.append(KUNCI_BAWAAN_MEMBER)
    return kunci


def _ambil() -> dict:
    """{kunci: teks mentah} + {"__bawaan_member__": dict}, satu kueri.

    Tidak melihat SKIP_ENV_VAR: aturan registri ini tidak punya env sama sekali
    (KEP-48), jadi database satu-satunya sumber selain `default`.
    """
    from plane.license.models import InstanceConfiguration

    baris = dict(InstanceConfiguration.objects.filter(key__in=_kunci_tersimpan()).values_list("key", "value"))
    bawaan_member = {}
    mentah = baris.pop(KUNCI_BAWAAN_MEMBER, None)
    if mentah:
        try:
            bawaan_member = json.loads(mentah)
        except (TypeError, ValueError):
            logger.warning("%s bukan JSON sah; aturan bawaan member memakai default", KUNCI_BAWAAN_MEMBER)
    baris["__bawaan_member__"] = bawaan_member if isinstance(bawaan_member, dict) else {}
    return baris


def _baris() -> dict:
    global _potret
    sekarang = time.monotonic()
    potret = _potret
    if potret is not None and sekarang - potret[0] < CACHE_DETIK:
        return potret[1]
    isi = _ambil()
    _potret = (sekarang, isi)
    return isi


def _mentah(rule: Rule, baris: dict):
    """Nilai tersimpan `rule` sebelum divalidasi, atau None kalau belum pernah diatur."""
    if rule.disimpan_di_bawaan_member:
        bagian, kolom = rule.member_default.split(".")
        isi = baris["__bawaan_member__"].get(bagian)
        return isi.get(kolom) if isinstance(isi, dict) else None
    return baris.get(rule.key)


def efektif(rule: Rule, baris: dict | None = None):
    """Nilai kanonik yang berlaku untuk `rule`. `baris` = potret yang sudah diambil."""
    mentah = _mentah(rule, _baris() if baris is None else baris)
    if mentah is None or mentah == "":
        return rule.default
    try:
        return normalkan(rule, mentah)
    except NilaiTidakSah:
        logger.warning("Nilai aturan %s rusak (%r); memakai default", rule.key, mentah)
        return rule.default


def get(kunci: str):
    """Nilai aturan `kunci` yang berlaku. Kunci tak terdaftar adalah bug: KeyError."""
    return efektif(_registri()[kunci])


def _dengan_jenis(kunci: str, jenis: tuple):
    rule = _registri()[kunci]
    if rule.kind not in jenis:
        raise TypeError(f"Aturan {kunci} berjenis {rule.kind}, bukan {'/'.join(jenis)}")
    return efektif(rule)


def get_bool(kunci: str) -> bool:
    return _dengan_jenis(kunci, (BOOL,))


def get_int(kunci: str) -> int:
    """Untuk `int` dan `level` (jenjang juga angka)."""
    return _dengan_jenis(kunci, (INT, LEVEL))


def get_choice(kunci: str):
    return _dengan_jenis(kunci, (CHOICE, LEVEL))


def get_list(kunci: str) -> tuple:
    return _dengan_jenis(kunci, (KEY_LIST,))
