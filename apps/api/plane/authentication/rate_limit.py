# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.authentication.adapter.error import (
    AuthenticationException,
    AUTHENTICATION_ERROR_CODES,
)
from plane.utils import aturan
from plane.utils.aturan.area_keamanan import EMAIL_CHANGE_CODES_PER_HOUR, LOGIN_ATTEMPTS_PER_MINUTE


class AuthenticationThrottle(AnonRateThrottle):
    # Paradise: rate comes from God Mode (LOGIN_ATTEMPTS_PER_MINUTE, seeded from
    # the old AUTHENTICATION_RATE_LIMIT env). DRF builds a throttle per request
    # and calls get_rate() because no class `rate` is set, so a change applies live.
    scope = "authentication"

    def get_rate(self):
        return f"{aturan.get_int(LOGIN_ATTEMPTS_PER_MINUTE)}/minute"

    def throttle_failure_view(self, request, *args, **kwargs):
        try:
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["RATE_LIMIT_EXCEEDED"],
                error_message="RATE_LIMIT_EXCEEDED",
            )
        except AuthenticationException as e:
            return Response(e.get_error_dict(), status=status.HTTP_429_TOO_MANY_REQUESTS)


def authentication_throttle_allows(request):
    """
    Apply AuthenticationThrottle to a plain django.views.View request.

    DRF's throttle_classes only run inside APIView.initial(); the magic
    sign-in / sign-up endpoints extend django.views.View to return
    HttpResponseRedirect from a form POST flow, so they need a manual
    throttle check. Returns True if the request is allowed through,
    False if it should be rejected with a RATE_LIMIT_EXCEEDED error.
    """
    throttle = AuthenticationThrottle()
    # SimpleRateThrottle.allow_request only reads request.META and
    # request.user, both available on a plain Django HttpRequest.
    return throttle.allow_request(request, None)


class EmailVerificationThrottle(UserRateThrottle):
    """
    Throttle for email verification code generation, per user.
    Paradise: the hourly budget is EMAIL_CHANGE_CODES_PER_HOUR in God Mode.
    """

    scope = "email_verification"

    def get_rate(self):
        return f"{aturan.get_int(EMAIL_CHANGE_CODES_PER_HOUR)}/hour"

    def throttle_failure_view(self, request, *args, **kwargs):
        try:
            raise AuthenticationException(
                error_code=AUTHENTICATION_ERROR_CODES["RATE_LIMIT_EXCEEDED"],
                error_message="RATE_LIMIT_EXCEEDED",
            )
        except AuthenticationException as e:
            return Response(e.get_error_dict(), status=status.HTTP_429_TOO_MANY_REQUESTS)
