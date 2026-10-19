# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.views import View
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.utils import timezone

# Module imports
from plane.authentication.utils.host import user_ip, base_host
from plane.db.models import LoginActivity, User


class SignOutAuthEndpoint(View):
    def post(self, request):
        # Get user
        try:
            user = User.objects.get(pk=request.user.id)
            user.last_logout_ip = user_ip(request=request)
            user.last_logout_time = timezone.now()
            user.save()
            # Jejak logout, dicatat SEBELUM logout(), setelah itu
            # session_key sudah hilang dan pasangannya dengan login tak bisa
            # ditemukan lagi untuk menghitung durasi.
            LoginActivity.catat(
                user=user,
                jenis=LoginActivity.Jenis.LOGOUT,
                request=request,
                permukaan="app",
                session_key=request.session.session_key or "",
            )
            # Log the user out
            logout(request)
            return HttpResponseRedirect(base_host(request=request, is_app=True))
        except Exception:
            return HttpResponseRedirect(base_host(request=request, is_app=True))
