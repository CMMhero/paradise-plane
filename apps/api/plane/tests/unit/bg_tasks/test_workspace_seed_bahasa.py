# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: isi contoh workspace baru mengikuti bahasa pembuatnya
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Workspace baru diisi proyek contoh dalam bahasa pembuatnya, tanpa merek Plane
dan tanpa cycle (fitur itu dicabut, KEP-53)."""

import json
import os
import re

import pytest
from django.conf import settings

from plane.bgtasks.workspace_seed_task import read_seed_file, workspace_seed
from plane.db.models import Cycle, Issue, Module, Page, Profile, Project

BERKAS = ("projects", "labels", "modules", "views", "cycles", "states", "issues", "pages")
MEREK_UPSTREAM = re.compile(r"\bPlane\b")


@pytest.mark.unit
class TestBerkasContohPerBahasa:
    @pytest.mark.parametrize("bahasa", ["id", "en"])
    def test_semua_berkas_ada_dan_sah(self, bahasa):
        for nama in BERKAS:
            path = os.path.join(settings.SEED_DIR, "data", bahasa, f"{nama}.json")
            assert os.path.exists(path), path
            assert isinstance(json.load(open(path, encoding="utf-8")), list)  # noqa: SIM115

    @pytest.mark.parametrize("bahasa", ["id", "en"])
    def test_tidak_menyebut_plane_atau_cycle(self, bahasa):
        for nama in BERKAS:
            teks = json.dumps(read_seed_file(f"{nama}.json", bahasa), ensure_ascii=False)
            assert not MEREK_UPSTREAM.search(teks), f"{bahasa}/{nama}.json menyebut Plane"
        assert read_seed_file("cycles.json", bahasa) == []

    def test_bahasa_tanpa_folder_jatuh_ke_bawaan_upstream(self):
        assert read_seed_file("projects.json", "de") == read_seed_file("projects.json")


@pytest.mark.unit
class TestWorkspaceSeedMengikutiBahasa:
    @pytest.mark.django_db
    @pytest.mark.parametrize(
        ("kode", "judul_pertama"),
        [("id", "Selamat datang di Paradise Task Tracker"), ("en", "Welcome to Paradise Task Tracker")],
    )
    def test_isi_contoh_dalam_bahasa_pemilik(self, workspace, create_user, kode, judul_pertama):
        Profile.objects.update_or_create(user=create_user, defaults={"language": kode})

        workspace_seed(workspace.id)

        proyek = Project.objects.get(workspace=workspace)
        assert proyek.description.startswith("Selamat datang" if kode == "id" else "Welcome")
        pertama = Issue.objects.filter(workspace=workspace).order_by("sort_order").first()
        assert pertama.name.startswith(judul_pertama)
        assert Issue.objects.filter(workspace=workspace).count() == 6
        assert Module.objects.filter(workspace=workspace).count() == 3
        assert Page.objects.filter(workspace=workspace).count() == 2
        assert Cycle.objects.filter(workspace=workspace).count() == 0
