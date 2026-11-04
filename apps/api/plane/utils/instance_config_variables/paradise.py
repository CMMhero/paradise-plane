# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: saklar fitur di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Benih untuk `configure_instance`: env hanya dibaca saat barisnya belum ada.
# Sesudah itu nilainya diatur dari God Mode > Fitur & otomasi.
#
# Kunci KEP-83 tidak punya env dengan namanya sendiri (`env_benih` mengembalikan
# bawaan untuk mereka): barisnya lahir berisi bawaan kode, yang untuk
# UPLOAD_MAX_MB dan SESSION_DAYS sudah berbenih env lama FILE_SIZE_LIMIT dan
# SESSION_COOKIE_AGE (lihat plane/utils/saklar_instance.py).

import os

from plane.utils.saklar_instance import SAKLAR_BAWAAN, SETELAN_ANGKA, env_benih
from plane.utils.setelan_instance import SETELAN_TEKS

paradise_config_variables = [
    *(
        {
            "key": kunci,
            "value": env_benih(kunci, bawaan),
            "category": "PARADISE",
            "is_encrypted": False,
        }
        for kunci, bawaan in SAKLAR_BAWAAN.items()
    ),
    *(
        {
            "key": kunci,
            "value": env_benih(kunci, str(bawaan)),
            "category": "PARADISE",
            "is_encrypted": False,
        }
        for kunci, (bawaan, _, _) in SETELAN_ANGKA.items()
    ),
    *(
        {
            "key": kunci,
            "value": bawaan,
            "category": "PARADISE",
            "is_encrypted": False,
        }
        for kunci, (_, bawaan) in SETELAN_TEKS.items()
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
