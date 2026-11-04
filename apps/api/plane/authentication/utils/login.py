# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.contrib.auth import login
from django.conf import settings

# Module imports
from plane.utils.host import base_host
from plane.utils.ip_address import get_client_ip
from plane.db.models import LoginActivity


_DETIK_SEHARI = 86400


def umur_sesi_detik():
    """Umur sesi login aplikasi dalam detik, dari SESSION_DAYS (KEP-83).

    Selama SESSION_DAYS sama dengan bawaannya (env lama SESSION_COOKIE_AGE
    dibulatkan ke hari lalu dijepit 1..90, lihat `SETELAN_ANGKA`), detik env itu
    yang dipakai apa adanya. Jadi deploy tidak mengubah umur sesi, termasuk env
    yang bukan kelipatan sehari, di bawah sehari (mis. 1800 detik), atau di atas
    90 hari. Baru kalau Super Admin memilih angka lain, angka hari itu yang berlaku.
    """
    from plane.utils.saklar_instance import SESSION_DAYS, setelan_angka  # noqa: PLC0415

    hari = setelan_angka(SESSION_DAYS)
    # Dihitung dari settings (sumber env yang sama dengan benih SETELAN_ANGKA),
    # supaya bawaan dan detik env selalu sepasang.
    bawaan = max(1, min(settings.SESSION_COOKIE_AGE // _DETIK_SEHARI, 90))
    if hari == bawaan:
        return settings.SESSION_COOKIE_AGE
    return hari * _DETIK_SEHARI


def user_login(request, user, is_app=False, is_admin=False, is_space=False):
    login(request=request, user=user)

    # If is admin cookie set the custom age
    if is_admin:
        request.session.set_expiry(settings.ADMIN_SESSION_COOKIE_AGE)
    else:
        # Paradise (KEP-83): umur sesi aplikasi & space dari God Mode (SESSION_DAYS).
        # Hanya dipasang saat login, jadi sesi yang sudah ada tetap pada umurnya.
        # Sesi God Mode tetap diatur env ADMIN_SESSION_COOKIE_AGE di atas.
        request.session.set_expiry(umur_sesi_detik())

    device_info = {
        "user_agent": request.META.get("HTTP_USER_AGENT", ""),
        "ip_address": get_client_ip(request=request),
        "domain": base_host(request=request, is_app=is_app, is_admin=is_admin, is_space=is_space),
    }
    request.session["device_info"] = device_info
    request.session.save()

    # Jejak login. Dicatat SESUDAH session.save() supaya session_key
    # sudah pasti final, Django membuat ulang kunci saat login (cycle_key),
    # jadi membaca sebelum save() memberi kunci lama dan pemasangan
    # login->logout untuk menghitung durasi jadi meleset.
    LoginActivity.catat(
        user=user,
        jenis=LoginActivity.Jenis.LOGIN,
        request=request,
        medium=getattr(user, "last_login_medium", "") or "",
        permukaan="admin" if is_admin else ("space" if is_space else "app"),
        session_key=request.session.session_key or "",
    )
    return
