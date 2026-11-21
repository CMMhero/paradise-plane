# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan area C, bawaan tampilan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Area C inventaris: bawaan tampilan untuk akun baru.

Aturan di sini memakai `member_default="tampilan.<kolom>"`: nilainya disimpan di
PARADISE_BAWAAN_MEMBER (God Mode > People > New member defaults), diberikan ke
akun baru, dan bisa diterapkan ke semua akun dengan tombol "Apply to existing
members" (`terapkan_ke_semua`, bagian "tampilan").
"""

from plane.utils.aturan.jenis import BOOL, RENDAH, Rule

# Urutan linimasa aktivitas & komentar work item. Per akun di
# `Profile.theme["urutan_aktivitas"]`; kosong = terbaru di atas
# (apps/web/core/hooks/use-urutan-aktivitas.ts).
ACTIVITY_NEWEST_FIRST = "ACTIVITY_NEWEST_FIRST"

ATURAN = (
    Rule(
        key=ACTIVITY_NEWEST_FIRST,
        kind=BOOL,
        default=True,
        group="display",
        label="Activity timeline shows newest first",
        help=(
            "The order of activity and comments on a work item for new accounts. "
            "Each person can still flip it on the work item or in their preferences."
        ),
        risk=RENDAH,
        member_default="tampilan.aktivitas_terbaru_di_atas",
        profile_theme_key="urutan_aktivitas",
        profile_values={True: "desc", False: "asc"},
    ),
)
