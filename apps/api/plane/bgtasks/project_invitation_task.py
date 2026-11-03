# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import logging

from celery import shared_task

from plane.db.models import Project, ProjectMemberInvite, User
from plane.utils.email_merek import avatar_untuk, bahasa_untuk_alamat, buat_pesan, render_email
from plane.utils.email_teks import teks
from plane.utils.exception_logger import log_exception


def susun_undangan_project(email, pengundang, nama_project, url, bahasa, gambar=None):
    """(subjek, html, teks). `pengundang` = User (fotonya ikut) atau nama."""
    user = pengundang if isinstance(pengundang, User) else None
    av, _ = avatar_untuk(user, nama="" if user else str(pengundang), gambar=gambar)
    t = teks("undangan_project", bahasa, pengundang=av["nama"], project=nama_project)
    html, polos = render_email(
        "emails/invitations/project_invitation.html",
        {
            "t": t,
            "invitation_url": url,
            "pengundang_avatar": av,
            "judul": t["judul"],
            "pratajuk": t["intro"],
            "email_penerima": email,
        },
        bahasa,
    )
    return t["subjek"], html, polos


@shared_task
def project_invitation(email, project_id, token, current_site, invitor):
    try:
        user = User.objects.get(email=invitor)
        project = Project.objects.get(pk=project_id)
        project_member_invite = ProjectMemberInvite.objects.get(token=token, email=email)

        relativelink = f"/project-invitations/?invitation_id={project_member_invite.id}&email={email}&slug={project.workspace.slug}&project_id={str(project_id)}"  # noqa: E501
        abs_url = current_site + relativelink

        gambar = []
        subjek, html, polos = susun_undangan_project(
            email, user, project.name, abs_url, bahasa_untuk_alamat(email), gambar
        )
        project_member_invite.message = polos
        project_member_invite.save()

        buat_pesan(ke=email, subjek=subjek, html=html, teks=polos, gambar=gambar).send()
        logging.getLogger("plane.worker").info("Email sent successfully.")
        return
    except (Project.DoesNotExist, ProjectMemberInvite.DoesNotExist):
        return
    except Exception as e:
        log_exception(e)
        return
