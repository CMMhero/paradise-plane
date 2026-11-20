# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
from urllib.parse import urlsplit

# Django imports
from django.conf import settings
from django.core.exceptions import DisallowedHost, ImproperlyConfigured
from django.http import HttpRequest

# Third party imports
from rest_framework.request import Request

# Module imports
from plane.utils.ip_address import get_client_ip

_DEFAULT_PORTS = {"http": 80, "https": 443}


def normalize_origin(url: str | None) -> str | None:
    """Reduce a URL to `scheme://host[:port]`, lowercased, default port dropped.

    Returns None for anything that is not an absolute http(s) URL, including
    the literal `null` browsers send as Origin from privacy-sensitive contexts.
    """
    if not url or not isinstance(url, str):
        return None
    try:
        parts = urlsplit(url.strip())
        port = parts.port
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if scheme not in _DEFAULT_PORTS or not host:
        return None
    if ":" in host:  # IPv6 literal
        host = f"[{host}]"
    if port and port != _DEFAULT_PORTS[scheme]:
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def trusted_origins() -> set[str]:
    """Every origin the operator configured this instance to be served from."""
    candidates = [
        settings.WEB_URL,
        settings.APP_BASE_URL,
        settings.ADMIN_BASE_URL,
        settings.SPACE_BASE_URL,
        *(getattr(settings, "CORS_ALLOWED_ORIGINS", None) or []),
    ]
    return {origin for origin in map(normalize_origin, candidates) if origin}


def request_origin(request: Request | HttpRequest) -> str | None:
    """The origin the browser is actually on, if it is one we are configured for.

    A session cookie belongs to the host that set it. Sending someone who signed
    in at https://example.com on to http://10.0.0.5 (or the other way round)
    lands them on a host with no cookie, or on one they cannot reach at all, so
    redirects go back to where the browser came from.

    Checked in order:
    1. The `Origin` header. Browsers send it on every form POST, and it names
       the page that submitted the form, which also covers deployments where
       the admin app and the API live on different hosts.
    2. The request's own scheme and host, as Django sees them behind the proxy
       (`SECURE_PROXY_SSL_HEADER` supplies https).

    Only origins in `trusted_origins()` are returned. A forged Host or Origin
    header can at most pick another origin the operator already configured,
    never an arbitrary site, so this cannot become an open redirect.
    """
    trusted = trusted_origins()
    if not trusted:
        return None

    django_request = getattr(request, "_request", request)

    origin = normalize_origin(django_request.META.get("HTTP_ORIGIN"))
    if origin in trusted:
        return origin

    try:
        own = normalize_origin(f"{django_request.scheme}://{django_request.get_host()}")
    except DisallowedHost:
        return None
    if own in trusted:
        return own
    return None


def _normalize_base_path(path: object, default: str) -> str:
    if not isinstance(path, str):
        path = default
    if not path.startswith("/"):
        path = "/" + path
    if not path.endswith("/"):
        path += "/"
    return path


def resolve_base_host(
    request: Request | HttpRequest,
    base_origin: str | None,
    is_admin: bool = False,
    is_space: bool = False,
    is_app: bool = False,
) -> str:
    """Shared body of both `base_host` helpers. `base_origin` is WEB_URL or APP_BASE_URL."""
    # Admin redirection. The origin the browser is on wins over ADMIN_BASE_URL,
    # which stays the fallback for requests that carry no trusted origin.
    if is_admin:
        admin_base_path = _normalize_base_path(getattr(settings, "ADMIN_BASE_PATH", None), "/god-mode/")
        origin = request_origin(request) or settings.ADMIN_BASE_URL or base_origin
        return origin.rstrip("/") + admin_base_path

    # Space redirection, same rule as admin.
    if is_space:
        space_base_path = _normalize_base_path(getattr(settings, "SPACE_BASE_PATH", None), "/spaces/")
        origin = request_origin(request) or settings.SPACE_BASE_URL or base_origin
        return origin.rstrip("/") + space_base_path

    # App Redirection
    if is_app:
        if settings.APP_BASE_URL:
            return settings.APP_BASE_URL
        else:
            return base_origin

    return base_origin


def base_host(
    request: Request | HttpRequest,
    is_admin: bool = False,
    is_space: bool = False,
    is_app: bool = False,
) -> str:
    """Utility function to return host / origin from the request"""
    # Calculate the base origin from request
    base_origin = settings.WEB_URL or settings.APP_BASE_URL

    if not base_origin:
        raise ImproperlyConfigured("APP_BASE_URL or WEB_URL is not set")

    return resolve_base_host(request, base_origin, is_admin=is_admin, is_space=is_space, is_app=is_app)


def user_ip(request: Request | HttpRequest) -> str:
    return get_client_ip(request=request)
