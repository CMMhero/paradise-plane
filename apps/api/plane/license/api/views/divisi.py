# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: keanggotaan divisi dari God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""`GET|POST /api/instances/divisi-anggota/` — tambah/hapus orang dari divisi.

Kenapa endpoint sendiri, bukan endpoint project biasa (`POST
.../projects/<id>/members/`):

* Endpoint project memeriksa keanggotaan PEMANGGIL di divisi itu
  (`allow_permission([ROLE.ADMIN])` level project). Dari God Mode itu rapuh:
  divisi arsip, selisih sinkronisasi B1, atau Superadmin yang bukan anggota
  workspace — semuanya 403 "You don't have the required permissions.",
  dan simpan bertahap (POST per divisi) berhenti di tengah dengan keadaan
  setengah jadi.
* Endpoint ini memakai `InstanceAdminPermission` (sama seperti halaman Member
  dan hierarki): satu panggilan, satu transaksi, semua-atau-tidak-sama-sekali.

Peran divisi DITURUNKAN dari jabatan (keputusan user 2026-10-16):
manager/supervisor = Admin divisi (20), member = Member (15). Backend
memvalidasi itu — UI yang mengirim peran lain ditolak, bukan dibulatkan.
"""

# Django imports
from django.db import transaction

# Third Party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.db.models import Project, ProjectMember, ProjectUserProperty, User, Workspace
from plane.utils.hierarki import TINGKAT_SUPERVISOR, tingkat_anggota
from .base import BaseAPIView

# Peran project yang sah. 5 (Guest) sengaja TIDAK ada: keanggotaan divisi dari
# God Mode minimal Member; Guest diatur admin divisi dari aplikasi utama.
_PERAN_SAH = {15, 20}


def _workspace_utama():
    return Workspace.objects.filter(deleted_at__isnull=True).order_by("created_at").first()


class InstanceDivisiAnggotaEndpoint(BaseAPIView):
    """GET daftar peran divisi satu orang · POST ganti seluruh daftarnya."""

    def get(self, request):
        member_id = request.query_params.get("member_id")
        if not member_id:
            return Response({"error": "member_id wajib dikirim."}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(pk=member_id).first()
        if user is None:
            return Response({"error": "User tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        workspace = _workspace_utama()
        if workspace is None:
            return Response({"error": "Workspace tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        projects = {
            p.id: p.identifier for p in Project.objects.filter(workspace=workspace, deleted_at__isnull=True)
        }
        hasil = [
            {"project_id": str(pid), "identifier": projects[pid], "role": role}
            for pid, role in ProjectMember.objects.filter(
                workspace=workspace, member=user, is_active=True, project_id__in=list(projects.keys())
            ).values_list("project_id", "role")
        ]
        return Response({"member_id": str(user.id), "divisi": sorted(hasil, key=lambda b: b["identifier"])})

    @transaction.atomic
    def post(self, request):
        """Ganti SELURUH keanggotaan divisi satu orang. Atomik.

        Badan: `{ "member_id": "<uuid>", "divisi": [{"project_id": "<uuid>",
        "role": 15|20}, ...] }`. Yang tidak disebut dikeluarkan (soft delete);
        peran yang beda di-PATCH; yang belum ada dibuat. Peran HARUS cocok
        dengan jabatan pengirim tidak memeriksa — pemanggil (God Mode) yang
        menurunkannya; yang diperiksa di sini hanya keanggotaan nilainya sah
        dan project-nya ada di workspace ini.
        """
        member_id = request.data.get("member_id")
        if not member_id:
            return Response({"error": "member_id wajib dikirim."}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(pk=member_id).first()
        if user is None:
            return Response({"error": "User tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        workspace = _workspace_utama()
        if workspace is None:
            return Response({"error": "Workspace tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        diminta = request.data.get("divisi")
        if not isinstance(diminta, list):
            return Response({"error": "divisi harus daftar {project_id, role}."}, status=status.HTTP_400_BAD_REQUEST)

        projects = {p.id: p.identifier for p in Project.objects.filter(workspace=workspace, deleted_at__isnull=True)}
        # Peta uuid→identifier untuk balasan. (Identifier→uuid tak perlu di sini:
        # pemanggil mengirim UUID, mendapatkannya dari GET hierarki.)
        ke_identifier = {str(pid): identifier for pid, identifier in projects.items()}

        ingin: dict[str, int] = {}
        for baris in diminta:
            pid = str((baris or {}).get("project_id") or "")
            if pid not in ke_identifier:
                return Response(
                    {"error": f"Project tidak dikenal di workspace ini: {pid or '(kosong)'}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                role = int((baris or {}).get("role"))
            except (TypeError, ValueError):
                return Response(
                    {"error": f"role harus 15 atau 20 (project {ke_identifier[pid]})."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if role not in _PERAN_SAH:
                return Response(
                    {"error": f"role harus 15 (Member) atau 20 (Admin divisi), bukan {role}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ingin[pid] = role

        # Peringatan, bukan penolakan: peran yang tidak cocok jabatan kemungkinan
        # salah klik (manager kok Member?). UI menurunkannya otomatis, jadi
        # keadaan ini hanya muncul dari pemanggil API langsung.
        tingkat = tingkat_anggota(user.id, workspace.id)
        peran_wajar = 20 if (tingkat is not None and tingkat >= TINGKAT_SUPERVISOR) else 15
        peringatan = sorted(
            f"{ke_identifier[q]} diberi {r}, wajarnya {peran_wajar}" for q, r in ingin.items() if r != peran_wajar
        )

        # Baris yang ADA (aktif maupun nonaktif — `is_active=False` TIDAK
        # membebaskan slot unik `deleted_at IS NULL`) dihidupkan lagi; yang
        # benar-benar baru dibuat massal. Pola persis endpoint project
        # (`bulk_update` + `bulk_create(ignore_conflicts=True)`): `create()`
        # memanggil `save()` yang ikut membuat baris `ProjectUserProperty`
        # dan menabrak uniknya saat tambah-ulang → 400 "payload is not valid".
        ada = {
            str(pid)
            for pid in ProjectMember.objects.filter(
                workspace=workspace, member=user, project_id__in=list(projects.keys())
            ).values_list("project_id", flat=True)
        }
        aktif = {
            str(pid): role
            for pid, role in ProjectMember.objects.filter(
                workspace=workspace, member=user, is_active=True, project_id__in=list(projects.keys())
            ).values_list("project_id", "role")
        }

        for pid in set(aktif) - set(ingin):
            ProjectMember.objects.filter(workspace=workspace, member=user, project_id=pid).update(is_active=False)
        hidupkan = [
            pm
            for pm in ProjectMember.objects.filter(workspace=workspace, member=user, project_id__in=list(ingin.keys()))
            if str(pm.project_id) in ada
        ]
        for pm in hidupkan:
            pm.is_active = True
            pm.role = ingin[str(pm.project_id)]
        ProjectMember.objects.bulk_update(hidupkan, ["is_active", "role"], batch_size=100)
        ProjectMember.objects.bulk_create(
            [
                ProjectMember(workspace=workspace, project_id=pid, member=user, role=role, is_active=True)
                for pid, role in ingin.items()
                if pid not in ada
            ],
            batch_size=10,
            ignore_conflicts=True,
        )
        ProjectUserProperty.objects.bulk_create(
            [
                ProjectUserProperty(user=user, project_id=pid, workspace=workspace, sort_order=65535)
                for pid in ingin
                if pid not in ada
            ],
            batch_size=10,
            ignore_conflicts=True,
        )

        # KEP-29: daftar di atas = keanggotaan eksplisit. Jangkauan hierarki selalu
        # menang, jadi baris otomatis yang baru saja dinonaktifkan oleh daftar lama
        # (mis. dikirim sesaat sesudah pindah departemen) dipulihkan di sini.
        from plane.db.jangkauan import sinkronkan_satu  # noqa: PLC0415

        sinkronkan_satu(workspace.id, user.id)

        return Response(
            {
                "member_id": str(user.id),
                "divisi": sorted(
                    ({"project_id": q, "identifier": ke_identifier[q], "role": r} for q, r in ingin.items()),
                    key=lambda b: b["identifier"],
                ),
                "peringatan": peringatan,
            }
        )