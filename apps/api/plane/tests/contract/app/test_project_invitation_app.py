# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Project invitation: menerima undangan harus memberi akses ke project yang
diundang, bukan ke project lain.

`ProjectJoinEndpoint` mencari ProjectMember dengan
`filter(workspace_id=..., member=user)` — TIDAK `project_id`. Kalau orang itu
sudah anggota project lain di workspace yang sama, baris itu yang ditemukan,
yang diaktifkan adalah keanggotaan project LAIN, dan keanggotaan untuk project
yang diundang tidak pernah dibuat. Undangan dijawab "berhasil", aksesnya tidak
ada.

Kelas kedua di berkas ini: MENGIRIM undangan project
(`ProjectInvitationsViewset.create`). Bentuk di HEAD memanggil `.role` pada
hasil `filter()` dan `.delay()` pada sebuah `list`, jadi setiap kiriman dijawab
500 sebelum satu baris pun tersimpan.
"""

import pytest
from django.utils import timezone
from rest_framework import status

from plane.db.models import (
    Project,
    ProjectMember,
    ProjectMemberInvite,
    ProjectUserProperty,
    State,
    User,
    WorkspaceMember,
)
from plane.db.superadmin import sinkronkan_super_admin
from plane.license.models import Instance, InstanceAdmin


def invitations_url(workspace_slug: str, project_id) -> str:
    """Kirim/daftar undangan project (`ProjectInvitationsViewset`)."""
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/invitations/"


def join_url(workspace_slug: str, project_id, invite_pk) -> str:
    """Terima/tolak undangan project (`ProjectJoinEndpoint`).

    Bukan `invitations_url()`: rute itu milik viewset undangan, dan POST ke sana
    berarti "kirim undangan", yang dijawab 400 "Emails are required". Rute
    penerimaan ada di `.../join/<pk>/` (`app/urls/project.py`, name
    `project-join`).
    """
    return f"/api/workspaces/{workspace_slug}/projects/{project_id}/join/{invite_pk}/"


@pytest.fixture
def project_a(workspace):
    p = Project.objects.create(name="Project A", identifier="PA", workspace=workspace)
    State.objects.create(name="Todo", color="#000000", project=p, workspace=workspace, sequence=1, group="backlog")
    return p


@pytest.fixture
def project_b(workspace):
    p = Project.objects.create(name="Project B", identifier="PB", workspace=workspace)
    State.objects.create(name="Todo", color="#000000", project=p, workspace=workspace, sequence=1, group="backlog")
    return p


@pytest.fixture
def invitee(db, workspace):
    """Anggota workspace yang sudah jadi anggota project A, tapi belum project B."""
    user = User.objects.create(
        email="invitee@test.local",
        username="invitee@test.local",
        first_name="Invitee",
        last_name="Tester",
    )
    user.set_password("invitee-password")
    user.save()
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15, company_role="member")
    return user


def buat_project_invite(project, email, role=15):
    return ProjectMemberInvite.objects.create(
        project=project,
        workspace=project.workspace,
        email=email,
        role=role,
        token="token-proyek-a",
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectInvitationAccept:
    def test_existing_member_of_other_project_gains_access_to_invited_project(
        self, api_client, workspace, project_a, project_b, invitee
    ):
        # Sudah anggota project A.
        ProjectMember.objects.create(project=project_a, member=invitee, workspace=workspace, role=15)

        invite = buat_project_invite(project_b, invitee.email)

        api_client.force_authenticate(user=invitee)
        response = api_client.post(
            join_url(workspace.slug, project_b.id, invite.id),
            {"token": invite.token, "accepted": True},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert ProjectMember.objects.filter(project=project_b, member=invitee, is_active=True).exists(), (
            "Menerima undangan harus memberi keanggotaan pada project yang diundang"
        )

    def test_brand_new_member_is_added_to_invited_project(self, api_client, workspace, project_b, invitee):
        # Belum anggota project manapun.
        invite = buat_project_invite(project_b, invitee.email)

        api_client.force_authenticate(user=invitee)
        response = api_client.post(
            join_url(workspace.slug, project_b.id, invite.id),
            {"token": invite.token, "accepted": True},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        member = ProjectMember.objects.get(project=project_b, member=invitee)
        assert member.is_active is True
        assert member.role == 15

    def test_existing_member_role_is_updated_to_invited_role(self, api_client, workspace, project_b, invitee):
        """Peran dari undangan harus diterapkan, bukan dibiarkan apa adanya."""
        ProjectMember.objects.create(project=project_b, member=invitee, workspace=workspace, role=5)

        invite = buat_project_invite(project_b, invitee.email, role=15)

        api_client.force_authenticate(user=invitee)
        response = api_client.post(
            join_url(workspace.slug, project_b.id, invite.id),
            {"token": invite.token, "accepted": True},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        member = ProjectMember.objects.get(project=project_b, member=invitee)
        assert member.role == 15, "Peran hasil undangan tidak pernah diterapkan ke anggota yang sudah ada"

    def test_soft_deleted_membership_is_revived_not_duplicated(self, api_client, workspace, project_b, invitee):
        """Keanggotaan yang pernah dicabut dihidupkan lagi, bukan digandakan.

        Manager bawaan (`objects`) tidak melihat baris ter-soft-delete, jadi
        bentuk lama akan membuat baris BARU untuk pasangan yang sama; baris itu
        menabrak constraint unik `ProjectUserProperty` milik baris lama yang
        masih hidup, dan hasilnya `IntegrityError`/500, bukan keanggotaan.
        """
        baris = ProjectMember.objects.create(project=project_b, member=invitee, workspace=workspace, role=5)
        ProjectMember.all_objects.filter(pk=baris.pk).update(deleted_at=timezone.now())

        invite = buat_project_invite(project_b, invitee.email, role=15)

        api_client.force_authenticate(user=invitee)
        response = api_client.post(
            join_url(workspace.slug, project_b.id, invite.id),
            {"token": invite.token, "accepted": True},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data

        semua = ProjectMember.all_objects.filter(project=project_b, member=invitee)
        assert semua.count() == 1, "harus dihidupkan, bukan digandakan"
        assert semua.first().deleted_at is None
        assert semua.first().is_active is True
        assert semua.first().role == 15
        assert ProjectUserProperty.all_objects.filter(project=project_b, user=invitee).count() == 1

    def test_super_admin_accepting_invitation_does_not_crash(self, api_client, workspace, project_b, invitee):
        """Super Admin sudah punya baris ProjectMember dari signal, jangan `create()` lagi."""
        instance = Instance.objects.first() or Instance.objects.create(last_checked_at=timezone.now())
        InstanceAdmin.objects.get_or_create(instance=instance, user=invitee)
        sinkronkan_super_admin(user_id=invitee.id)

        invite = buat_project_invite(project_b, invitee.email, role=20)

        api_client.force_authenticate(user=invitee)
        response = api_client.post(
            join_url(workspace.slug, project_b.id, invite.id),
            {"token": invite.token, "accepted": True},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert ProjectMember.all_objects.filter(project=project_b, member=invitee).count() == 1


class TestUserJoinsProjects:
    """`POST /users/me/workspaces/<slug>/projects/invitations/`.

    Ini endpoint yang benar-benar dipakai UI (tab Projects di pengaturan
    workspace), jadi ia harus punya tes sendiri. Tanpa itu, kekeliruan sekelas
    nama yang tidak terimpor di view ini tidak akan ketahuan oleh tes mana pun.
    """

    def test_anggota_workspace_dapat_bergabung_ke_project(self, api_client, workspace, project_a, invitee):
        api_client.force_authenticate(user=invitee)

        response = api_client.post(
            f"/api/users/me/workspaces/{workspace.slug}/projects/invitations/",
            {"project_ids": [str(project_a.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        member = ProjectMember.objects.get(project=project_a, member=invitee)
        assert member.is_active is True
        assert member.role == 15, "peran mengikuti peran workspace"
        assert ProjectUserProperty.objects.filter(project=project_a, user=invitee).exists()

    def test_project_di_workspace_lain_tidak_ikut_dimasukkan(self, api_client, workspace, invitee):
        """`project_ids` mentah dari workspace lain tidak boleh lolos (GHSA-45hc-q4mw-jhxm)."""
        from plane.db.models import Workspace

        lain = Project.objects.create(
            name="Project Luar",
            identifier="PL",
            workspace=Workspace.objects.create(name="Workspace Lain", slug="workspace-lain", owner=invitee),
        )

        api_client.force_authenticate(user=invitee)
        response = api_client.post(
            f"/api/users/me/workspaces/{workspace.slug}/projects/invitations/",
            {"project_ids": [str(lain.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert not ProjectMember.objects.filter(project=lain, member=invitee).exists()


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectInvitationSend:
    """`POST /invitations/` dulu 500 untuk SETIAP undangan project."""

    def test_project_admin_can_invite_an_email(self, api_client, workspace, create_user, project_a):
        ProjectMember.objects.create(project=project_a, member=create_user, workspace=workspace, role=20)
        api_client.force_authenticate(user=create_user)

        response = api_client.post(
            invitations_url(workspace.slug, project_a.id),
            {"emails": [{"email": "undangan.baru@test.local", "role": 15}]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert ProjectMemberInvite.objects.filter(
            project=project_a, email="undangan.baru@test.local", role=15
        ).exists(), "undangan harus benar-benar tersimpan"

    def test_workspace_role_mismatch_is_a_400_not_a_500(self, api_client, workspace, create_user, project_a):
        """Tamu workspace (5) tidak boleh diundang dengan peran project 15."""
        ProjectMember.objects.create(project=project_a, member=create_user, workspace=workspace, role=20)
        tamu = User.objects.create(email="tamu@test.local", username="tamu@test.local")
        WorkspaceMember.objects.create(workspace=workspace, member=tamu, role=5, company_role="guest")

        api_client.force_authenticate(user=create_user)
        response = api_client.post(
            invitations_url(workspace.slug, project_a.id),
            {"emails": [{"email": "tamu@test.local", "role": 15}]},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.data
        assert not ProjectMemberInvite.objects.filter(project=project_a, email="tamu@test.local").exists()
