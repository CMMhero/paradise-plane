# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan area B, apa yang boleh dilakukan tiap jenjang
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Area B inventaris: menugaskan, mengubah, menyetujui, membuat."""

from plane.utils.aturan.jenis import LEVEL, TINGGI, Rule

# Jenjang terendah yang boleh menyetujui pekerjaan selesai (`calon_penyetuju` di
# utils/hierarki.py). Leader (12) sengaja tidak ditawarkan: `divisi_diawasi`
# leader selalu kosong, jadi pilihan itu tidak akan mengubah apa pun.
APPROVER_MIN_LEVEL = "APPROVER_MIN_LEVEL"

ATURAN = (
    Rule(
        key=APPROVER_MIN_LEVEL,
        kind=LEVEL,
        default=20,
        choices=(20, 30),
        group="approvals",
        label="Lowest level that can approve",
        help=(
            "Finished work waits for someone at this level or above who oversees the department and sits above "
            "the person who finished it. Raising it to Manager takes approvals away from supervisors."
        ),
        risk=TINGGI,
        kep="P29",
    ),
)
