# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: semua anggota otomatis masuk Wiki
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Setiap anggota workspace jadi anggota project Wiki (identifier `WIKI`).

Keputusan user 2026-10-26: semua anggota aplikasi, lama maupun baru, punya
akses Wiki dan ikut bergabung secara bawaan. Anggota Wiki = `ProjectMember`
(baca untuk semua; hak unggah tetap diatur ACL folder, bukan di sini).

Tidak pernah menurunkan atau menimpa keanggotaan yang sudah ada: admin Wiki
tetap admin, dan orang yang sengaja dikeluarkan lewat God Mode tidak dipaksa
masuk lagi oleh jalur lain selain pendaftaran anggota workspace baru.
"""

# Django imports
from django.db.models.signals import post_save
from django.dispatch import receiver

IDENTIFIER_WIKI = "WIKI"
ROLE_MEMBER = 15
ROLE_GUEST = 5


def gabungkan_ke_wiki(workspace_id, user_id, role_workspace=ROLE_MEMBER):
    """Jadikan user anggota Wiki bila belum aktif. True kalau ada yang berubah."""
    from plane.db.membership import jadikan_anggota_project
    from plane.db.models import Project, ProjectMember

    wiki = Project.objects.filter(
        workspace_id=workspace_id, identifier=IDENTIFIER_WIKI, deleted_at__isnull=True
    ).first()
    if wiki is None:
        return False
    if ProjectMember.objects.filter(project_id=wiki.id, member_id=user_id, is_active=True).exists():
        return False
    role = ROLE_GUEST if role_workspace == ROLE_GUEST else ROLE_MEMBER
    _, berubah = jadikan_anggota_project(wiki.id, user_id, role, workspace_id=workspace_id)
    return berubah


def gabungkan_semua_ke_wiki(workspace_id):
    """Backfill anggota lama. Mengembalikan jumlah orang yang baru digabungkan."""
    from plane.db.models import WorkspaceMember

    jumlah = 0
    for uid, role in WorkspaceMember.objects.filter(workspace_id=workspace_id, is_active=True).values_list(
        "member_id", "role"
    ):
        jumlah += 1 if gabungkan_ke_wiki(workspace_id, uid, role) else 0
    return jumlah


@receiver(post_save, sender="db.WorkspaceMember")
def anggota_workspace_masuk_wiki(sender, instance, created, **kwargs):
    """Anggota workspace baru langsung jadi anggota Wiki. Edit berikutnya dibiarkan."""
    if created and instance.is_active:
        gabungkan_ke_wiki(instance.workspace_id, instance.member_id, instance.role)
