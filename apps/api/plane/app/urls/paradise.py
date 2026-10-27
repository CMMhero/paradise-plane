# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: URL fitur kustom
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

# Permintaan lintas divisi sengaja diimpor LANGSUNG dari modulnya, bukan lewat
# barrel `plane.app.views`. Barrel itu berkas upstream; satu baris impor di
# sana adalah divergensi yang harus dibayar di setiap upstream sync, dan modul
# ini sudah terdaftar di `urls/__init__.py` lewat `paradise_urls`.
from plane.app.views.issue.cross_division import (
    DivisiTujuanEndpoint,
    PermintaanLintasDivisiEndpoint,
    RingkasanLintasDivisiEndpoint,
)
from plane.app.views.penempatan_saya import PenempatanSayaEndpoint
from plane.app.views.issue.persetujuan import PenggunaBisaDitugaskanEndpoint, PersetujuanPenugasanEndpoint
from plane.app.views.workspace.organisasi import StrukturOrganisasiEndpoint
from plane.app.views import (
    ProjectTrashEndpoint,
    ChatAnggotaEndpoint,
    ChatCariEndpoint,
    ChatConversationsEndpoint,
    ChatGabungEndpoint,
    ChatIceEndpoint,
    ChatPanggilanTokenEndpoint,
    ChatRuangEndpoint,
    ChatRuangThreadEndpoint,
    ChatLampiranEndpoint,
    ChatPesanEndpoint,
    ChatReaksiEndpoint,
    ChatThreadEndpoint,
    ChatUnreadEndpoint,
    DivisionDashboardEndpoint,
    WorkLogExportEndpoint,
    GoogleCalendarCallbackEndpoint,
    GoogleCalendarConnectEndpoint,
    GoogleCalendarStatusEndpoint,
    InitiativeViewSet,
    PageCanEditEndpoint,
    WikiAccessEndpoint,
    WikiFolderEndpoint,
    WikiMaterialCountEndpoint,
    WikiMaterialEndpoint,
    WikiMaterialPreviewEndpoint,
    WikiMaterialSearchEndpoint,
    WikiPermissionsEndpoint,
    WikiTopicMaterialEndpoint,
    WikiFolderAccessEndpoint,
)

urlpatterns = [
    # Google Calendar. Callback-nya SENGAJA di bawah /api/, bukan /auth/:
    # /auth/ dimiliki berkas URL upstream, dan menyisipkan satu baris di sana
    # menambah permukaan konflik tiap kali upstream sync dijalankan.
    #
    # ⚠️ Nilai persis di bawah ini harus didaftarkan sebagai Authorized redirect
    # URI di Google Cloud Console. Beda satu garis miring pun ditolak dengan
    # `redirect_uri_mismatch`, dan pesannya tidak menyebut bagian mana yang beda:
    #   https://<host>/api/google-calendar/callback/
    path(
        "google-calendar/connect/",
        GoogleCalendarConnectEndpoint.as_view(),
        name="google-calendar-connect",
    ),
    path(
        "google-calendar/callback/",
        GoogleCalendarCallbackEndpoint.as_view(),
        name="google-calendar-callback",
    ),
    path(
        "google-calendar/",
        GoogleCalendarStatusEndpoint.as_view(),
        name="google-calendar-status",
    ),
    path(
        "workspaces/<str:slug>/initiatives/",
        InitiativeViewSet.as_view({"get": "list", "post": "create"}),
        name="initiatives",
    ),
    path(
        "workspaces/<str:slug>/initiatives/<uuid:pk>/",
        InitiativeViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="initiatives",
    ),
    path(
        "workspaces/<str:slug>/initiatives/<uuid:pk>/projects/",
        InitiativeViewSet.as_view({"post": "link_project"}),
        name="initiative-projects",
    ),
    path(
        "workspaces/<str:slug>/initiatives/<uuid:pk>/projects/<uuid:project_id>/",
        InitiativeViewSet.as_view({"delete": "unlink_project"}),
        name="initiative-projects",
    ),
    path(
        "workspaces/<str:slug>/chat/",
        ChatConversationsEndpoint.as_view(),
        name="chat-conversations",
    ),
    # Sebelum pola <uuid:user_id> supaya niatnya terbaca. Tidak akan bentrok
    # walau dibalik: "belum-dibaca" bukan UUID yang sah.
    path(
        "workspaces/<str:slug>/chat/belum-dibaca/",
        ChatUnreadEndpoint.as_view(),
        name="chat-unread",
    ),
    path(
        "workspaces/<str:slug>/chat/lampiran/<uuid:asset_id>/",
        ChatLampiranEndpoint.as_view(),
        name="chat-lampiran",
    ),
    path(
        "workspaces/<str:slug>/chat/cari/",
        ChatCariEndpoint.as_view(),
        name="chat-cari",
    ),
    # Operasi pada satu pesan. Ditaruh sebelum pola <uuid:user_id> supaya
    # "pesan" tidak pernah ditafsirkan sebagai id lawan bicara.
    path(
        "workspaces/<str:slug>/chat/pesan/<uuid:pesan_id>/",
        ChatPesanEndpoint.as_view(),
        name="chat-pesan",
    ),
    path(
        "workspaces/<str:slug>/chat/pesan/<uuid:pesan_id>/reaksi/",
        ChatReaksiEndpoint.as_view(),
        name="chat-reaksi",
    ),
    # Kanal. Ditaruh sebelum pola <uuid:user_id> mengikuti alasan yang sama
    # dengan "pesan" dan "belum-dibaca" di atas: "ruang" bukan UUID yang sah,
    # jadi tidak akan bentrok, tapi urutannya membuat niatnya terbaca.
    path(
        "workspaces/<str:slug>/chat/ice/",
        ChatIceEndpoint.as_view(),
        name="chat-ice",
    ),
    path(
        "workspaces/<str:slug>/chat/ruang/",
        ChatRuangEndpoint.as_view(),
        name="chat-ruang",
    ),
    path(
        "workspaces/<str:slug>/chat/ruang/<uuid:ruang_id>/",
        ChatRuangThreadEndpoint.as_view(),
        name="chat-ruang-isi",
    ),
    path(
        "workspaces/<str:slug>/chat/ruang/<uuid:ruang_id>/panggilan/",
        ChatPanggilanTokenEndpoint.as_view(),
        name="chat-panggilan-token",
    ),
    path(
        "workspaces/<str:slug>/chat/ruang/<uuid:ruang_id>/gabung/",
        ChatGabungEndpoint.as_view(),
        name="chat-ruang-gabung",
    ),
    path(
        "workspaces/<str:slug>/chat/ruang/<uuid:ruang_id>/anggota/",
        ChatAnggotaEndpoint.as_view(),
        name="chat-ruang-anggota",
    ),
    path(
        "workspaces/<str:slug>/chat/<uuid:user_id>/",
        ChatThreadEndpoint.as_view(),
        name="chat-thread",
    ),
    path(
        "workspaces/<str:slug>/divisi-dashboard/",
        DivisionDashboardEndpoint.as_view(),
        name="divisi-dashboard",
    ),
    # Permintaan tugas lintas divisi. "tujuan" dan "ringkasan" ditaruh sebelum
    # "permintaan" (yang tidak punya segmen variabel) supaya niatnya terbaca;
    # tidak akan bentrok karena ketiganya literal.
    # Pengelompokan sidebar divisi -> departemen (KEP-29).
    path(
        "workspaces/<str:slug>/struktur-organisasi/",
        StrukturOrganisasiEndpoint.as_view(),
        name="struktur-organisasi",
    ),
    path(
        "workspaces/<str:slug>/cross-division/tujuan/",
        DivisiTujuanEndpoint.as_view(),
        name="cross-division-tujuan",
    ),
    path(
        "workspaces/<str:slug>/cross-division/ringkasan/",
        RingkasanLintasDivisiEndpoint.as_view(),
        name="cross-division-ringkasan",
    ),
    path(
        "workspaces/<str:slug>/cross-division/permintaan/",
        PermintaanLintasDivisiEndpoint.as_view(),
        name="cross-division-permintaan",
    ),
    path(
        "workspaces/<str:slug>/penempatan-saya/",
        PenempatanSayaEndpoint.as_view(),
        name="penempatan-saya",
    ),
    # Antrean persetujuan penugasan. Baris menunggu tugasnya TETAP muncul (keputusan user
    # 2026-10-15), jadi endpoint ini yang menjadi indikatornya. Literal
    # "bisa-ditugaskan" didaftarkan SEBELUM pola <uuid:pk> supaya tidak
    # ditafsirkan sebagai id permintaan.
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/persetujuan-penugasan/bisa-ditugaskan/",
        PenggunaBisaDitugaskanEndpoint.as_view(),
        name="bisa-ditugaskan",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/persetujuan-penugasan/",
        PersetujuanPenugasanEndpoint.as_view(),
        name="persetujuan-penugasan",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/persetujuan-penugasan/<uuid:pk>/",
        PersetujuanPenugasanEndpoint.as_view(),
        name="persetujuan-penugasan-item",
    ),
    path(
        "workspaces/<str:slug>/worklogs/export/",
        WorkLogExportEndpoint.as_view(),
        name="worklogs-export",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/<uuid:page_id>/can-edit/",
        PageCanEditEndpoint.as_view(),
        name="page-can-edit",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/wiki-access/",
        WikiAccessEndpoint.as_view(),
        name="wiki-access",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/wiki-permissions/",
        WikiPermissionsEndpoint.as_view(),
        name="wiki-permissions",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/wiki/topics/<uuid:page_id>/materials/",
        WikiTopicMaterialEndpoint.as_view(),
        name="wiki-topic-materials",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/wiki/folders/<uuid:page_id>/",
        WikiFolderEndpoint.as_view(),
        name="wiki-folder",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/wiki/material-counts/",
        WikiMaterialCountEndpoint.as_view(),
        name="wiki-material-counts",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/wiki/search/",
        WikiMaterialSearchEndpoint.as_view(),
        name="wiki-material-search",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/wiki/materials/<uuid:asset_id>/",
        WikiMaterialEndpoint.as_view(),
        name="wiki-material",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/wiki/materials/<uuid:asset_id>/preview/",
        WikiMaterialPreviewEndpoint.as_view(),
        name="wiki-material-preview",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/wiki-access/folders/<uuid:folder_id>/",
        WikiFolderAccessEndpoint.as_view(),
        name="wiki-folder-access",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/trash/",
        ProjectTrashEndpoint.as_view(),
        name="project-trash",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/trash/<str:trash_type>/<uuid:pk>/",
        ProjectTrashEndpoint.as_view(),
        name="project-trash-item",
    ),
]
