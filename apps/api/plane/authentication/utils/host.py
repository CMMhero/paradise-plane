# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.conf import settings
from django.http import HttpRequest

# Third party imports
from rest_framework.request import Request

# Module imports
from plane.utils.host import resolve_base_host
from plane.utils.ip_address import get_client_ip


def base_host(
    request: Request | HttpRequest,
    is_admin: bool = False,
    is_space: bool = False,
    is_app: bool = False,
) -> str:
    """Utility function to return host / origin from the request.

    Same rules as `plane.utils.host.base_host`, except that an unset
    WEB_URL / APP_BASE_URL does not raise here.
    """
    base_origin = settings.WEB_URL or settings.APP_BASE_URL
    return resolve_base_host(request, base_origin, is_admin=is_admin, is_space=is_space, is_app=is_app)


def user_ip(request: Request | HttpRequest) -> str:
    return get_client_ip(request=request)
