# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: impor link portal (KEP-82)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Dikunci untuk migrasi 0166 (impor link one.paradiseperkasa.com):

1. Semua 23 link masuk sebagai quick link global (untuk semua orang) tanpa ikon pilihan:
   logo situs yang tampil, emoji kategori hanya cadangan kalau situs tak punya favicon.
2. Unit organisasi yang namanya sama dengan kategori portal TIDAK mempersempit sasaran.
3. Dijalankan dua kali tidak menggandakan apa pun.
"""

from importlib import import_module

import pytest
from django.apps import apps as django_apps

from plane.db.models import Divisi, QuickLinkBersama

migrasi = import_module("plane.db.migrations.0166_quick_link_portal")


@pytest.mark.django_db
def test_impor_link_portal_global(workspace):
    it = Divisi.objects.create(workspace=workspace, kode="IT", nama="Information Technology")

    migrasi.impor(django_apps, None)

    links = QuickLinkBersama.objects.filter(workspace=workspace)
    assert links.count() == len(migrasi.LINKS) == 23
    assert set(links.values_list("cakupan", flat=True)) == {"semua"}
    assert not it.quick_link_bersama.exists()
    assert links.get(title="HRIS - Haermes").url == "https://ids.cloudapp.id/account/login"

    assert not any(link.metadata.get("logo_props") for link in links)
    drive = links.get(title="SAP Grow - Google Drive - Master Data")
    assert drive.metadata["logo_cadangan"] == {"in_use": "emoji", "emoji": {"value": migrasi.EMOJI_DRIVE}}

    migrasi.impor(django_apps, None)
    assert QuickLinkBersama.objects.filter(workspace=workspace).count() == 23
