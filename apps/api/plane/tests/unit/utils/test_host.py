# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Where god-mode and space redirects send the browser.

The production bug these pin down: the server ran with
WEB_URL=https://space.paradiseperkasa.com but ADMIN_BASE_URL=http://128.159.110.5,
so a successful god-mode sign-in from the public domain redirected to the raw
IP. The admin session cookie had been set on the domain, so the IP either was
unreachable or showed the login page again.
"""

import pytest
from django.test import RequestFactory

from plane.authentication.utils.host import base_host as auth_base_host
from plane.utils.host import base_host, normalize_origin, request_origin

DOMAIN = "https://space.paradiseperkasa.com"
IP = "http://128.159.110.5"

# The values read off the production .env on 2026-11-20.
PRODUCTION = dict(
    ALLOWED_HOSTS=["*"],
    SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
    WEB_URL=DOMAIN,
    APP_BASE_URL=DOMAIN,
    ADMIN_BASE_URL=IP,
    SPACE_BASE_URL=IP,
    CORS_ALLOWED_ORIGINS=[DOMAIN, IP],
    ADMIN_BASE_PATH="/god-mode/",
    SPACE_BASE_PATH="/spaces/",
)

SIGN_IN = "/api/instances/admins/sign-in/"


@pytest.fixture
def production(settings):
    """Production values, restored by pytest-django after each test."""
    for name, value in PRODUCTION.items():
        setattr(settings, name, value)
    return settings


def _from_domain(**extra):
    """A form POST from the public site, as Caddy forwards it to the api."""
    headers = dict(
        HTTP_HOST="space.paradiseperkasa.com",
        HTTP_X_FORWARDED_PROTO="https",
        HTTP_ORIGIN=DOMAIN,
    )
    headers.update(extra)
    return RequestFactory().post(SIGN_IN, **headers)


def _from_lan(**extra):
    headers = dict(HTTP_HOST="128.159.110.5", HTTP_X_FORWARDED_PROTO="http", HTTP_ORIGIN=IP)
    headers.update(extra)
    return RequestFactory().post(SIGN_IN, **headers)


@pytest.mark.unit
@pytest.mark.usefixtures("production")
class TestAdminRedirectFollowsTheBrowser:
    @pytest.mark.parametrize("helper", [base_host, auth_base_host])
    def test_public_domain_sign_in_stays_on_the_domain(self, helper):
        assert helper(request=_from_domain(), is_admin=True) == f"{DOMAIN}/god-mode/"

    @pytest.mark.parametrize("helper", [base_host, auth_base_host])
    def test_lan_sign_in_by_ip_stays_on_the_ip(self, helper):
        assert helper(request=_from_lan(), is_admin=True) == f"{IP}/god-mode/"

    def test_without_origin_header_the_request_host_is_used(self):
        request = _from_domain()
        del request.META["HTTP_ORIGIN"]
        assert base_host(request=request, is_admin=True) == f"{DOMAIN}/god-mode/"

    def test_scheme_comes_from_the_proxy_header(self):
        # Without X-Forwarded-Proto Django sees plain http, which is not a
        # configured origin for the domain, so it falls back to the setting.
        request = _from_domain()
        del request.META["HTTP_ORIGIN"]
        del request.META["HTTP_X_FORWARDED_PROTO"]
        assert base_host(request=request, is_admin=True) == f"{IP}/god-mode/"

    def test_space_redirects_follow_the_same_rule(self):
        assert base_host(request=_from_domain(), is_space=True) == f"{DOMAIN}/spaces/"
        assert base_host(request=_from_lan(), is_space=True) == f"{IP}/spaces/"

    def test_app_redirect_is_unchanged(self):
        assert base_host(request=_from_lan(), is_app=True) == DOMAIN
        assert base_host(request=_from_lan()) == DOMAIN


@pytest.mark.unit
@pytest.mark.usefixtures("production")
class TestForgedHeadersCannotRedirectElsewhere:
    def test_untrusted_origin_and_host_fall_back_to_the_setting(self):
        request = _from_domain(HTTP_ORIGIN="https://evil.example", HTTP_HOST="evil.example")
        assert base_host(request=request, is_admin=True) == f"{IP}/god-mode/"

    def test_untrusted_origin_falls_through_to_a_trusted_host(self):
        request = _from_domain(HTTP_ORIGIN="https://evil.example")
        assert base_host(request=request, is_admin=True) == f"{DOMAIN}/god-mode/"

    def test_null_origin_is_ignored(self):
        request = _from_domain(HTTP_ORIGIN="null")
        assert request_origin(request) == DOMAIN

    def test_disallowed_host_does_not_raise(self, production):
        production.ALLOWED_HOSTS = ["space.paradiseperkasa.com"]
        request = _from_domain(HTTP_ORIGIN="https://evil.example", HTTP_HOST="evil.example")
        assert request_origin(request) is None
        assert base_host(request=request, is_admin=True) == f"{IP}/god-mode/"


@pytest.mark.unit
class TestConfigurationFallbacks:
    def test_unset_admin_url_falls_back_to_web_url(self, production):
        production.ADMIN_BASE_URL = None
        production.SPACE_BASE_URL = None
        production.CORS_ALLOWED_ORIGINS = []
        request = _from_lan()  # the IP is no longer a configured origin
        assert base_host(request=request, is_admin=True) == f"{DOMAIN}/god-mode/"
        assert base_host(request=request, is_space=True) == f"{DOMAIN}/spaces/"

    def test_trailing_slash_and_bare_path_do_not_double_up(self, production):
        production.ADMIN_BASE_URL = f"{DOMAIN}/"
        production.ADMIN_BASE_PATH = "god-mode"
        request = RequestFactory().post(SIGN_IN, HTTP_HOST="internal-api:8000")
        assert base_host(request=request, is_admin=True) == f"{DOMAIN}/god-mode/"

    def test_split_admin_host_is_taken_from_the_origin_header(self, production):
        # Admin SPA on its own host posting to the API on the app host.
        production.WEB_URL = "https://app.example.com"
        production.APP_BASE_URL = "https://app.example.com"
        production.ADMIN_BASE_URL = "https://admin.example.com"
        production.CORS_ALLOWED_ORIGINS = ["https://app.example.com", "https://admin.example.com"]
        request = RequestFactory().post(
            SIGN_IN,
            HTTP_HOST="app.example.com",
            HTTP_X_FORWARDED_PROTO="https",
            HTTP_ORIGIN="https://admin.example.com",
        )
        assert base_host(request=request, is_admin=True) == "https://admin.example.com/god-mode/"


@pytest.mark.unit
class TestNormalizeOrigin:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("https://Space.Example.com/god-mode/", "https://space.example.com"),
            ("https://example.com:443", "https://example.com"),
            ("http://example.com:80/", "http://example.com"),
            ("http://10.0.0.5:8080", "http://10.0.0.5:8080"),
            ("http://[::1]:3000", "http://[::1]:3000"),
            (" https://example.com ", "https://example.com"),
            ("null", None),
            ("", None),
            (None, None),
            ("ftp://example.com", None),
            ("example.com", None),
            ("http://example.com:notaport", None),
        ],
    )
    def test_cases(self, raw, expected):
        assert normalize_origin(raw) == expected
