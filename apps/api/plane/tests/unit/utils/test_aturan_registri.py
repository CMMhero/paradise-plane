# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pagar registri aturan God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Pagar untuk setiap aturan di `plane.utils.aturan`, termasuk yang ditambahkan
agen area nanti: deklarasinya lengkap, bawaannya lolos validatornya sendiri,
kuncinya tidak bentrok dengan registri lama, dan pembacanya jatuh ke bawaan
untuk nilai rusak.
"""

import ast
import inspect
import re

import pytest

from plane.db.models.hierarki import TINGKAT_CHOICES
from plane.utils import aturan
from plane.utils.aturan import baca, jenis, registri
from plane.utils.aturan.grup import GRUP
from plane.utils.aturan.jenis import NilaiTidakSah, Rule, ke_teks, normalkan
from plane.utils.setelan_instance import dikenal

SEMUA = list(aturan.REGISTRI.values())
ID = [r.key for r in SEMUA]


def nilai_lain(rule: Rule):
    """Satu nilai sah yang BUKAN bawaan, untuk menguji perubahan."""
    if rule.kind == jenis.BOOL:
        return not rule.default
    if rule.kind == jenis.INT:
        return rule.default + 1 if rule.default < rule.max else rule.default - 1
    if rule.kind in (jenis.CHOICE, jenis.LEVEL):
        return next(v for v in rule.nilai_pilihan if v != rule.default)
    if rule.kind == jenis.TEXT:
        return (rule.default + "x")[: rule.max_length or jenis.TEKS_MAKS_BAWAAN]
    lain = tuple(k for k in rule.nilai_pilihan if k not in rule.default)
    return lain[:1] if lain else rule.default[1:]


@pytest.mark.unit
class TestDeklarasi:
    def test_registri_tidak_kosong_dan_setiap_area_ditemukan(self):
        assert SEMUA
        modul = registri._modul_area()
        assert {"area_visibilitas", "area_tugas", "area_tampilan", "area_obrolan"} <= set(modul)
        for nama in modul:
            assert isinstance(__import__(f"plane.utils.aturan.{nama}", fromlist=["ATURAN"]).ATURAN, tuple), nama

    @pytest.mark.parametrize("rule", SEMUA, ids=ID)
    def test_metadata_lengkap(self, rule):
        assert re.fullmatch(r"[A-Z][A-Z0-9_]*", rule.key)
        assert rule.label.strip() and rule.help.strip()
        assert rule.group in GRUP
        assert rule.area and f"area_{rule.area}" in registri._modul_area()
        assert rule.risk in jenis.RISIKO
        assert rule.applies in jenis.BERLAKU

    @pytest.mark.parametrize("rule", SEMUA, ids=ID)
    def test_bawaan_lolos_validatornya_dan_kanonik(self, rule):
        assert normalkan(rule, rule.default) == rule.default
        # Bolak-balik lewat bentuk tersimpan juga kembali ke nilai yang sama.
        assert normalkan(rule, ke_teks(rule, rule.default)) == rule.default

    @pytest.mark.parametrize("rule", SEMUA, ids=ID)
    def test_nilai_lain_sah_dan_berbeda(self, rule):
        lain = nilai_lain(rule)
        assert normalkan(rule, lain) != rule.default

    def test_kunci_unik_dan_tidak_dimiliki_registri_lama(self):
        assert len(set(ID)) == len(ID)
        assert [k for k in ID if dikenal(k)] == []

    def test_kunci_kembar_menggagalkan_penemuan(self, monkeypatch):
        satu = Rule(key="DUPLIKAT_UJI", kind=jenis.BOOL, default=True, group="chat", label="x", help="y", risk="low")
        modul = type("M", (), {"ATURAN": (satu,)})
        monkeypatch.setattr(registri, "_modul_area", lambda: ["area_a", "area_b"])
        monkeypatch.setattr(registri.importlib, "import_module", lambda nama: modul)
        with pytest.raises(ValueError, match="dua kali"):
            registri.kumpulkan()

    def test_grup_asing_menggagalkan_penemuan(self, monkeypatch):
        satu = Rule(key="GRUP_UJI", kind=jenis.BOOL, default=True, group="tidak_ada", label="x", help="y", risk="low")
        monkeypatch.setattr(registri, "_modul_area", lambda: ["area_a"])
        monkeypatch.setattr(registri.importlib, "import_module", lambda nama: type("M", (), {"ATURAN": (satu,)}))
        with pytest.raises(ValueError, match="grup"):
            registri.kumpulkan()

    @pytest.mark.parametrize(
        "salah",
        [
            {"key": "huruf_kecil"},
            {"kind": "matrix"},
            {"risk": "extreme"},
            {"label": " "},
            {"help": ""},
            {"default": "ya"},
            {"kind": jenis.INT, "default": 5, "min": 1},
            {"kind": jenis.INT, "default": 50, "min": 1, "max": 10},
            {"kind": jenis.CHOICE, "default": "a"},
            {"kind": jenis.LEVEL, "default": 20, "choices": (20, 99)},
            {"kind": jenis.CHOICE, "default": "c", "choices": (("a", "A"), ("b", "B"))},
            {"member_default": "profile.bahasa"},
            {"member_default": "tampilan.x", "web": True},
            {"profile_theme_key": "x"},
        ],
    )
    def test_deklarasi_cacat_ditolak_saat_dibuat(self, salah):
        dasar = {"key": "UJI", "kind": jenis.BOOL, "default": True, "group": "chat", "label": "x", "help": "y"}
        with pytest.raises(ValueError):
            Rule(**{**dasar, "risk": "low", **salah})

    def test_nama_tingkat_cermin_model(self):
        assert {t: n for t, n in TINGKAT_CHOICES}.keys() == jenis.NAMA_TINGKAT.keys()

    def test_bawaan_member_tampilan_dibangun_dari_registri(self):
        from plane.utils.bawaan_member import PABRIK, aturan_tampilan

        tampilan = aturan_tampilan()
        assert tampilan
        assert PABRIK["tampilan"] == {kolom: rule.default for kolom, rule in tampilan.items()}

    @pytest.mark.parametrize("rule", [r for r in SEMUA if r.web], ids=[r.key for r in SEMUA if r.web])
    def test_aturan_web_berbawaan_literal_yang_bisa_dibaca_tes_ts(self, rule):
        """packages/constants/src/aturan/aturan.test.ts membaca `default=` dari sumber Python.

        Aturan `web=True` wajib menulis `default=<literal>` (bool, int, "teks", atau
        tuple teks) di satu baris, supaya tes TS bisa mencocokkannya dengan cermin web.
        """
        sumber = inspect.getsource(__import__(f"plane.utils.aturan.area_{rule.area}", fromlist=["ATURAN"]))
        blok = [b for b in sumber.split("Rule(")[1:] if re.search(rf"key=({rule.key}|\"{rule.key}\")\b", b)]
        assert len(blok) == 1, rule.key
        cocok = re.search(r"^\s*default=(.+),\s*$", blok[0], re.M)
        assert cocok, f"{rule.key}: default harus satu baris literal"
        literal = ast.literal_eval(cocok.group(1))
        assert normalkan(rule, literal) == rule.default


@pytest.mark.unit
class TestValidator:
    def _rule(self, **lain):
        dasar = {"key": "UJI", "group": "chat", "label": "x", "help": "y", "risk": "low"}
        return Rule(**{**dasar, **lain})

    def test_bool(self):
        r = self._rule(kind=jenis.BOOL, default=False)
        assert [normalkan(r, v) for v in (True, 1, "1", "true", False, 0, "0", "false")] == [True] * 4 + [False] * 4
        with pytest.raises(NilaiTidakSah):
            normalkan(r, "ya")
        assert ke_teks(r, True) == "1"

    def test_int_menolak_bool_dan_di_luar_rentang(self):
        r = self._rule(kind=jenis.INT, default=5, min=1, max=10)
        assert normalkan(r, "7") == 7
        for salah in (True, 0, 11, "7.5", "tujuh"):
            with pytest.raises(NilaiTidakSah):
                normalkan(r, salah)

    def test_choice_teks_dan_angka(self):
        r = self._rule(kind=jenis.CHOICE, default="a", choices=(("a", "A"), ("b", "B")))
        assert normalkan(r, "b") == "b"
        angka = self._rule(kind=jenis.CHOICE, default=1, choices=((1, "Satu"), (2, "Dua")))
        assert normalkan(angka, "2") == 2
        with pytest.raises(NilaiTidakSah):
            normalkan(angka, True)

    def test_level_berlabel_dari_nama_tingkat(self):
        r = self._rule(kind=jenis.LEVEL, default=20, choices=(20, 30))
        assert r.choices == ((20, "Supervisor (20)"), (30, "Manager (30)"))
        with pytest.raises(NilaiTidakSah):
            normalkan(r, 40)

    def test_text_dan_panjang(self):
        r = self._rule(kind=jenis.TEXT, default="", max_length=3)
        assert normalkan(r, " ab ") == "ab"
        with pytest.raises(NilaiTidakSah):
            normalkan(r, "abcd")
        with pytest.raises(NilaiTidakSah):
            normalkan(r, 5)

    def test_list_of_keys_kanonik_urutan_choices(self):
        r = self._rule(kind=jenis.KEY_LIST, default=(), choices=(("a", "A"), ("b", "B"), ("c", "C")))
        assert normalkan(r, ["c", "a"]) == ("a", "c")
        assert normalkan(r, "c,a") == ("a", "c")
        assert ke_teks(r, ("a", "c")) == "a,c"
        for salah in (["a", "a"], ["z"], 5):
            with pytest.raises(NilaiTidakSah):
                normalkan(r, salah)


@pytest.mark.unit
class TestPembaca:
    @pytest.mark.django_db
    @pytest.mark.parametrize("rule", SEMUA, ids=ID)
    def test_tanpa_baris_semua_aturan_bernilai_bawaan(self, rule):
        assert aturan.get(rule.key) == rule.default

    @pytest.mark.django_db
    def test_nilai_rusak_jatuh_ke_bawaan(self):
        from plane.license.models import InstanceConfiguration

        rule = next(r for r in SEMUA if r.kind == jenis.INT)
        InstanceConfiguration.objects.create(key=rule.key, value="bukan angka", category="PARADISE")
        assert aturan.get(rule.key) == rule.default

    @pytest.mark.django_db
    def test_pembantu_berjenis_menolak_jenis_lain(self):
        rule_bool = next(r for r in SEMUA if r.kind == jenis.BOOL)
        with pytest.raises(TypeError):
            aturan.get_int(rule_bool.key)
        with pytest.raises(KeyError):
            aturan.get("TIDAK_ADA")

    @pytest.mark.django_db
    def test_potret_satu_kueri_dan_dibuang_saat_disimpan(self, django_assert_num_queries):
        from plane.license.models import InstanceConfiguration
        from plane.utils.aturan.area_obrolan import CHAT_PINS_MAX

        aturan.segarkan()
        with django_assert_num_queries(1):
            for _ in range(5):
                for rule in SEMUA:
                    aturan.get(rule.key)
        # Proses yang menulis langsung membaca nilai baru (sinyal post_save).
        InstanceConfiguration.objects.create(key=CHAT_PINS_MAX, value="7", category="PARADISE")
        assert aturan.get_int(CHAT_PINS_MAX) == 7
        InstanceConfiguration.objects.filter(key=CHAT_PINS_MAX).delete(soft=False)
        assert aturan.get_int(CHAT_PINS_MAX) == 20

    @pytest.mark.django_db
    def test_potret_kedaluwarsa_sesudah_cache_detik(self, monkeypatch):
        from plane.license.models import InstanceConfiguration
        from plane.utils.aturan.area_obrolan import CHAT_PINS_MAX

        jam = [1000.0]
        monkeypatch.setattr(baca.time, "monotonic", lambda: jam[0])
        assert aturan.get_int(CHAT_PINS_MAX) == 20
        # Ditulis proses lain: tanpa sinyal di proses ini.
        InstanceConfiguration.objects.bulk_create([InstanceConfiguration(key=CHAT_PINS_MAX, value="9")])
        assert aturan.get_int(CHAT_PINS_MAX) == 20
        jam[0] += aturan.CACHE_DETIK
        assert aturan.get_int(CHAT_PINS_MAX) == 9
