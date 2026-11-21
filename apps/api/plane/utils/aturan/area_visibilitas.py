# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan area A, apa yang dilihat tiap jenjang
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Area A inventaris: apa yang dilihat tiap jenjang (menu, halaman, data)."""

from plane.utils.aturan.jenis import CHOICE, RENDAH, Rule

# Menu sidebar yang disembunyikan dari Direktur (jenjang 40). Dulu
# `DIRECTOR_HIDDEN_NAV_KEYS = ["archives"]` di apps/web/core/hooks/use-is-direktur.ts.
# Tampilan saja: API arsip tidak memeriksa jenjang, jadi risikonya rendah.
DIRECTOR_SIDEBAR_HIDES = "DIRECTOR_SIDEBAR_HIDES"

ATURAN = (
    Rule(
        key=DIRECTOR_SIDEBAR_HIDES,
        kind=CHOICE,
        default="archives",
        choices=(
            ("none", "Everything"),
            ("archives", "Everything except Archives"),
            ("archives_your_work", "Everything except Archives and Your work"),
        ),
        group="visibility",
        label="What directors see in the sidebar",
        help=(
            "Menus hidden from directors (level 40). Hidden Archives also sends them back from the Archives page. "
            "This only changes the sidebar; it does not block access to data."
        ),
        risk=RENDAH,
        web=True,
    ),
)
