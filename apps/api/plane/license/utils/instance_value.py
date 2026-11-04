# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import os

# Django imports
from django.conf import settings

# Module imports
from plane.license.models import InstanceConfiguration
from plane.license.utils.encryption import decrypt_data


# Helper function to return value from the passed key
def get_configuration_value(keys):
    environment_list = []
    if settings.SKIP_ENV_VAR:
        # Get the configurations
        instance_configuration = InstanceConfiguration.objects.values("key", "value", "is_encrypted")

        for key in keys:
            for item in instance_configuration:
                if key.get("key") == item.get("key"):
                    if item.get("is_encrypted", False):
                        environment_list.append(decrypt_data(item.get("value")))
                    else:
                        environment_list.append(item.get("value"))

                    break
            else:
                environment_list.append(key.get("default"))
    else:
        # Get the configuration from os
        for key in keys:
            environment_list.append(os.environ.get(key.get("key"), key.get("default")))

    return tuple(environment_list)


_BACA_SENDIRI = object()


def email_aktif(host=_BACA_SENDIRI) -> bool:
    """Kustomisasi Paradise (KEP-83): satu jawaban untuk "apakah email terkirim".

    Benar kalau EMAIL_HOST terisi. Itulah saklar yang sesungguhnya: tombol
    "matikan email" di God Mode mengosongkan EMAIL_HOST (configuration.py), dan
    sebelum KEP-83 tidak ada kode yang membaca ENABLE_SMTP. Baris ENABLE_SMTP
    tetap ditulis demi kecocokan, tetapi SENGAJA tidak dibaca: benihnya "0",
    sehingga instance yang EMAIL_HOST-nya terisi dari env akan berhenti mengirim
    email diam-diam sesudah deploy kalau saklar itu ikut diperiksa.

    `host` = EMAIL_HOST yang sudah dibaca pemanggil lewat `get_email_configuration()`
    (hemat satu kueri, dan pemanggil yang sedang mengirim memakai host yang sama
    dengan yang diperiksa). Tanpa argumen: dibaca sendiri.
    """
    if host is _BACA_SENDIRI:
        (host,) = get_configuration_value([{"key": "EMAIL_HOST", "default": os.environ.get("EMAIL_HOST", "")}])
    return bool(str(host or "").strip())


def get_email_configuration():
    return get_configuration_value(
        [
            {"key": "EMAIL_HOST", "default": os.environ.get("EMAIL_HOST")},
            {"key": "EMAIL_HOST_USER", "default": os.environ.get("EMAIL_HOST_USER")},
            {
                "key": "EMAIL_HOST_PASSWORD",
                "default": os.environ.get("EMAIL_HOST_PASSWORD"),
            },
            {"key": "EMAIL_PORT", "default": os.environ.get("EMAIL_PORT", 587)},
            {"key": "EMAIL_USE_TLS", "default": os.environ.get("EMAIL_USE_TLS", "1")},
            {"key": "EMAIL_USE_SSL", "default": os.environ.get("EMAIL_USE_SSL", "0")},
            {
                "key": "EMAIL_FROM",
                "default": os.environ.get("EMAIL_FROM", "Team Plane <team@mailer.plane.so>"),
            },
        ]
    )
