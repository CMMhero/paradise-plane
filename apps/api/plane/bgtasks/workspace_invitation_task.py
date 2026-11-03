# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import logging

from celery import shared_task

from plane.db.models import User, Workspace, WorkspaceMemberInvite
from plane.utils.email_merek import avatar_untuk, bahasa_untuk_alamat, buat_pesan, render_email
from plane.utils.email_teks import teks
from plane.utils.exception_logger import log_exception


def susun_undangan_workspace(email, pengundang, nama_workspace, url, bahasa, gambar=None):
    """(subjek, html, teks). `pengundang` = User (fotonya ikut) atau nama."""
    user = pengundang if isinstance(pengundang, User) else None
    av, _ = avatar_untuk(user, nama="" if user else str(pengundang), gambar=gambar)
    t = teks("undangan_workspace", bahasa, pengundang=av["nama"], workspace=nama_workspace)
    html, polos = render_email(
        "emails/invitations/workspace_invitation.html",
        {
            "t": t,
            "abs_url": url,
            "pengundang_avatar": av,
            "judul": t["judul"],
            "pratajuk": t["intro"],
            "email_penerima": email,
        },
        bahasa,
    )
    return t["subjek"], html, polos


@shared_task
def workspace_invitation(email, workspace_id, token, current_site, inviter):
    try:
        user = User.objects.get(email=inviter)
        workspace = Workspace.objects.get(pk=workspace_id)
        workspace_member_invite = WorkspaceMemberInvite.objects.get(token=token, email=email)

        relative_link = (
            f"/workspace-invitations/?invitation_id={workspace_member_invite.id}&slug={workspace.slug}&token={token}"  # noqa: E501
        )
        abs_url = str(current_site) + relative_link

        gambar = []
        subjek, html, polos = susun_undangan_workspace(
            email, user, workspace.name, abs_url, bahasa_untuk_alamat(email), gambar
        )
        workspace_member_invite.message = polos
        workspace_member_invite.save()

        buat_pesan(ke=email, subjek=subjek, html=html, teks=polos, gambar=gambar).send()
        logging.getLogger("plane.worker").info("Email sent successfully")
        return
    except (Workspace.DoesNotExist, WorkspaceMemberInvite.DoesNotExist):
        return
    except Exception as e:
        log_exception(e)
        return
