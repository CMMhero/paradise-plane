# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: bawaan kode KEP-84
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Pins the shipped code defaults decided in KEP-84.

The rest of the suite pins the hierarchy gate OFF (see conftest), so this file is
the one place that proves what a fresh install actually gets.
"""

import os

import pytest

from plane.utils import saklar_instance as si
from plane.utils.bawaan_member import PABRIK


@pytest.mark.unit
@pytest.mark.gerbang_bawaan
class TestBawaanKodeKep84:
    @pytest.mark.parametrize(
        "kunci",
        [
            si.HIERARKI_GERBANG_TUGAS,
            si.ENABLE_DEADLINE_REMINDER,
            si.ENABLE_EMAIL_THREADING,
            si.ENABLE_EMAIL_ACTIVE_ONLY,
        ],
    )
    def test_saklar_menyala_secara_bawaan(self, kunci):
        assert si.SAKLAR_BAWAAN[kunci] == "1"

    def test_gerbang_hierarki_menyala_tanpa_env(self, monkeypatch):
        monkeypatch.delenv(si.HIERARKI_GERBANG_TUGAS, raising=False)
        assert si.env_benih(si.HIERARKI_GERBANG_TUGAS, si.SAKLAR_BAWAAN[si.HIERARKI_GERBANG_TUGAS]) == "1"

    def test_angka_bawaan(self):
        assert si.SETELAN_ANGKA[si.INVITE_EXPIRY_DAYS][0] == 7
        assert si.SETELAN_ANGKA[si.CHAT_EDIT_WINDOW_HOURS][0] == 24

    def test_retensi_trash_jatuh_ke_30_hari(self):
        # The fallback is int(env HARD_DELETE_AFTER_DAYS, 30) evaluated at import.
        if os.environ.get("HARD_DELETE_AFTER_DAYS"):
            pytest.skip("HARD_DELETE_AFTER_DAYS is set in this environment")
        assert si.SETELAN_ANGKA[si.TRASH_RETENTION_DAYS][0] == 30

    def test_zona_waktu_profil_pabrik(self):
        assert PABRIK["profile"]["timezone"] == "Asia/Jakarta"
