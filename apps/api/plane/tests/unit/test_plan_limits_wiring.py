# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Bahwa penjaganya benar-benar DIPANGGIL, bukan cuma ada.

Berkas ini lahir dari kesalahan nyata: `periksa_penambahan_anggota` ditulis
lengkap dengan ujinya, lolos semua, dan ternyata tidak dipanggil satu view pun.
Batas yang tidak dipanggil bukan batas, dan uji unit atas fungsinya tidak pernah
bisa menangkap itu.

Jadi yang diuji di sini bukan aturannya melainkan SAMBUNGANNYA: permintaan HTTP
sungguhan lewat rute sungguhan, dan jawabannya harus 403.
"""

import pytest
from rest_framework.test import APIClient

from plane.db.models import (
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceMemberInvite,
    WorkspacePlan,
)


def _admin_workspace(slug):
    pemilik = User.objects.create(email=f"{slug}@demo.test", username=f"{slug}_demo_test")
    ws = Workspace.objects.create(name=slug, slug=slug, owner=pemilik)
    WorkspaceMember.objects.create(workspace=ws, member=pemilik, role=20, is_active=True)
    return ws, pemilik


@pytest.mark.unit
@pytest.mark.django_db
class TestKursiDitegakkanLewatHTTP:
    def test_gratis_perorangan_MENOLAK_undangan_lewat_endpoint_sungguhan(self):
        """Inilah uji yang seharusnya ada sejak awal."""
        ws, pemilik = _admin_workspace("kirim-a")
        klien = APIClient()
        klien.force_authenticate(user=pemilik)

        jawab = klien.post(
            f"/api/workspaces/{ws.slug}/invitations/",
            {"emails": [{"email": "calon@demo.test", "role": 15}]},
            format="json",
        )

        assert jawab.status_code == 403
        assert jawab.json()["code"] == "MEMBER_LIMIT_REACHED"
        assert WorkspaceMemberInvite.objects.filter(workspace=ws).count() == 0

    def test_tingkatan_berbayar_membiarkannya_lewat(self):
        ws, pemilik = _admin_workspace("kirim-b")
        WorkspacePlan.objects.create(workspace=ws, tier="PRO")
        klien = APIClient()
        klien.force_authenticate(user=pemilik)

        jawab = klien.post(
            f"/api/workspaces/{ws.slug}/invitations/",
            {"emails": [{"email": "calon@demo.test", "role": 15}]},
            format="json",
        )

        assert jawab.status_code in (200, 201), jawab.content
        assert WorkspaceMemberInvite.objects.filter(workspace=ws).count() == 1

    def test_mengundang_SEKALIGUS_lebih_banyak_dari_kursi_ditolak(self):
        """Sepuluh undangan sekaligus tidak boleh lolos hanya karena dikirim bersamaan."""
        ws, pemilik = _admin_workspace("kirim-c")
        WorkspacePlan.objects.create(workspace=ws, tier="FREE", max_members=3)
        klien = APIClient()
        klien.force_authenticate(user=pemilik)

        jawab = klien.post(
            f"/api/workspaces/{ws.slug}/invitations/",
            {"emails": [{"email": f"c{i}@demo.test", "role": 15} for i in range(10)]},
            format="json",
        )

        assert jawab.status_code == 403
        assert WorkspaceMemberInvite.objects.filter(workspace=ws).count() == 0

    def test_undangan_kedua_ditolak_karena_yang_pertama_masih_memesan_kursi(self):
        """Batas yang bisa dilewati dengan mengirim undangan satu per satu bukan batas."""
        ws, pemilik = _admin_workspace("kirim-d")
        WorkspacePlan.objects.create(workspace=ws, tier="FREE", max_members=2)
        klien = APIClient()
        klien.force_authenticate(user=pemilik)
        alamat = f"/api/workspaces/{ws.slug}/invitations/"

        pertama = klien.post(
            alamat, {"emails": [{"email": "satu@demo.test", "role": 15}]}, format="json"
        )
        kedua = klien.post(
            alamat, {"emails": [{"email": "dua@demo.test", "role": 15}]}, format="json"
        )

        assert pertama.status_code in (200, 201), pertama.content
        assert kedua.status_code == 403
        assert WorkspaceMemberInvite.objects.filter(workspace=ws).count() == 1
