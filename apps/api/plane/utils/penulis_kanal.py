# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: penulis kanal Announcements
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Siapa, selain admin, yang boleh menulis di kanal Announcements.

Admin memberi izin per departemen (mis. HR) atau per orang lewat `PenulisKanal`.
Izin departemen berlaku untuk siapa pun yang ditempatkan di departemen itu, di
jenjang apa pun, dan ikut berubah begitu penempatannya berubah: yang pindah
departemen kehilangan izinnya tanpa ada yang perlu mencabut.
"""

from django.db.models import Q

from plane.db.models import JabatanOrganisasi, PenulisKanal


def penulis_diizinkan(user_id, ruang) -> bool:
    departemen_saya = JabatanOrganisasi.objects.filter(
        workspace_id=ruang.workspace_id, member_id=user_id, departemen__isnull=False
    ).values("departemen_id")
    return PenulisKanal.objects.filter(Q(user_id=user_id) | Q(departemen_id__in=departemen_saya), ruang=ruang).exists()
