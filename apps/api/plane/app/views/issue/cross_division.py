# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: permintaan tugas lintas divisi
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Pintu masuk internal untuk meminta bantuan divisi lain.

KEP-02 membuat divisi = project private: anggota divisi lain tidak bisa melihat
apa pun di dalamnya, dan itu memang yang diinginkan. Akibatnya pekerjaan yang
lahir di satu divisi tapi dikerjakan divisi lain tidak punya jalur masuk.

Jalur yang SUDAH ada di sistem ini adalah Intake ([[Business Process]] Alur 2):
divisi peminta mengirim permintaan ke kotak masuk divisi tujuan, admin divisi
tujuan menyaring terima/tolak, yang diterima menjadi work item di papan divisi
tujuan. Mesinnya lengkap -- yang hilang cuma pintunya, karena
`IntakeIssueViewSet.create` (`plane/app/views/intake/base.py:228`) menuntut
keanggotaan project tujuan.

Modul ini menambahkan pintu itu, dan **tidak menyentuh** resolver izin mana pun:

* Peminta TIDAK pernah mendapat `ProjectMember` di project tujuan.
* Pekerja TIDAK pernah mendapat `ProjectMember` di project asal.
* Yang menyeberang hanya satu baris permintaan yang peminta tulis sendiri,
  dengan proyeksi daftar-putih (`serializers/cross_division.py`).

Tiga endpoint:

    GET  /workspaces/<slug>/cross-division/tujuan/      divisi yang menerima
    GET  /workspaces/<slug>/cross-division/permintaan/  milik saya sendiri
    POST /workspaces/<slug>/cross-division/permintaan/  kirim permintaan baru
    GET  /workspaces/<slug>/cross-division/ringkasan/   hitungan per divisi

Catatan implementasi yang penting, jangan "diperbaiki" tanpa membaca
`.herdr/crossdiv-desain.md` bagian "Yang harus dijaga":

1. Work item di project tujuan dibuat dengan `created_by = NULL`. Kalau diisi
   peminta, `IntakeIssueViewSet.destroy` (`plane/app/views/intake/base.py:553`)
   yang memakai `creator=True` TANPA penjaga keanggotaan akan membiarkan
   peminta menghapus pekerjaannya di project orang lain.
2. Divisi tujuan harus sudah menyalakan Intake. Pintu masuk sebuah divisi
   adalah keputusan divisi itu.
"""

# Python imports
import json

# Django imports
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

# Third Party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from .. import BaseAPIView
from plane.app.permissions import WorkspaceEntityPermission
from plane.app.serializers.cross_division import (
    DivisiTujuanSerializer,
    serialize_permintaan,
)
from plane.bgtasks.issue_activities_task import issue_activity
from plane.db.models import (
    Intake,
    IntakeIssue,
    Issue,
    PermintaanLintasDivisi,
    Project,
    ProjectMember,
    State,
    StateGroup,
)
from plane.utils.content_validator import validate_html_content
from plane.utils.host import base_host

# Nilai `IntakeIssue.source`. `source` adalah CharField tanpa `choices`
# (plane/db/models/intake.py), jadi tidak perlu migrasi; yang wajib cuma
# mempertahankan string ini kalau nanti dijadikan konstanta.
SOURCE_LINTAS_DIVISI = "CROSSDIV"

PRIORITAS_SAH = {"low", "medium", "high", "urgent", "none"}
BATAS_CATATAN = 2000

# Status `IntakeIssue`: -2 menunggu · 0 ditunda · 1 diterima.
_STATUS_BELUM_DIJAWAB = (-2, 0)
# Hanya status "diterima" yang berarti pekerjaannya jalan di divisi tujuan.
_STATUS_DITERIMA = 1

_GROUP_TERBUKA = ["backlog", "unstarted", "started"]


class DivisiTujuanEndpoint(BaseAPIView):
    """Divisi yang membuka pintu permintaan (punya Intake default aktif)."""

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        projects = (
            Project.objects.filter(
                workspace__slug=slug,
                archived_at__isnull=True,
                project_intake__is_default=True,
                project_intake__deleted_at__isnull=True,
            )
            .distinct()
            .order_by("name")
        )
        return Response(DivisiTujuanSerializer(projects, many=True).data, status=status.HTTP_200_OK)


class PermintaanLintasDivisiEndpoint(BaseAPIView):
    """Kirim permintaan baru, dan baca kembali permintaan yang SAYA kirim."""

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        # Hanya permintaan milik pemanggil. Divisi asal tidak otomatis melihat
        # permintaan anggotanya; itu keputusan tersendiri (lihat pertanyaan
        # terbuka di rancangan), bukan default yang aman untuk ditebak.
        permintaan = (
            PermintaanLintasDivisi.objects.filter(workspace__slug=slug, diminta_oleh=request.user)
            .select_related(
                "asal_project",
                "tujuan_project",
                "intake_issue",
                "intake_issue__issue",
                "intake_issue__issue__state",
            )
            .order_by("-created_at")
        )
        return Response([serialize_permintaan(p) for p in permintaan], status=status.HTTP_200_OK)

    def post(self, request, slug):
        judul = (request.data.get("judul") or "").strip()
        if not judul:
            return Response({"error": "Judul permintaan wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)
        if len(judul) > 255:
            return Response({"error": "Judul maksimal 255 karakter."}, status=status.HTTP_400_BAD_REQUEST)

        prioritas = request.data.get("prioritas") or "none"
        if prioritas not in PRIORITAS_SAH:
            return Response({"error": "Prioritas tidak dikenal."}, status=status.HTTP_400_BAD_REQUEST)

        catatan = (request.data.get("catatan") or "").strip()
        if len(catatan) > BATAS_CATATAN:
            return Response(
                {"error": f"Catatan maksimal {BATAS_CATATAN} karakter."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        asal_id = request.data.get("asal_project")
        tujuan_id = request.data.get("tujuan_project")
        if not asal_id or not tujuan_id:
            return Response(
                {"error": "Divisi asal dan divisi tujuan wajib diisi."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        asal = Project.objects.filter(workspace__slug=slug, pk=asal_id, archived_at__isnull=True).first()
        if asal is None:
            return Response({"error": "Divisi asal tidak ditemukan."}, status=status.HTTP_400_BAD_REQUEST)

        # Peminta harus benar-benar anggota divisi asal yang dia klaim. Tanpa
        # pemeriksaan ini, anggota divisi mana pun bisa menuliskan permintaan
        # atas nama divisi lain.
        if not ProjectMember.objects.filter(project=asal, member=request.user, is_active=True).exists():
            return Response(
                {"error": "Anda bukan anggota divisi asal yang dipilih."},
                status=status.HTTP_403_FORBIDDEN,
            )

        tujuan = Project.objects.filter(workspace__slug=slug, pk=tujuan_id, archived_at__isnull=True).first()
        if tujuan is None:
            return Response({"error": "Divisi tujuan tidak ditemukan."}, status=status.HTTP_400_BAD_REQUEST)

        if str(asal.id) == str(tujuan.id):
            return Response(
                {"error": "Divisi tujuan tidak boleh sama dengan divisi asal."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Sengaja TIDAK membuat Intake diam-diam. Menyalakan pintu masuk sebuah
        # divisi adalah keputusan divisi itu (pola `intake_view` di
        # plane/app/views/project/base.py:393).
        intake = Intake.objects.filter(project=tujuan, is_default=True).first()
        if intake is None:
            return Response(
                {"error": f"{tujuan.name} belum membuka pintu permintaan lintas divisi."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        html_valid, html_error, html_bersih = validate_html_content(request.data.get("deskripsi_html") or "<p></p>")
        if not html_valid:
            return Response({"error": html_error}, status=status.HTTP_400_BAD_REQUEST)
        html_bersih = html_bersih or "<p></p>"

        with transaction.atomic():
            triage_state = State.triage_objects.filter(project=tujuan, workspace_id=tujuan.workspace_id).first()
            if triage_state is None:
                triage_state = State.objects.create(
                    name="Triage",
                    group=StateGroup.TRIAGE.value,
                    project=tujuan,
                    workspace_id=tujuan.workspace_id,
                    color="#4E5355",
                    sequence=65000,
                    default=False,
                )

            # `disable_auto_set_user=True` memastikan `created_by` KOSONG.
            # Lihat catatan (1) di kepala modul ini sebelum mengubahnya.
            issue = Issue(
                name=judul,
                description_html=html_bersih,
                description_json={},
                priority=prioritas,
                project=tujuan,
                state_id=triage_state.id,
            )
            issue.save(disable_auto_set_user=True)

            intake_issue = IntakeIssue(
                intake_id=intake.id,
                project=tujuan,
                issue_id=issue.id,
                source=SOURCE_LINTAS_DIVISI,
                external_source=asal.identifier,
                external_id=str(asal.id),
                extra={
                    "crossdiv": {
                        "asal_project_id": str(asal.id),
                        "asal_identifier": asal.identifier,
                        "peminta_id": str(request.user.id),
                        "peminta": request.user.display_name or request.user.email,
                    }
                },
            )
            # `created_by` di sini = peminta, dan itu disengaja: `IntakeIssue`
            # yang dibuat peminta TIDAK memberi dia hak apa pun (partial_update
            # menolak non-anggota lebih dulu, destroy memakai pembuat *Issue*).
            intake_issue.save()

            permintaan = PermintaanLintasDivisi.objects.create(
                workspace_id=tujuan.workspace_id,
                asal_project=asal,
                tujuan_project=tujuan,
                intake_issue=intake_issue,
                diminta_oleh=request.user,
                catatan=catatan,
            )

            issue_activity.delay(
                type="issue.activity.created",
                requested_data=json.dumps(
                    {
                        "name": judul,
                        "description_html": html_bersih,
                        "priority": prioritas,
                        "state_id": str(triage_state.id),
                    },
                    cls=DjangoJSONEncoder,
                ),
                actor_id=str(request.user.id),
                issue_id=str(issue.id),
                project_id=str(tujuan.id),
                current_instance=None,
                epoch=int(timezone.now().timestamp()),
                notification=True,
                origin=base_host(request=request, is_app=True),
                intake=str(intake_issue.id),
            )

        permintaan = PermintaanLintasDivisi.objects.select_related(
            "asal_project", "tujuan_project", "intake_issue", "intake_issue__issue", "intake_issue__issue__state"
        ).get(pk=permintaan.pk)
        return Response(serialize_permintaan(permintaan), status=status.HTTP_201_CREATED)


class RingkasanLintasDivisiEndpoint(BaseAPIView):
    """Hitungan lintas divisi per project, TERBATAS pada project yang user ikuti.

    Dipakai Dashboard Divisi supaya metrik "berapa tugas lintas divisi yang
    masih terbuka" tidak perlu membaca project tetangga. Hanya project tempat
    user menjadi anggota yang dihitung, jadi endpoint ini tidak memperluas
    apa pun yang sudah bisa dia lihat.
    """

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        project_ids = list(
            Project.objects.filter(
                workspace__slug=slug,
                project_projectmember__member=request.user,
                project_projectmember__is_active=True,
            )
            .values_list("id", flat=True)
            .distinct()
        )

        masuk = (
            PermintaanLintasDivisi.objects.filter(workspace__slug=slug, tujuan_project_id__in=project_ids)
            .values("tujuan_project_id")
            .annotate(
                menunggu=Count("id", filter=Q(intake_issue__status__in=_STATUS_BELUM_DIJAWAB)),
                terbuka=Count(
                    "id",
                    filter=Q(
                        intake_issue__status=_STATUS_DITERIMA,
                        intake_issue__issue__state__group__in=_GROUP_TERBUKA,
                    ),
                ),
            )
        )
        keluar = (
            PermintaanLintasDivisi.objects.filter(workspace__slug=slug, asal_project_id__in=project_ids)
            .values("asal_project_id")
            .annotate(
                menunggu=Count("id", filter=Q(intake_issue__status__in=_STATUS_BELUM_DIJAWAB)),
                terbuka=Count(
                    "id",
                    filter=Q(
                        intake_issue__status=_STATUS_DITERIMA,
                        intake_issue__issue__state__group__in=_GROUP_TERBUKA,
                    ),
                ),
            )
        )

        hasil = {
            str(pid): {"masuk_menunggu": 0, "masuk_terbuka": 0, "keluar_menunggu": 0, "keluar_terbuka": 0}
            for pid in project_ids
        }
        for row in masuk:
            hasil[str(row["tujuan_project_id"])]["masuk_menunggu"] = row["menunggu"]
            hasil[str(row["tujuan_project_id"])]["masuk_terbuka"] = row["terbuka"]
        for row in keluar:
            hasil[str(row["asal_project_id"])]["keluar_menunggu"] = row["menunggu"]
            hasil[str(row["asal_project_id"])]["keluar_terbuka"] = row["terbuka"]

        return Response(hasil, status=status.HTTP_200_OK)
