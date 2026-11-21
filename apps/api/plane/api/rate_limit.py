# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework.throttling import SimpleRateThrottle

# Module imports
from plane.utils import aturan
from plane.utils.aturan.area_keamanan import API_KEY_REQUESTS_PER_MINUTE


class ApiKeyRateThrottle(SimpleRateThrottle):
    scope = "api_key"

    def get_rate(self):
        # Paradise: God Mode API_KEY_REQUESTS_PER_MINUTE (seeded from the old
        # API_KEY_RATE_LIMIT env), read per request because no class `rate` is set.
        return f"{aturan.get_int(API_KEY_REQUESTS_PER_MINUTE)}/minute"

    def get_cache_key(self, request, view):
        # Retrieve the API key from the request header
        api_key = request.headers.get("X-Api-Key")
        if not api_key:
            return None  # Allow the request if there's no API key

        # Use the API key as part of the cache key
        return f"{self.scope}:{api_key}"

    def allow_request(self, request, view):
        allowed = super().allow_request(request, view)

        if allowed:
            now = self.timer()
            # Calculate the remaining limit and reset time
            history = self.cache.get(self.key, [])

            # Remove old histories
            while history and history[-1] <= now - self.duration:
                history.pop()

            # Calculate the requests
            num_requests = len(history)

            # Check available requests
            available = self.num_requests - num_requests

            # Unix timestamp for when the rate limit will reset
            reset_time = int(now + self.duration)

            # Add headers
            request.META["X-RateLimit-Remaining"] = max(0, available)
            request.META["X-RateLimit-Reset"] = reset_time

        return allowed
