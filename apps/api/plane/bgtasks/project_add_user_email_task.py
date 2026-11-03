# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import logging

from celery import shared_task

from plane.db.models import ProjectMember, User
from plane.utils.email_merek import avatar_untuk, bahasa_penerima, buat_pesan, render_email
from plane.utils.email_teks import teks
from plane.utils.exception_logger import log_exception


def susun_tambah_project(email, pengundang, nama_project, nama_workspace, url, bahasa, gambar=None):
    """(subjek, html, teks). `pengundang` = User (fotonya ikut) atau nama."""
    user = pengundang if isinstance(pengundang, User) else None
    av, _ = avatar_untuk(user, nama="" if user else str(pengundang), gambar=gambar)
    t = teks("tambah_project", bahasa, pengundang=av["nama"], project=nama_project, workspace=nama_workspace)
    html, polos = render_email(
        "emails/notifications/project_addition.html",
        {
            "t": t,
            "project_url": url,
            "pengundang_avatar": av,
            "judul": t["judul"],
            "pratajuk": t["intro"],
            "email_penerima": email,
        },
        bahasa,
    )
    return t["subjek"], html, polos


@shared_task
def project_add_user_email(current_site, project_member_id, invitor_id):
    try:
        invitor = User.objects.get(pk=invitor_id)
        project_member = ProjectMember.objects.select_related("project", "workspace", "member").get(
            pk=project_member_id
        )
        # Kustomisasi Paradise: kartu "ditambahkan ke project" di ruang "Paradise"
        # obrolan, sebelum email (yang bisa gagal karena konfigurasi SMTP).
        # Menelan galatnya sendiri.
        from plane.utils.kartu_obrolan import kartu_ditambahkan_ke_project  # noqa: PLC0415

        kartu_ditambahkan_ke_project(project_member, invitor_id)
        member = project_member.member
        project_url = f"{current_site}/{project_member.workspace.slug}/projects/{project_member.project_id}/issues"
        gambar = []
        subjek, html, polos = susun_tambah_project(
            member.email,
            invitor,
            project_member.project.name,
            project_member.workspace.name,
            project_url,
            bahasa_penerima(member),
            gambar,
        )
        buat_pesan(ke=member.email, subjek=subjek, html=html, teks=polos, gambar=gambar).send()
        logging.getLogger("plane.worker").info("Email sent successfully.")
        return
    except Exception as e:
        log_exception(e)
        return
