# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path
from plane.web.views import robots_txt, health_check, corresponding_source

urlpatterns = [
    path("robots.txt", robots_txt),
    # Tawaran kode sumber AGPL-3.0 pasal 13. Jalur ini WAJIB ikut ditambahkan di
    # apps/proxy/Caddyfile.ce: Caddy hanya meneruskan /api/*, /auth/*, dan
    # /static/* ke Django, sisanya jatuh ke aplikasi web.
    path("source/", corresponding_source),
    path("", health_check),
]
