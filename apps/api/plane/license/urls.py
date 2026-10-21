# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.license.api.views import (
    EmailCredentialCheckEndpoint,
    InstanceAdminEndpoint,
    InstanceAdminSignInEndpoint,
    InstanceAdminSignUpEndpoint,
    InstanceConfigurationEndpoint,
    DisableEmailFeatureEndpoint,
    InstanceEndpoint,
    SignUpScreenVisitedEndpoint,
    InstanceAdminUserMeEndpoint,
    InstanceAdminSignOutEndpoint,
    InstanceAdminUserSessionEndpoint,
    InstanceWorkSpaceAvailabilityCheckEndpoint,
    InstanceWorkSpaceEndpoint,
    InstanceAuditLogEndpoint,
    InstanceTrashEndpoint,
    InstanceMemberEndpoint,
    InstanceActivityEndpoint,
    InstanceLoginHistoryEndpoint,
    InstanceMemberSessionEndpoint,
)
from plane.license.api.views.hierarki import InstanceHierarkiEndpoint
from plane.license.api.views.divisi import InstanceDivisiAnggotaEndpoint
from plane.license.api.views.organisasi import (
    InstanceDepartemenDariProjectEndpoint,
    InstanceDepartemenEndpoint,
    InstanceDivisiEndpoint,
    InstanceOrganisasiEndpoint,
)

urlpatterns = [
    path("", InstanceEndpoint.as_view(), name="instance"),
    path("admins/", InstanceAdminEndpoint.as_view(), name="instance-admins"),
    path("admins/me/", InstanceAdminUserMeEndpoint.as_view(), name="instance-admins"),
    path(
        "admins/session/",
        InstanceAdminUserSessionEndpoint.as_view(),
        name="instance-admin-session",
    ),
    path(
        "admins/sign-out/",
        InstanceAdminSignOutEndpoint.as_view(),
        name="instance-admins",
    ),
    path("admins/<uuid:pk>/", InstanceAdminEndpoint.as_view(), name="instance-admins"),
    path(
        "configurations/",
        InstanceConfigurationEndpoint.as_view(),
        name="instance-configuration",
    ),
    path(
        "configurations/disable-email-feature/",
        DisableEmailFeatureEndpoint.as_view(),
        name="disable-email-configuration",
    ),
    path(
        "admins/sign-in/",
        InstanceAdminSignInEndpoint.as_view(),
        name="instance-admin-sign-in",
    ),
    path(
        "admins/sign-up/",
        InstanceAdminSignUpEndpoint.as_view(),
        name="instance-admin-sign-in",
    ),
    path(
        "admins/sign-up-screen-visited/",
        SignUpScreenVisitedEndpoint.as_view(),
        name="instance-sign-up",
    ),
    path(
        "email-credentials-check/",
        EmailCredentialCheckEndpoint.as_view(),
        name="email-credential-check",
    ),
    path(
        "workspace-slug-check/",
        InstanceWorkSpaceAvailabilityCheckEndpoint.as_view(),
        name="instance-workspace-availability",
    ),
    path("workspaces/", InstanceWorkSpaceEndpoint.as_view(), name="instance-workspace"),
    # Kustomisasi Paradise. Menggantikan endpoint workspace-level lama
    # di app/urls/paradise.py: jejak audit sengaja hanya terbaca dari God Mode.
    path("audit-logs/", InstanceAuditLogEndpoint.as_view(), name="instance-audit-logs"),
    # TPA, tong sampah lintas project, hanya Super Admin.
    path("trash/", InstanceTrashEndpoint.as_view(), name="instance-trash"),
    path(
        "trash/<str:trash_type>/<uuid:pk>/",
        InstanceTrashEndpoint.as_view(),
        name="instance-trash-item",
    ),
    # Kelola member, satu-satunya pintu masuk akun selama signup mati.
    path("members/", InstanceMemberEndpoint.as_view(), name="instance-members"),
    path("members/<uuid:pk>/", InstanceMemberEndpoint.as_view(), name="instance-member"),
    # Paradise: pemantauan sesi & aktivitas
    path(
        "members/<uuid:pk>/sessions/",
        InstanceMemberSessionEndpoint.as_view(),
        name="instance-member-sessions",
    ),
    path("activity/", InstanceActivityEndpoint.as_view(), name="instance-activity"),
    path(
        "login-history/",
        InstanceLoginHistoryEndpoint.as_view(),
        name="instance-login-history",
    ),
    # Hierarki organisasi, BACA-SAJA: jenjang, pengawasan, dan siapa yang belum
    # punya atasan. Yang mengisinya belum diputuskan user, jadi belum ada endpoint
    # tulis -- lihat .herdr/hierarki-desain.md pertanyaan #4.
    path("hierarki/", InstanceHierarkiEndpoint.as_view(), name="instance-hierarki"),
    # Keanggotaan divisi (tambah/hapus/ubah peran) dari God Mode. Endpoint
    # project biasa memeriksa keanggotaan PEMANGGIL per divisi — dari sini rapuh
    # (403 di tengah simpan bertahap). Satu panggilan atomik di sini.
    path("divisi-anggota/", InstanceDivisiAnggotaEndpoint.as_view(), name="instance-divisi-anggota"),
    # Struktur divisi -> departemen -> project (KEP-29).
    path("organisasi/", InstanceOrganisasiEndpoint.as_view(), name="instance-organisasi"),
    path("organisasi/divisi/", InstanceDivisiEndpoint.as_view(), name="instance-organisasi-divisi"),
    path("organisasi/divisi/<uuid:pk>/", InstanceDivisiEndpoint.as_view(), name="instance-organisasi-divisi-detail"),
    # Literal "dari-project" sebelum <uuid:pk> supaya tidak dibaca sebagai id.
    path(
        "organisasi/departemen/dari-project/",
        InstanceDepartemenDariProjectEndpoint.as_view(),
        name="instance-organisasi-departemen-dari-project",
    ),
    path("organisasi/departemen/", InstanceDepartemenEndpoint.as_view(), name="instance-organisasi-departemen"),
    path(
        "organisasi/departemen/<uuid:pk>/",
        InstanceDepartemenEndpoint.as_view(),
        name="instance-organisasi-departemen-detail",
    ),
]
