# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Rute bidang kendali. Hanya terpasang kalau ENABLE_CONTROL_PLANE=1."""

from django.urls import path

from plane.control.views import CompaniesEndpoint, HeartbeatEndpoint
from plane.control.views_billing import InvoicesEndpoint, XenditWebhookEndpoint

urlpatterns = [
    path("heartbeat/", HeartbeatEndpoint.as_view(), name="control-heartbeat"),
    path("companies/", CompaniesEndpoint.as_view(), name="control-companies"),
    path("companies/<str:slug>/", CompaniesEndpoint.as_view(), name="control-company"),
    path(
        "companies/<str:slug>/invoices/",
        InvoicesEndpoint.as_view(),
        name="control-invoices",
    ),
    # Terbuka ke internet. Alamatnya sengaja tidak menebak-nebak nama penyedia
    # berikutnya: kalau suatu saat ada dua penyedia, keduanya punya rute sendiri.
    path("payments/xendit/", XenditWebhookEndpoint.as_view(), name="control-xendit-webhook"),
]
