# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pembaca pilihan "siapa boleh" area E
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Menerjemahkan satu pilihan bernama God Mode (area E) jadi ya atau tidak.

Admin workspace dan Super Admin selalu lolos, kecuali pilihannya `nobody`.
Selebihnya dibandingkan dengan jenjang efektif orang itu di workspace
(jabatan belum diisi dihitung staf, lihat `hierarki.tingkat_efektif`).
"""

from plane.db.models.hierarki import TINGKAT_MANAGER, TINGKAT_SEKRETARIS, TINGKAT_SUPERVISOR
from plane.utils.aturan.area_obrolan import DIREKTUR, MANAGER, SEMUA, SUPERVISOR, TIDAK_ADA

_AMBANG = {SUPERVISOR: TINGKAT_SUPERVISOR, MANAGER: TINGKAT_MANAGER, DIREKTUR: TINGKAT_SEKRETARIS}


def lolos_jenjang(user, workspace_id, pilihan, admin=None) -> bool:
    """`user` lolos `pilihan`. `admin` boleh diisi pemanggil yang sudah menghitungnya."""
    from plane.utils.hierarki import adalah_admin_penuh, tingkat_efektif  # noqa: PLC0415

    if pilihan == SEMUA:
        return True
    if pilihan == TIDAK_ADA:
        return False
    if admin is None:
        admin = adalah_admin_penuh(user, workspace_id)
    if admin:
        return True
    ambang = _AMBANG.get(pilihan)
    if ambang is None:
        return False
    return tingkat_efektif(user.id, workspace_id) >= ambang
