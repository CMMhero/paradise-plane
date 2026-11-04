# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: registri setelan instance (KEP-83)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Validator dan pembaca registri setelan God Mode.

Yang dijaga: setiap jenis menolak bentuk yang salah dan menormalkan bentuk yang
benar, pembaca jatuh ke bawaan saat database berisi sampah (task Celery tidak
boleh mati), kunci baru tidak membaca env dengan namanya sendiri (KEP-48), dan
bawaan setiap kunci baru sama dengan perilaku sebelum kuncinya ada.
"""

from datetime import time
from zoneinfo import ZoneInfo

import pytest

from plane.license.models import InstanceConfiguration
from plane.utils import saklar_instance as si
from plane.utils import setelan_instance as st


def _simpan(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(key=kunci, defaults={"value": nilai, "category": "PARADISE"})


@pytest.mark.unit
class TestValidator:
    @pytest.mark.parametrize(
        "nilai,hasil", [("1", "1"), ("0", "0"), (1, "1"), (0, "0"), (True, "1"), (False, "0"), (" 1 ", "1")]
    )
    def test_toggle_sah(self, nilai, hasil):
        assert st.normalkan(si.ASSIGN_DOWN_ONLY, nilai) == hasil

    @pytest.mark.parametrize("nilai", ["2", "yes", "", "true", None])
    def test_toggle_ditolak(self, nilai):
        with pytest.raises(st.NilaiTidakSah):
            st.normalkan(si.ASSIGN_DOWN_ONLY, nilai)

    def test_angka_rentang(self):
        assert st.normalkan(si.STUCK_AFTER_DAYS, "90") == "90"
        assert st.normalkan(si.STUCK_AFTER_DAYS, 1) == "1"
        for salah in ("0", "91", "7.5", "abc", True, ""):
            with pytest.raises(st.NilaiTidakSah):
                st.normalkan(si.STUCK_AFTER_DAYS, salah)

    def test_pilihan_hanya_dari_daftar(self):
        assert st.jenis(si.APPROVAL_REQUIRED_BELOW_LEVEL) == st.JENIS_PILIHAN
        assert st.normalkan(si.APPROVAL_REQUIRED_BELOW_LEVEL, "30") == "30"
        with pytest.raises(st.NilaiTidakSah):
            st.normalkan(si.APPROVAL_REQUIRED_BELOW_LEVEL, "25")
        with pytest.raises(st.NilaiTidakSah):
            st.normalkan(si.TASK_DELETE_RULE, 3)

    @pytest.mark.parametrize(
        "nilai,hasil", [("08:30", "08:30"), ("8:05", "08:05"), ("23:50", "23:50"), ("00:00", "00:00")]
    )
    def test_jam_sah(self, nilai, hasil):
        assert st.normalkan(st.DIGEST_MORNING_TIME, nilai) == hasil

    @pytest.mark.parametrize("nilai", ["24:00", "12:60", "8", "08:5", "8.30", 830, ""])
    def test_jam_ditolak(self, nilai):
        with pytest.raises(st.NilaiTidakSah):
            st.normalkan(st.DIGEST_MORNING_TIME, nilai)

    # Detak beat tiap 5 menit: menit di luar kelipatan 5 dan jam sesudah 23:50
    # tidak pernah jatuh tempo tepat waktu (atau sama sekali).
    @pytest.mark.parametrize("nilai", ["08:03", "17:31", "23:55", "23:59"])
    def test_jam_harus_kelipatan_lima_dan_paling_lambat_2350(self, nilai):
        with pytest.raises(st.NilaiTidakSah, match="5-minute steps, no later than 23:50"):
            st.normalkan(st.DIGEST_MORNING_TIME, nilai)

    def test_daftar_hari_diurutkan(self):
        assert st.normalkan(st.DEADLINE_REMINDER_EMAIL_DAYS, "3, -1,0") == "-1,0,3"
        assert st.normalkan(st.DEADLINE_REMINDER_EMAIL_DAYS, [7, -7]) == "-7,7"

    @pytest.mark.parametrize("nilai", ["", "1,1", "-31", "31", "a,b", ",".join(str(i) for i in range(13)), "1,,2"])
    def test_daftar_hari_ditolak(self, nilai):
        with pytest.raises(st.NilaiTidakSah):
            st.normalkan(st.DEADLINE_REMINDER_EMAIL_DAYS, nilai)

    def test_hari_kerja(self):
        assert st.normalkan(st.DIGEST_WEEKDAYS, "5,1,3") == "1,3,5"
        for salah in ("", "0", "8", "1,1"):
            with pytest.raises(st.NilaiTidakSah):
                st.normalkan(st.DIGEST_WEEKDAYS, salah)

    def test_zona_waktu_memakai_all_timezones(self):
        # Jebakan L2: America/Godthab tidak ada di common_timezones.
        assert st.normalkan(st.OFFICE_TIMEZONE, "America/Godthab") == "America/Godthab"
        assert st.normalkan(st.OFFICE_TIMEZONE, "Asia/Jakarta") == "Asia/Jakarta"
        with pytest.raises(st.NilaiTidakSah):
            st.normalkan(st.OFFICE_TIMEZONE, "Mars/Olympus")

    def test_kunci_asing(self):
        with pytest.raises(st.NilaiTidakSah):
            st.normalkan("BUKAN_KUNCI", "1")

    def test_kunci_sensitif(self):
        assert st.SENSITIF == {
            si.SESSION_DAYS,
            si.APPROVAL_REQUIRED_BELOW_LEVEL,
            si.APPROVAL_REJECT_REASON_REQUIRED,
            si.TASK_DELETE_RULE,
            si.DUE_DATE_CHANGE_RULE,
            si.ASSIGN_DOWN_ONLY,
            si.HIERARKI_GERBANG_TUGAS,
            si.APPROVAL_FINISH_TIME,
            si.APPROVAL_PENDING_NOT_LATE,
            # KEP-85: aturan izin per sumber juga mengubah siapa boleh apa.
            *si.IZIN_ISI,
            *si.IZIN_STRUKTUR,
        }


@pytest.mark.unit
class TestBawaanSamaDenganHariIni:
    def test_bawaan(self):
        harapan = {
            st.OFFICE_TIMEZONE: "Asia/Jakarta",
            st.DEADLINE_REMINDER_EMAIL_DAYS: "-7,-5,-3,-1,0,3,5,7",
            st.DEADLINE_REMINDER_INBOX_DAYS: "-1,0,1,3,7",
            st.DEADLINE_REMINDER_TIME: "08:00",
            st.DIGEST_MORNING_TIME: "08:30",
            st.DIGEST_EVENING_TIME: "17:30",
            st.DIRECTOR_DIGEST_TIME: "08:30",
            st.DIGEST_WEEKDAYS: "1,2,3,4,5",
            si.DIGEST_LOOKAHEAD_DAYS: "7",
            si.STUCK_AFTER_DAYS: "7",
            si.INVITE_EXPIRY_DAYS: "7",
            si.CHAT_MESSAGE_MAX_LENGTH: "5000",
            si.CHAT_ATTACHMENTS_MAX: "5",
            si.CHAT_EDIT_WINDOW_HOURS: "24",
            si.ATTENTION_REJECTED_DAYS: "14",
            si.ATTENTION_MENTION_DAYS: "7",
            si.APPROVAL_REQUIRED_BELOW_LEVEL: "20",
            si.APPROVAL_REJECT_REASON_REQUIRED: "1",
            si.TASK_DELETE_RULE: "0",
            si.DUE_DATE_CHANGE_RULE: "0",
            si.ASSIGN_DOWN_ONLY: "1",
            si.HIERARKI_GERBANG_TUGAS: "1",
        }
        assert {k: st.bawaan(k) for k in harapan} == harapan

    def test_benih_env_lama(self, monkeypatch):
        monkeypatch.setenv("FILE_SIZE_LIMIT", "524288000")
        assert si.batas_proxy_mb() == 500
        monkeypatch.setenv("FILE_SIZE_LIMIT", "rusak")
        assert si.batas_proxy_mb() == 5
        monkeypatch.delenv("FILE_SIZE_LIMIT")
        assert si.batas_proxy_mb() == 5
        monkeypatch.setenv("SESSION_COOKIE_AGE", "604800")
        assert si._benih_env("SESSION_COOKIE_AGE", 86400, 7, 1, 90) == 7
        monkeypatch.setenv("SESSION_COOKIE_AGE", "60")
        assert si._benih_env("SESSION_COOKIE_AGE", 86400, 7, 1, 90) == 1

    def test_upload_max_tidak_melewati_proxy(self):
        bawaan, minimum, maksimum = si.SETELAN_ANGKA[si.UPLOAD_MAX_MB]
        assert minimum == 1 and bawaan == maksimum == si.batas_proxy_mb()


@pytest.mark.unit
class TestPembaca:
    @pytest.mark.django_db
    def test_tanpa_baris_memakai_bawaan(self):
        assert st.setelan_jam(st.DEADLINE_REMINDER_TIME) == time(8, 0)
        assert st.setelan_hari(st.DEADLINE_REMINDER_INBOX_DAYS) == (-1, 0, 1, 3, 7)
        assert st.setelan_hari_kerja(st.DIGEST_WEEKDAYS) == frozenset({1, 2, 3, 4, 5})
        assert st.zona_kantor() == ZoneInfo("Asia/Jakarta")

    @pytest.mark.django_db
    def test_database_menang(self):
        _simpan(st.DIGEST_EVENING_TIME, "18:15")
        _simpan(st.DIGEST_WEEKDAYS, "1,3")
        _simpan(st.OFFICE_TIMEZONE, "Asia/Makassar")
        assert st.setelan_jam(st.DIGEST_EVENING_TIME) == time(18, 15)
        assert st.setelan_hari_kerja(st.DIGEST_WEEKDAYS) == frozenset({1, 3})
        assert st.zona_kantor() == ZoneInfo("Asia/Makassar")

    @pytest.mark.django_db
    def test_sampah_di_database_jatuh_ke_bawaan(self):
        _simpan(st.DIGEST_MORNING_TIME, "25:99")
        _simpan(st.DEADLINE_REMINDER_EMAIL_DAYS, "x")
        _simpan(st.OFFICE_TIMEZONE, "Bukan/Zona")
        _simpan(si.STUCK_AFTER_DAYS, "rusak")
        assert st.setelan_jam(st.DIGEST_MORNING_TIME) == time(8, 30)
        assert st.setelan_hari(st.DEADLINE_REMINDER_EMAIL_DAYS) == (-7, -5, -3, -1, 0, 3, 5, 7)
        assert st.zona_kantor() == ZoneInfo("Asia/Jakarta")
        assert si.setelan_angka(si.STUCK_AFTER_DAYS) == 7

    @pytest.mark.django_db
    def test_kunci_baru_tidak_membaca_env(self, monkeypatch):
        # KEP-48: env baru = MAJOR. Kunci KEP-83 hanya database -> bawaan kode.
        monkeypatch.setenv(si.STUCK_AFTER_DAYS, "30")
        monkeypatch.setenv(si.ASSIGN_DOWN_ONLY, "0")
        monkeypatch.setenv(st.DIGEST_MORNING_TIME, "06:00")
        assert si.setelan_angka(si.STUCK_AFTER_DAYS) == 7
        assert si.saklar_aktif(si.ASSIGN_DOWN_ONLY) is True
        assert st.setelan_jam(st.DIGEST_MORNING_TIME) == time(8, 30)

    @pytest.mark.django_db
    def test_kunci_lama_tetap_membaca_env(self, monkeypatch):
        monkeypatch.setenv(si.HIERARKI_GERBANG_TUGAS, "1")
        assert si.saklar_aktif(si.HIERARKI_GERBANG_TUGAS) is True

    def test_pembaca_salah_jenis_adalah_bug(self):
        with pytest.raises(KeyError):
            st.setelan_jam(st.DIGEST_WEEKDAYS)
        with pytest.raises(KeyError):
            st.setelan_hari(st.DIGEST_MORNING_TIME)

    @pytest.mark.django_db
    def test_daftar_setelan_mencakup_semua_kunci(self):
        daftar = st.daftar_setelan()
        kunci = [d["key"] for d in daftar]
        assert kunci == st.semua_kunci()
        assert len(kunci) == len(set(kunci))
        peta = {d["key"]: d for d in daftar}
        assert peta[si.APPROVAL_REQUIRED_BELOW_LEVEL]["choices"] == [20, 30, 40]
        assert peta[si.STUCK_AFTER_DAYS] | {"value": None} == {
            "key": si.STUCK_AFTER_DAYS,
            "kind": "number",
            "default": "7",
            "value": None,
            "min": 1,
            "max": 90,
            "choices": None,
            "sensitive": False,
        }
        assert peta[st.DIGEST_WEEKDAYS]["min"] is None
        assert peta[si.SESSION_DAYS]["sensitive"] is True
        assert "GOOGLE_CALENDAR_CLIENT_SECRET" not in peta
