# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: bentuk aturan God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""`Rule`, jenisnya, dan validatornya. Python murni: tanpa Django, tanpa model.

Modul area (`area_<nama>.py`) hanya mengimpor berkas ini, jadi registri bisa
dimuat sebelum app Django siap (serializer mengimpor pembacanya lebih awal).

Bentuk nilai:

    jenis         nilai di Python / JSON        disimpan di InstanceConfiguration
    bool          True / False                  "1" / "0"
    int           bilangan bulat, min..max      "20"
    choice        salah satu `choices` (str/int) "archives"
    text          str, panjang <= max_length    apa adanya
    level         jenjang TINGKAT di `choices`  "20"
    list_of_keys  tuple str dari `choices`      "a,b" (urutan `choices`, unik)
                  `ordered=True`: urutan isian dipertahankan (urutan = nilainya)
"""

import re
from dataclasses import dataclass, field
from typing import Any

BOOL = "bool"
INT = "int"
CHOICE = "choice"
TEXT = "text"
LEVEL = "level"
KEY_LIST = "list_of_keys"
JENIS = (BOOL, INT, CHOICE, TEXT, LEVEL, KEY_LIST)

RISIKO = ("low", "medium", "high")
RENDAH, SEDANG, TINGGI = RISIKO

# Kapan perubahan terasa. `live` = dalam CACHE_DETIK di setiap proses (lihat baca.py).
LIVE = "live"
NEXT_RUN = "next_run"
RESTART = "restart"
BERLAKU = (LIVE, NEXT_RUN, RESTART)

# Cermin TINGKAT_CHOICES di plane/db/models/hierarki.py; test_aturan_registri.py
# mencocokkannya. Disalin, bukan diimpor: berkas ini tidak boleh memuat model.
NAMA_TINGKAT = {
    10: "Member",
    12: "Leader",
    20: "Supervisor",
    25: "Assistant manager",
    30: "Manager",
    33: "Branch manager",
    35: "Secretary",
    40: "Director",
}

TEKS_MAKS_BAWAAN = 200
_POLA_KUNCI = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$")
# Bagian PARADISE_BAWAAN_MEMBER yang boleh diisi registri ini. `tampilan` seluruhnya
# dibangun dari registri (bawaan_member.PABRIK["tampilan"]); `work_items` memegang
# `layout` yang ditulis tangan, kolom lainnya dari registri. Bagian lain tetap tangan.
BAGIAN_TAMPILAN = "tampilan"
BAGIAN_WORK_ITEMS = "work_items"
BAGIAN_MEMBER = (BAGIAN_TAMPILAN, BAGIAN_WORK_ITEMS)
_POLA_JALUR = re.compile(rf"^({'|'.join(BAGIAN_MEMBER)})\.[a-z_]+$")


class NilaiTidakSah(ValueError):
    """Nilai aturan ditolak. `str(e)` = pesan untuk God Mode (bahasa Inggris, KEP-46)."""


@dataclass(frozen=True)
class Rule:
    """Satu aturan God Mode. Dideklarasikan di `area_<nama>.py`, tuple `ATURAN`.

    `default` WAJIB sama dengan perilaku sebelum aturannya ada. `area` diisi
    penemuan modul (nama berkasnya), jangan diisi tangan.

    `member_default="tampilan.<kolom>"` (atau `work_items.<kolom>`): nilainya bukan
    baris sendiri, melainkan kolom di PARADISE_BAWAAN_MEMBER (God Mode > People > New member defaults),
    berlaku untuk akun baru dan bisa diterapkan ke semua akun lewat tombol
    "Apply to existing members". `profile_theme_key` + `profile_values` = kunci
    `Profile.theme` yang diisi dan petanya dari nilai aturan.
    """

    key: str
    kind: str
    default: Any
    group: str
    label: str
    help: str
    risk: str
    applies: str = LIVE
    web: bool = False
    kep: str | None = None
    min: int | None = None
    max: int | None = None
    max_length: int | None = None
    # (nilai, label). Untuk `level` boleh angka jenjang saja; labelnya dari NAMA_TINGKAT.
    choices: tuple = ()
    member_default: str | None = None
    profile_theme_key: str | None = None
    # Dict tidak bisa di-hash; Rule dipakai sebagai kunci dict (bawaan_member.nilai_tampilan).
    profile_values: dict | None = field(default=None, hash=False)
    # Hanya list_of_keys: urutan isian bagian dari nilai (mis. urutan widget Home).
    ordered: bool = False
    area: str = field(default="", compare=False)

    def __post_init__(self):
        if self.kind == LEVEL:
            object.__setattr__(
                self,
                "choices",
                tuple(
                    c if isinstance(c, tuple) else (c, f"{NAMA_TINGKAT.get(c, 'Level')} ({c})") for c in self.choices
                ),
            )
        else:
            object.__setattr__(self, "choices", tuple(self.choices))
        if self.kind == KEY_LIST and isinstance(self.default, list):
            object.__setattr__(self, "default", tuple(self.default))
        masalah = periksa_deklarasi(self)
        if masalah:
            raise ValueError(f"Aturan {self.key!r} tidak sah: {masalah}")

    @property
    def nilai_pilihan(self) -> tuple:
        return tuple(v for v, _ in self.choices)

    @property
    def disimpan_di_bawaan_member(self) -> bool:
        return self.member_default is not None


def periksa_deklarasi(rule: Rule) -> str | None:
    """Alasan deklarasi `rule` tidak sah, atau None. Dipanggil saat Rule dibuat."""
    if not isinstance(rule.key, str) or not _POLA_KUNCI.match(rule.key):
        return "key harus UPPER_SNAKE"
    if rule.kind not in JENIS:
        return f"kind harus salah satu {JENIS}"
    if rule.risk not in RISIKO:
        return f"risk harus salah satu {RISIKO}"
    if rule.applies not in BERLAKU:
        return f"applies harus salah satu {BERLAKU}"
    for nama in ("group", "label", "help"):
        if not isinstance(getattr(rule, nama), str) or not getattr(rule, nama).strip():
            return f"{nama} wajib diisi"
    if rule.kind == INT and (rule.min is None or rule.max is None or rule.min > rule.max):
        return "int butuh min <= max"
    if rule.kind in (CHOICE, LEVEL, KEY_LIST):
        if not rule.choices:
            return "choices wajib untuk choice, level, dan list_of_keys"
        nilai = [v for v, _ in rule.choices]
        if len(set(nilai)) != len(nilai):
            return "choices tidak boleh kembar"
        if any(not isinstance(lbl, str) or not lbl.strip() for _, lbl in rule.choices):
            return "setiap choice butuh label"
    if rule.kind == LEVEL and any(v not in NAMA_TINGKAT for v in rule.nilai_pilihan):
        return "level hanya boleh jenjang di NAMA_TINGKAT"
    if rule.kind == KEY_LIST and any(not isinstance(v, str) or "," in v for v in rule.nilai_pilihan):
        return "list_of_keys: setiap kunci str tanpa koma"
    if rule.member_default is not None:
        if not _POLA_JALUR.match(rule.member_default):
            return f"member_default berbentuk '<{'|'.join(BAGIAN_MEMBER)}>.<kolom>'"
        if rule.web:
            return "aturan bawaan member tidak dikirim ke web: web membaca nilai milik akunnya"
    if (rule.profile_theme_key is None) != (rule.profile_values is None):
        return "profile_theme_key dan profile_values selalu berpasangan"
    if rule.profile_theme_key is not None and not (rule.member_default or "").startswith(f"{BAGIAN_TAMPILAN}."):
        return "profile_theme_key hanya untuk aturan member_default bagian tampilan"
    if rule.ordered and rule.kind != KEY_LIST:
        return "ordered hanya untuk list_of_keys"
    try:
        if normalkan(rule, rule.default) != rule.default:
            return "default harus sudah dalam bentuk kanonik"
    except NilaiTidakSah as e:
        return f"default ditolak validatornya sendiri: {e}"
    if rule.profile_values is not None and set(rule.profile_values) != set(_semua_nilai(rule)):
        return "profile_values harus memetakan setiap nilai yang mungkin"
    return None


def _semua_nilai(rule: Rule) -> tuple:
    if rule.kind == BOOL:
        return (True, False)
    return rule.nilai_pilihan


# --------------------------------------------------------------------------
# Validator: nilai masuk (JSON atau teks tersimpan) -> nilai kanonik
# --------------------------------------------------------------------------


def _bulat(nilai) -> int:
    if isinstance(nilai, bool):
        raise ValueError
    if isinstance(nilai, int):
        return nilai
    teks = str(nilai).strip()
    if not re.fullmatch(r"-?\d+", teks):
        raise ValueError
    return int(teks)


def _bool(nilai) -> bool:
    if isinstance(nilai, bool):
        return nilai
    if isinstance(nilai, int) and nilai in (0, 1):
        return bool(nilai)
    teks = str(nilai).strip().lower()
    if teks in ("1", "true"):
        return True
    if teks in ("0", "false"):
        return False
    raise NilaiTidakSah("Must be on or off.")


def _int(rule: Rule, nilai) -> int:
    try:
        angka = _bulat(nilai)
    except (TypeError, ValueError):
        raise NilaiTidakSah("Must be a whole number.") from None
    if not rule.min <= angka <= rule.max:
        raise NilaiTidakSah(f"Must be between {rule.min} and {rule.max}.")
    return angka


def _pilihan(rule: Rule, nilai):
    for v in rule.nilai_pilihan:
        # Teks tersimpan selalu str; nilai JSON bisa int. bool tidak pernah lolos sebagai 0/1.
        if not isinstance(nilai, bool) and (nilai == v or str(nilai).strip() == str(v)):
            return v
    daftar = ", ".join(lbl for _, lbl in rule.choices)
    raise NilaiTidakSah(f"Must be one of: {daftar}.")


def _teks(rule: Rule, nilai) -> str:
    if not isinstance(nilai, str):
        raise NilaiTidakSah("Must be text.")
    teks = nilai.strip()
    batas = rule.max_length or TEKS_MAKS_BAWAAN
    if len(teks) > batas:
        raise NilaiTidakSah(f"Must be at most {batas} characters.")
    return teks


def _daftar_kunci(rule: Rule, nilai) -> tuple:
    if isinstance(nilai, str):
        butir = [b.strip() for b in nilai.split(",") if b.strip()]
    elif isinstance(nilai, (list, tuple)):
        butir = list(nilai)
    else:
        raise NilaiTidakSah("Must be a list.")
    sah = rule.nilai_pilihan
    asing = [b for b in butir if b not in sah]
    if asing:
        raise NilaiTidakSah(f"Unknown items: {', '.join(map(str, asing))}.")
    if len(set(butir)) != len(butir):
        raise NilaiTidakSah("Each item may appear only once.")
    if rule.ordered:
        return tuple(butir)
    return tuple(k for k in sah if k in butir)


def normalkan(rule: Rule, nilai):
    """Validasi `nilai` untuk `rule`, kembalikan bentuk kanonik. Tak sah: NilaiTidakSah."""
    if nilai is None:
        raise NilaiTidakSah("A value is required.")
    if rule.kind == BOOL:
        return _bool(nilai)
    if rule.kind == INT:
        return _int(rule, nilai)
    if rule.kind in (CHOICE, LEVEL):
        return _pilihan(rule, nilai)
    if rule.kind == TEXT:
        return _teks(rule, nilai)
    return _daftar_kunci(rule, nilai)


def ke_teks(rule: Rule, nilai) -> str:
    """Nilai kanonik -> teks yang disimpan di InstanceConfiguration.value."""
    if rule.kind == BOOL:
        return "1" if nilai else "0"
    if rule.kind == KEY_LIST:
        return ",".join(nilai)
    return str(nilai)


def ke_json(rule: Rule, nilai):
    """Nilai kanonik -> bentuk JSON (tuple jadi list)."""
    return list(nilai) if rule.kind == KEY_LIST else nilai
