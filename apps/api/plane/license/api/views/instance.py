# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import os

# Django imports
from django.conf import settings

# Third party imports
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# Module imports
from plane.license.audit_godmode import catat_godmode
from plane.app.views import BaseAPIView
from plane.db.models import Workspace
from plane.license.api.permissions import InstanceAdminPermission
from plane.license.api.serializers import InstanceSerializer
from plane.license.models import Instance
from plane.license.utils.instance_value import email_aktif, get_configuration_value
from plane.utils.cache import cache_response, invalidate_cache
from plane.utils import google_calendar as gcal
from plane.utils.saklar_instance import (
    APPROVAL_PENDING_NOT_LATE,
    AUTO_ARCHIVE_DONE_DAYS,
    CHAT_ATTACHMENTS_MAX,
    CHAT_DELETE_WINDOW_HOURS,
    CHAT_EDIT_WINDOW_HOURS,
    CHAT_MESSAGE_MAX_LENGTH,
    OVERDUE_GRACE_DAYS,
    UPLOAD_MAX_MB,
    modul_aktif,
    saklar_aktif,
    setelan_angka,
)
from plane.utils.setelan_instance import OFFICE_TIMEZONE, efektif
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control


class InstanceEndpoint(BaseAPIView):
    def get_permissions(self):
        if self.request.method == "PATCH":
            return [InstanceAdminPermission()]
        return [AllowAny()]

    @cache_response(60 * 60 * 2, user=False)
    @method_decorator(cache_control(private=True, max_age=12))
    def get(self, request):
        instance = Instance.objects.first()

        # get the instance
        if instance is None:
            return Response(
                {"is_activated": False, "is_setup_done": False},
                status=status.HTTP_200_OK,
            )
        # Return instance
        serializer = InstanceSerializer(instance)
        data = serializer.data
        data["is_activated"] = True
        # Get all the configuration
        (
            ENABLE_SIGNUP,
            DISABLE_WORKSPACE_CREATION,
            IS_GOOGLE_ENABLED,
            IS_GITHUB_ENABLED,
            GITHUB_APP_NAME,
            IS_GITLAB_ENABLED,
            IS_GITEA_ENABLED,
            EMAIL_HOST,
            ENABLE_MAGIC_LINK_LOGIN,
            ENABLE_EMAIL_PASSWORD,
            SLACK_CLIENT_ID,
            POSTHOG_API_KEY,
            POSTHOG_HOST,
            UNSPLASH_ACCESS_KEY,
            LLM_API_KEY,
        ) = get_configuration_value(
            [
                {
                    "key": "ENABLE_SIGNUP",
                    "default": os.environ.get("ENABLE_SIGNUP", "1"),
                },
                {
                    "key": "DISABLE_WORKSPACE_CREATION",
                    "default": os.environ.get("DISABLE_WORKSPACE_CREATION", "0"),
                },
                {
                    "key": "IS_GOOGLE_ENABLED",
                    "default": os.environ.get("IS_GOOGLE_ENABLED", "0"),
                },
                {
                    "key": "IS_GITHUB_ENABLED",
                    "default": os.environ.get("IS_GITHUB_ENABLED", "0"),
                },
                {
                    "key": "GITHUB_APP_NAME",
                    "default": os.environ.get("GITHUB_APP_NAME", ""),
                },
                {
                    "key": "IS_GITLAB_ENABLED",
                    "default": os.environ.get("IS_GITLAB_ENABLED", "0"),
                },
                {
                    "key": "IS_GITEA_ENABLED",
                    "default": os.environ.get("IS_GITEA_ENABLED", "0"),
                },
                {"key": "EMAIL_HOST", "default": os.environ.get("EMAIL_HOST", "")},
                {
                    "key": "ENABLE_MAGIC_LINK_LOGIN",
                    "default": os.environ.get("ENABLE_MAGIC_LINK_LOGIN", "0"),
                },
                {
                    "key": "ENABLE_EMAIL_PASSWORD",
                    "default": os.environ.get("ENABLE_EMAIL_PASSWORD", "1"),
                },
                {
                    "key": "SLACK_CLIENT_ID",
                    "default": os.environ.get("SLACK_CLIENT_ID", None),
                },
                {
                    "key": "POSTHOG_API_KEY",
                    "default": os.environ.get("POSTHOG_API_KEY", None),
                },
                {
                    "key": "POSTHOG_HOST",
                    "default": os.environ.get("POSTHOG_HOST", None),
                },
                {
                    "key": "UNSPLASH_ACCESS_KEY",
                    "default": os.environ.get("UNSPLASH_ACCESS_KEY", ""),
                },
                {
                    "key": "LLM_API_KEY",
                    "default": os.environ.get("LLM_API_KEY", ""),
                },
            ]
        )

        data = {}
        # Authentication
        data["enable_signup"] = ENABLE_SIGNUP == "1"
        data["is_workspace_creation_disabled"] = DISABLE_WORKSPACE_CREATION == "1"
        data["is_google_enabled"] = IS_GOOGLE_ENABLED == "1"
        data["is_github_enabled"] = IS_GITHUB_ENABLED == "1"
        data["is_gitlab_enabled"] = IS_GITLAB_ENABLED == "1"
        data["is_gitea_enabled"] = IS_GITEA_ENABLED == "1"
        data["is_magic_login_enabled"] = ENABLE_MAGIC_LINK_LOGIN == "1"
        data["is_email_password_enabled"] = ENABLE_EMAIL_PASSWORD == "1"

        # Bidang kendali. Diumumkan supaya God Mode bisa menyembunyikan menu
        # Owner Panel di instance yang bukan milik pemilik produk. Menu yang
        # menuju halaman mati di tiap instance pasang-sendiri adalah menu yang
        # membuat orang mengira produknya rusak.
        data["is_control_plane_enabled"] = bool(getattr(settings, "ENABLE_CONTROL_PLANE", False))

        # Modul yang dinyalakan/dimatikan Super Admin di God Mode > Features.
        # apps/web menyembunyikan menu dan menjaga halamannya berdasarkan ini.
        data["paradise_modules"] = modul_aktif()

        # Tenggang terlambat (God Mode > Features). apps/web memakainya untuk
        # menentukan kapan Due date tampil merah, sama dengan hitungan server.
        data["paradise_overdue_grace_days"] = setelan_angka(OVERDUE_GRACE_DAYS)

        # KEP-84: tugas yang menunggu persetujuan selesai tidak dihitung terlambat.
        # apps/web memakainya supaya Due date tugas seperti itu tidak merah.
        data["paradise_approval_pending_not_late"] = saklar_aktif(APPROVAL_PENDING_NOT_LATE)

        # Umur maksimum pesan obrolan yang masih bisa dihapus (God Mode > Features).
        # apps/web menyembunyikan tombol hapus sesudahnya; server tetap menolak.
        data["paradise_chat_delete_window_hours"] = setelan_angka(CHAT_DELETE_WINDOW_HOURS)

        # Batas yang dijaga server dan perlu diketahui web sebelum mengirim
        # (KEP-83, God Mode). Server tetap yang menolak; ini hanya supaya web
        # memberi tahu lebih dulu, bukan sesudah unggahan 40 MB gagal.
        # Batas byte yang benar-benar dijaga server (plan_limits.batas_unggah_byte):
        # di bawaan = settings.FILE_SIZE_LIMIT apa adanya, termasuk env yang bukan
        # kelipatan MiB. `upload_max_mb` = angka God Mode untuk ditampilkan;
        # `file_size_limit` di bawah adalah batas byte yang dipakai web.
        from plane.utils.plan_limits import batas_unggah_byte

        batas_unggah = batas_unggah_byte()
        upload_max_mb = setelan_angka(UPLOAD_MAX_MB)
        data["paradise_limits"] = {
            "upload_max_mb": upload_max_mb,
            "chat_message_max_length": setelan_angka(CHAT_MESSAGE_MAX_LENGTH),
            "chat_attachments_max": setelan_angka(CHAT_ATTACHMENTS_MAX),
            "chat_edit_window_hours": setelan_angka(CHAT_EDIT_WINDOW_HOURS),
            "auto_archive_done_days": setelan_angka(AUTO_ARCHIVE_DONE_DAYS),
            "chat_delete_window_hours": setelan_angka(CHAT_DELETE_WINDOW_HOURS),
            "office_timezone": efektif(OFFICE_TIMEZONE),
        }

        # Bawaan project baru (God Mode > Workspaces > New project defaults).
        # Formulir "Create project" di apps/web mengisi dirinya dari sini.
        from plane.utils.bawaan_project import baca_bawaan as bawaan_project

        data["paradise_project_defaults"] = bawaan_project()

        # Github app name
        data["github_app_name"] = str(GITHUB_APP_NAME)

        # Slack client
        data["slack_client_id"] = SLACK_CLIENT_ID

        # Posthog
        data["posthog_api_key"] = POSTHOG_API_KEY
        data["posthog_host"] = POSTHOG_HOST

        # Unsplash
        data["has_unsplash_configured"] = bool(UNSPLASH_ACCESS_KEY)

        # Open AI settings
        data["has_llm_configured"] = bool(LLM_API_KEY)

        # Google Calendar: tanpa client ID + secret di God Mode (atau env), tab
        # Connections di setelan profil disembunyikan. Tombol Connect yang mati
        # terlihat seperti aplikasi rusak bagi orang yang tak bisa mengisinya.
        gcal_id, gcal_secret = gcal.kredensial()
        data["has_google_calendar_configured"] = bool(gcal_id and gcal_secret)

        # File size settings. Paradise: batas byte yang sama dengan yang ditolak
        # server (UPLOAD_MAX_MB dari God Mode, dijepit batas proxy FILE_SIZE_LIMIT).
        data["file_size_limit"] = float(batas_unggah)

        # is smtp configured. Paradise: `email_aktif()` = EMAIL_HOST terisi.
        data["is_smtp_configured"] = email_aktif()

        # Base URL
        data["admin_base_url"] = settings.ADMIN_BASE_URL
        data["space_base_url"] = settings.SPACE_BASE_URL
        data["app_base_url"] = settings.APP_BASE_URL

        data["instance_changelog_url"] = settings.INSTANCE_CHANGELOG_URL
        data["is_self_managed"] = settings.IS_SELF_MANAGED

        instance_data = serializer.data
        instance_data["workspaces_exist"] = Workspace.objects.count() >= 1

        response_data = {"config": data, "instance": instance_data}
        return Response(response_data, status=status.HTTP_200_OK)

    @invalidate_cache(path="/api/instances/", user=False)
    def patch(self, request):
        # Get the instance
        instance = Instance.objects.first()
        serializer = InstanceSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            catat_godmode(
                request,
                kind="instance_profile",
                label="Instance profile",
                object_pk=str(instance.pk),
                changes={"fields": ["", ", ".join(sorted(request.data))]},
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SignUpScreenVisitedEndpoint(BaseAPIView):
    permission_classes = [AllowAny]

    @invalidate_cache(path="/api/instances/", user=False)
    def post(self, request):
        instance = Instance.objects.first()
        if instance is None:
            return Response(
                {"error": "Instance is not configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.is_signup_screen_visited = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
