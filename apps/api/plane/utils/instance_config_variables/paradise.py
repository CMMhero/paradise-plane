# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: saklar fitur di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Benih untuk `configure_instance`: env hanya dibaca saat barisnya belum ada.
# Sesudah itu nilainya diatur dari God Mode > Fitur & otomasi.

import os

from plane.utils.saklar_instance import SAKLAR_BAWAAN, SETELAN_ANGKA

paradise_config_variables = [
    *(
        {
            "key": kunci,
            "value": os.environ.get(kunci, bawaan),
            "category": "PARADISE",
            "is_encrypted": False,
        }
        for kunci, bawaan in SAKLAR_BAWAAN.items()
    ),
    *(
        {
            "key": kunci,
            "value": os.environ.get(kunci, str(bawaan)),
            "category": "PARADISE",
            "is_encrypted": False,
        }
        for kunci, (bawaan, _, _) in SETELAN_ANGKA.items()
    ),
    # Sengaja terpisah dari GOOGLE_CLIENT_ID milik login Google: scope-nya beda,
    # dan menggabungkannya berarti setiap orang yang login lewat Google ikut
    # dimintai izin kalender.
    {
        "key": "GOOGLE_CALENDAR_CLIENT_ID",
        "value": os.environ.get("GOOGLE_CALENDAR_CLIENT_ID"),
        "category": "GOOGLE_CALENDAR",
        "is_encrypted": False,
    },
    {
        "key": "GOOGLE_CALENDAR_CLIENT_SECRET",
        "value": os.environ.get("GOOGLE_CALENDAR_CLIENT_SECRET"),
        "category": "GOOGLE_CALENDAR",
        "is_encrypted": True,
    },
]
