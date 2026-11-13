# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import json
import uuid
from uuid import UUID
from types import SimpleNamespace


# Module imports
from plane.db.models import (
    IssueMention,
    IssueSubscriber,
    Project,
    User,
    IssueAssignee,
    Issue,
    State,
    EmailNotificationLog,
    Notification,
    IssueComment,
    IssueActivity,
    ProjectMember,
)
from django.db.models import Subquery
from plane.utils.preferensi_email import saklar_untuk

# Third Party imports
from celery import shared_task
from bs4 import BeautifulSoup


# =========== Issue Description Html Parsing and notification Functions ======================


def update_mentions_for_issue(issue, project, new_mentions, removed_mention):
    aggregated_issue_mentions = []
    for mention_id in new_mentions:
        aggregated_issue_mentions.append(
            IssueMention(
                mention_id=mention_id,
                issue=issue,
                project=project,
                workspace_id=project.workspace_id,
            )
        )

    IssueMention.objects.bulk_create(aggregated_issue_mentions, batch_size=100)
    IssueMention.objects.filter(issue=issue, mention__in=removed_mention).delete()


def get_new_mentions(requested_instance, current_instance):
    # requested_data is the newer instance of the current issue
    # current_instance is the older instance of the current issue, saved in the database

    # extract mentions from both the instance of data
    mentions_older = extract_mentions(current_instance)

    mentions_newer = extract_mentions(requested_instance)

    # Getting Set Difference from mentions_newer
    new_mentions = [mention for mention in mentions_newer if mention not in mentions_older]

    return new_mentions


# Get Removed Mention
def get_removed_mentions(requested_instance, current_instance):
    # requested_data is the newer instance of the current issue
    # current_instance is the older instance of the current issue, saved in the database

    # extract mentions from both the instance of data
    mentions_older = extract_mentions(current_instance)
    mentions_newer = extract_mentions(requested_instance)

    # Getting Set Difference from mentions_newer
    removed_mentions = [mention for mention in mentions_older if mention not in mentions_newer]

    return removed_mentions


# Adds mentions as subscribers
def extract_mentions_as_subscribers(project_id, issue_id, mentions):
    # mentions is an array of User IDs representing the FILTERED set of mentioned users

    bulk_mention_subscribers = []

    for mention_id in mentions:
        # If the particular mention has not already been subscribed to the issue, he must be sent the mentioned notification # noqa: E501
        if (
            not IssueSubscriber.objects.filter(
                issue_id=issue_id, subscriber_id=mention_id, project_id=project_id
            ).exists()
            and not IssueAssignee.objects.filter(
                project_id=project_id, issue_id=issue_id, assignee_id=mention_id
            ).exists()
            and not Issue.objects.filter(project_id=project_id, pk=issue_id, created_by_id=mention_id).exists()
            and ProjectMember.objects.filter(project_id=project_id, member_id=mention_id, is_active=True).exists()
        ):
            project = Project.objects.get(pk=project_id)

            bulk_mention_subscribers.append(
                IssueSubscriber(
                    workspace_id=project.workspace_id,
                    project_id=project_id,
                    issue_id=issue_id,
                    subscriber_id=mention_id,
                )
            )
    return bulk_mention_subscribers


# Parse Issue Description & extracts mentions
def extract_mentions(issue_instance):
    try:
        # issue_instance has to be a dictionary passed, containing the description_html and other set of activity data. # noqa: E501
        mentions = []
        # Convert string to dictionary
        data = json.loads(issue_instance)
        html = data.get("description_html")
        soup = BeautifulSoup(html, "html.parser")
        mention_tags = soup.find_all("mention-component", attrs={"entity_name": "user_mention"})

        mentions = [mention_tag["entity_identifier"] for mention_tag in mention_tags]

        return list(set(mentions))
    except Exception:
        return []


# =========== Comment Parsing and notification Functions ======================
def extract_comment_mentions(comment_value):
    try:
        mentions = []
        soup = BeautifulSoup(comment_value, "html.parser")
        mentions_tags = soup.find_all("mention-component", attrs={"entity_name": "user_mention"})
        for mention_tag in mentions_tags:
            mentions.append(mention_tag["entity_identifier"])
        return list(set(mentions))
    except Exception:
        return []


# Kustomisasi Paradise (KEP-91): @all di deskripsi dan komentar. Sebutan ini
# BUKAN orang: entity_identifier-nya "all", jadi tidak boleh lewat UUID() atau
# jadi IssueMention/IssueSubscriber. Yang dikirimi hanya notifikasi sebutan.
SEBUT_SEMUA = "everyone_mention"


def ada_sebut_semua(html) -> bool:
    """True kalau HTML memuat mention-component @all."""
    if not html:
        return False
    try:
        return bool(BeautifulSoup(html, "html.parser").find("mention-component", attrs={"entity_name": SEBUT_SEMUA}))
    except Exception:
        return False


def _deskripsi_html(issue_instance):
    try:
        return (json.loads(issue_instance) or {}).get("description_html")
    except Exception:
        return None


def sebut_semua_baru_di_deskripsi(requested_instance, current_instance) -> bool:
    """@all muncul di deskripsi BARU dan belum ada di deskripsi lama."""
    return ada_sebut_semua(_deskripsi_html(requested_instance)) and not ada_sebut_semua(
        _deskripsi_html(current_instance)
    )


def sebut_semua_baru_di_komentar(new_value, old_value) -> bool:
    """@all muncul di komentar baru/hasil sunting dan belum ada di versi lamanya."""
    return ada_sebut_semua(new_value) and not ada_sebut_semua(old_value)


def _uuid_aman(nilai):
    try:
        return UUID(str(nilai))
    except (TypeError, ValueError, AttributeError):
        return None


def get_new_comment_mentions(new_value, old_value):
    mentions_newer = extract_comment_mentions(new_value)
    if old_value is None:
        return mentions_newer

    mentions_older = extract_comment_mentions(old_value)
    # Getting Set Difference from mentions_newer
    new_mentions = [mention for mention in mentions_newer if mention not in mentions_older]

    return new_mentions


def _jenis_kabar(issue_activity, subscriber, project_id) -> str:
    """Jenis kabar satu aktivitas bagi satu penerima, untuk saklar `inbox_<jenis>`.

    Kustomisasi Paradise (2026-11-02): inbox tidak lagi selalu ditulis. Pembagiannya
    sama dengan saklar email di bawah, plus "assigned" untuk orang yang baru
    ditugaskan.
    """
    field = issue_activity.get("field")
    if field == "assignees" and str(issue_activity.get("new_identifier")) == str(subscriber):
        return "assigned"
    if field == "state":
        selesai = State.objects.filter(
            project_id=project_id, pk=issue_activity.get("new_identifier"), group="completed"
        ).exists()
        return "issue_completed" if selesai else "state_change"
    if field == "comment":
        return "comment"
    return "property_change"


def penerima_balasan_komentar(issue_activities, issue_id, actor_id, anggota_aktif) -> dict:
    """{id penulis induk (str): (aktivitas, teks balasan)} untuk komentar BARU yang membalas.

    Kustomisasi Paradise (balasan komentar): penulis komentar yang dibalas dikabari
    walau bukan subscriber. Hanya aktivitas "created" (menyunting balasan tidak
    mengabari ulang), hanya induk pada work item yang sama, bukan diri sendiri,
    dan hanya anggota aktif project. Induk tanpa penulis (komentar sistem/impor)
    tidak dikabari.
    """
    hasil: dict = {}
    for aktivitas in issue_activities or []:
        if aktivitas.get("field") != "comment" or aktivitas.get("verb") != "created":
            continue
        komentar_id = aktivitas.get("issue_comment")
        if not komentar_id:
            continue
        balasan = IssueComment.objects.filter(pk=komentar_id, issue_id=issue_id).first()
        if balasan is None or balasan.parent_id is None:
            continue
        induk = IssueComment.objects.filter(pk=balasan.parent_id, issue_id=issue_id).first()
        if induk is None:
            continue
        penulis = induk.actor_id or induk.created_by_id
        if penulis is None:
            continue
        penulis = str(penulis)
        if penulis == str(actor_id) or penulis not in anggota_aktif:
            continue
        hasil.setdefault(penulis, (aktivitas, balasan.comment_stripped))
    return hasil


def create_mention_notification(project, notification_comment, issue, actor_id, mention_id, issue_id, activity):
    return Notification(
        workspace=project.workspace,
        sender="in_app:issue_activities:mentioned",
        triggered_by_id=actor_id,
        receiver_id=mention_id,
        entity_identifier=issue_id,
        entity_name="issue",
        project=project,
        message=notification_comment,
        data={
            "issue": {
                "id": str(issue_id),
                "name": str(issue.name),
                "identifier": str(issue.project.identifier),
                "sequence_id": issue.sequence_id,
                "state_name": issue.state.name,
                "state_group": issue.state.group,
            },
            "issue_activity": {
                "id": str(activity.get("id")),
                "verb": str(activity.get("verb")),
                "field": str(activity.get("field")),
                "actor": str(activity.get("actor_id")),
                "new_value": str(activity.get("new_value")),
                "old_value": str(activity.get("old_value")),
                "old_identifier": (str(activity.get("old_identifier")) if activity.get("old_identifier") else None),
                "new_identifier": (str(activity.get("new_identifier")) if activity.get("new_identifier") else None),
            },
        },
    )


@shared_task
def notifications(
    type,
    issue_id,
    project_id,
    actor_id,
    subscriber,
    issue_activities_created,
    requested_data,
    current_instance,
):
    try:
        issue_activities_created = (
            json.loads(issue_activities_created) if issue_activities_created is not None else None
        )
        if type not in [
            "cycle.activity.created",
            "cycle.activity.deleted",
            "module.activity.created",
            "module.activity.deleted",
            "issue_reaction.activity.created",
            "issue_reaction.activity.deleted",
            "comment_reaction.activity.created",
            "comment_reaction.activity.deleted",
            "issue_vote.activity.created",
            "issue_vote.activity.deleted",
            "issue_draft.activity.created",
            "issue_draft.activity.updated",
            "issue_draft.activity.deleted",
        ]:
            # Create Notifications
            bulk_notifications = []
            bulk_email_logs = []

            """
            Mention Tasks
            1. Perform Diffing and Extract the mentions, that mention notification needs to be sent
            2. From the latest set of mentions, extract the users which are not a subscribers & make them subscribers
            """

            # get the list of active project members
            project_members = ProjectMember.objects.filter(project_id=project_id, is_active=True).values_list(
                "member_id", flat=True
            )

            # Get new mentions from the newer instance
            new_mentions = get_new_mentions(requested_instance=requested_data, current_instance=current_instance)
            new_mentions = list(set(new_mentions) & {str(member) for member in project_members})
            removed_mention = get_removed_mentions(requested_instance=requested_data, current_instance=current_instance)

            # KEP-91: @all di deskripsi = seluruh anggota aktif project, sebagai
            # penerima notifikasi sebutan SAJA (bukan IssueMention/subscriber).
            semua_anggota = [str(member) for member in project_members]
            # Hanya yang disebut BERNAMA yang dicatat sebagai IssueMention.
            sebut_tersurat = list(new_mentions)
            if sebut_semua_baru_di_deskripsi(requested_data, current_instance):
                new_mentions = list(dict.fromkeys(new_mentions + semua_anggota))

            comment_mentions = []
            all_comment_mentions = []

            # Get New Subscribers from the mentions of the newer instance
            requested_mentions = extract_mentions(issue_instance=requested_data)
            mention_subscribers = extract_mentions_as_subscribers(
                project_id=project_id, issue_id=issue_id, mentions=requested_mentions
            )

            for issue_activity in issue_activities_created:
                issue_comment = issue_activity.get("issue_comment")
                issue_comment_new_value = issue_activity.get("new_value")
                issue_comment_old_value = issue_activity.get("old_value")
                if issue_comment is not None:
                    # TODO: Maybe save the comment mentions, so that in future, we can filter out the issues based on comment mentions as well.

                    all_comment_mentions = all_comment_mentions + extract_comment_mentions(issue_comment_new_value)

                    new_comment_mentions = get_new_comment_mentions(
                        old_value=issue_comment_old_value,
                        new_value=issue_comment_new_value,
                    )
                    comment_mentions = comment_mentions + new_comment_mentions
                    if sebut_semua_baru_di_komentar(issue_comment_new_value, issue_comment_old_value):
                        comment_mentions = comment_mentions + semua_anggota
                    anggota_project = set(project_members)
                    comment_mentions = list(
                        dict.fromkeys(
                            mention for mention in comment_mentions if _uuid_aman(mention) in anggota_project
                        )
                    )

            comment_mention_subscribers = extract_mentions_as_subscribers(
                project_id=project_id, issue_id=issue_id, mentions=all_comment_mentions
            )
            # Balasan komentar: penulis induk dikabari sebagai balasan. Yang sudah
            # disebut di komentar yang sama dan memang menerima kabar sebutan hanya
            # mendapat kabar sebutan, jadi tidak ada yang dikabari dua kali. Kalau
            # kabar sebutannya dimatikan (saklar sendiri atau batas direktur),
            # balasan tetap dikabari menurut saklar komentar.
            sudah_disebut = {str(mention) for mention in comment_mentions}
            penerima_balasan = penerima_balasan_komentar(
                issue_activities_created, issue_id, actor_id, {str(member) for member in project_members}
            )
            for penerima in list(penerima_balasan):
                if penerima in sudah_disebut:
                    saklar_sebutan = saklar_untuk(penerima)
                    if saklar_sebutan["inbox_mention"] or saklar_sebutan["mention"]:
                        del penerima_balasan[penerima]
            """
            We will not send subscription activity notification to the below mentioned user sets
            - Those who have been newly mentioned in the issue description, we will send mention notification to them.
            - When the activity is a comment_created and there exist a mention in the comment, 
              then we have to send the "mention_in_comment" notification
            - When the activity is a comment_updated and there exist a mention change, 
              then also we have to send the "mention_in_comment" notification
            """

            # ---------------------------------------------------------------------------------------------------------
            issue_subscribers = list(
                IssueSubscriber.objects.filter(
                    project_id=project_id,
                    issue_id=issue_id,
                    subscriber__in=Subquery(project_members),
                )
                .exclude(subscriber_id__in=list(new_mentions + comment_mentions + [actor_id] + list(penerima_balasan)))
                .values_list("subscriber", flat=True)
            )

            issue = Issue.objects.filter(pk=issue_id).first()

            if subscriber:
                # add the user to issue subscriber
                try:
                    _ = IssueSubscriber.objects.get_or_create(
                        project_id=project_id, issue_id=issue_id, subscriber_id=actor_id
                    )
                except Exception:
                    pass

            project = Project.objects.get(pk=project_id)

            issue_assignees = IssueAssignee.objects.filter(
                issue_id=issue_id,
                project_id=project_id,
                assignee__in=Subquery(project_members),
            ).values_list("assignee", flat=True)

            issue_subscribers = list(set(issue_subscribers) - {uuid.UUID(actor_id)})

            for subscriber in issue_subscribers:
                if issue.created_by_id and issue.created_by_id == subscriber:
                    sender = "in_app:issue_activities:created"
                elif subscriber in issue_assignees and issue.created_by_id not in issue_assignees:
                    sender = "in_app:issue_activities:assigned"
                else:
                    sender = "in_app:issue_activities:subscribed"

                preference = SimpleNamespace(**saklar_untuk(subscriber))

                for issue_activity in issue_activities_created:
                    # If activity done in blocking then blocked by email should not go
                    if issue_activity.get("issue_detail").get("id") != issue_id:
                        continue

                    # Do not send notification for description update
                    if issue_activity.get("field") == "description":
                        continue

                    # Check if the value should be sent or not
                    send_email = False
                    # Kustomisasi Paradise: penerima yang baru ditugaskan sudah
                    # dapat email "tugas baru" sendiri (penugasan_email.py).
                    if (
                        issue_activity.get("field") == "assignees"
                        and str(issue_activity.get("new_identifier")) == str(subscriber)
                        and preference.assigned
                    ):
                        send_email = False
                    elif issue_activity.get("field") == "state" and preference.state_change:
                        send_email = True
                    elif (
                        issue_activity.get("field") == "state"
                        and preference.issue_completed
                        and State.objects.filter(
                            project_id=project_id,
                            pk=issue_activity.get("new_identifier"),
                            group="completed",
                        ).exists()
                    ):
                        send_email = True
                    elif issue_activity.get("field") == "comment" and preference.comment:
                        send_email = True
                    elif preference.property_change:
                        send_email = True
                    else:
                        send_email = False

                    # If activity is of issue comment fetch the comment
                    issue_comment = (
                        IssueComment.objects.filter(
                            id=issue_activity.get("issue_comment"),
                            issue_id=issue_id,
                            project_id=project_id,
                            workspace_id=project.workspace_id,
                        ).first()
                        if issue_activity.get("issue_comment")
                        else None
                    )

                    # Create in app notification
                    if getattr(preference, "inbox_" + _jenis_kabar(issue_activity, subscriber, project_id)):
                        bulk_notifications.append(
                            Notification(
                                workspace=project.workspace,
                                sender=sender,
                                triggered_by_id=actor_id,
                                receiver_id=subscriber,
                                entity_identifier=issue_id,
                                entity_name="issue",
                                project=project,
                                title=issue_activity.get("comment"),
                                data={
                                    "issue": {
                                        "id": str(issue_id),
                                        "name": str(issue.name),
                                        "identifier": str(issue.project.identifier),
                                        "sequence_id": issue.sequence_id,
                                        "state_name": issue.state.name,
                                        "state_group": issue.state.group,
                                    },
                                    "issue_activity": {
                                        "id": str(issue_activity.get("id")),
                                        "verb": str(issue_activity.get("verb")),
                                        "field": str(issue_activity.get("field")),
                                        "actor": str(issue_activity.get("actor_id")),
                                        "new_value": str(issue_activity.get("new_value")),
                                        "old_value": str(issue_activity.get("old_value")),
                                        "issue_comment": str(
                                            issue_comment.comment_stripped if issue_comment is not None else ""
                                        ),
                                        "old_identifier": (
                                            str(issue_activity.get("old_identifier"))
                                            if issue_activity.get("old_identifier")
                                            else None
                                        ),
                                        "new_identifier": (
                                            str(issue_activity.get("new_identifier"))
                                            if issue_activity.get("new_identifier")
                                            else None
                                        ),
                                    },
                                },
                            )
                        )
                    # Create email notification
                    if send_email:
                        bulk_email_logs.append(
                            EmailNotificationLog(
                                triggered_by_id=actor_id,
                                receiver_id=subscriber,
                                entity_identifier=issue_id,
                                entity_name="issue",
                                data={
                                    "issue": {
                                        "id": str(issue_id),
                                        "name": str(issue.name),
                                        "identifier": str(issue.project.identifier),
                                        "project_id": str(issue.project.id),
                                        "workspace_slug": str(issue.project.workspace.slug),
                                        "sequence_id": issue.sequence_id,
                                        "state_name": issue.state.name,
                                        "state_group": issue.state.group,
                                    },
                                    "issue_activity": {
                                        "id": str(issue_activity.get("id")),
                                        "verb": str(issue_activity.get("verb")),
                                        "field": str(issue_activity.get("field")),
                                        "actor": str(issue_activity.get("actor_id")),
                                        "new_value": str(issue_activity.get("new_value")),
                                        "old_value": str(issue_activity.get("old_value")),
                                        "issue_comment": str(
                                            issue_comment.comment_stripped if issue_comment is not None else ""
                                        ),
                                        "old_identifier": (
                                            str(issue_activity.get("old_identifier"))
                                            if issue_activity.get("old_identifier")
                                            else None
                                        ),
                                        "new_identifier": (
                                            str(issue_activity.get("new_identifier"))
                                            if issue_activity.get("new_identifier")
                                            else None
                                        ),
                                        "activity_time": issue_activity.get("created_at"),
                                    },
                                },
                            )
                        )

            # Kabar balasan: pengarang komentar yang dibalas. Saklar yang dipakai
            # adalah saklar komentar (inbox_comment / comment), jadi pilihan pribadi
            # dan batas direktur (KEP-59) berlaku apa adanya.
            for penerima, (aktivitas, isi_balasan) in penerima_balasan.items():
                preference = SimpleNamespace(**saklar_untuk(penerima))
                data_kabar = {
                    "issue": {
                        "id": str(issue_id),
                        "name": str(issue.name),
                        "identifier": str(issue.project.identifier),
                        "project_id": str(issue.project.id),
                        "workspace_slug": str(issue.project.workspace.slug),
                        "sequence_id": issue.sequence_id,
                        "state_name": issue.state.name,
                        "state_group": issue.state.group,
                    },
                    "issue_activity": {
                        "id": str(aktivitas.get("id")),
                        "verb": str(aktivitas.get("verb")),
                        "field": str(aktivitas.get("field")),
                        "actor": str(aktivitas.get("actor_id")),
                        "new_value": str(aktivitas.get("new_value")),
                        "old_value": str(aktivitas.get("old_value")),
                        "issue_comment": str(isi_balasan or ""),
                        "old_identifier": None,
                        "new_identifier": (
                            str(aktivitas.get("new_identifier")) if aktivitas.get("new_identifier") else None
                        ),
                    },
                }
                if preference.inbox_comment:
                    bulk_notifications.append(
                        Notification(
                            workspace=project.workspace,
                            sender="in_app:issue_activities:subscribed",
                            triggered_by_id=actor_id,
                            receiver_id=penerima,
                            entity_identifier=issue_id,
                            entity_name="issue",
                            project=project,
                            title="replied to your comment",
                            data=data_kabar,
                        )
                    )
                if preference.comment:
                    bulk_email_logs.append(
                        EmailNotificationLog(
                            triggered_by_id=actor_id,
                            receiver_id=penerima,
                            entity_identifier=issue_id,
                            entity_name="issue",
                            data={
                                **data_kabar,
                                "issue_activity": {
                                    **data_kabar["issue_activity"],
                                    "activity_time": aktivitas.get("created_at"),
                                },
                            },
                        )
                    )

            # -------------------------------------------------------------------------------------------------------- #

            # Add Mentioned as Issue Subscribers
            IssueSubscriber.objects.bulk_create(
                mention_subscribers + comment_mention_subscribers,
                batch_size=100,
                ignore_conflicts=True,
            )

            last_activity = IssueActivity.objects.filter(issue_id=issue_id).order_by("-created_at").first()

            actor = User.objects.get(pk=actor_id)

            for mention_id in comment_mentions:
                if mention_id != actor_id:
                    preference = SimpleNamespace(**saklar_untuk(mention_id))
                    for issue_activity in issue_activities_created:
                        notification = create_mention_notification(
                            project=project,
                            issue=issue,
                            notification_comment=f"{actor.display_name} has mentioned you in a comment in issue {issue.name}",  # noqa: E501
                            actor_id=actor_id,
                            mention_id=mention_id,
                            issue_id=issue_id,
                            activity=issue_activity,
                        )

                        # check for email notifications
                        if preference.mention:
                            bulk_email_logs.append(
                                EmailNotificationLog(
                                    triggered_by_id=actor_id,
                                    receiver_id=mention_id,
                                    entity_identifier=issue_id,
                                    entity_name="issue",
                                    data={
                                        "issue": {
                                            "id": str(issue_id),
                                            "name": str(issue.name),
                                            "identifier": str(issue.project.identifier),
                                            "sequence_id": issue.sequence_id,
                                            "state_name": issue.state.name,
                                            "state_group": issue.state.group,
                                            "project_id": str(issue.project.id),
                                            "workspace_slug": str(issue.project.workspace.slug),
                                        },
                                        "issue_activity": {
                                            "id": str(issue_activity.get("id")),
                                            "verb": str(issue_activity.get("verb")),
                                            "field": str("mention"),
                                            "actor": str(issue_activity.get("actor_id")),
                                            "new_value": str(issue_activity.get("new_value")),
                                            "old_value": str(issue_activity.get("old_value")),
                                            "old_identifier": (
                                                str(issue_activity.get("old_identifier"))
                                                if issue_activity.get("old_identifier")
                                                else None
                                            ),
                                            "new_identifier": (
                                                str(issue_activity.get("new_identifier"))
                                                if issue_activity.get("new_identifier")
                                                else None
                                            ),
                                            "activity_time": issue_activity.get("created_at"),
                                        },
                                    },
                                )
                            )
                        if preference.inbox_mention:
                            bulk_notifications.append(notification)

            for mention_id in new_mentions:
                if mention_id != actor_id:
                    preference = SimpleNamespace(**saklar_untuk(mention_id))
                    if (
                        last_activity is not None
                        and last_activity.field == "description"
                        and actor_id == str(last_activity.actor_id)
                    ):
                        # Saklar inbox_mention mati = barisnya dibangun lalu dibuang.
                        (bulk_notifications if preference.inbox_mention else []).append(
                            Notification(
                                workspace=project.workspace,
                                sender="in_app:issue_activities:mentioned",
                                triggered_by_id=actor_id,
                                receiver_id=mention_id,
                                entity_identifier=issue_id,
                                entity_name="issue",
                                project=project,
                                message=f"You have been mentioned in the issue {issue.name}",
                                data={
                                    "issue": {
                                        "id": str(issue_id),
                                        "name": str(issue.name),
                                        "identifier": str(issue.project.identifier),
                                        "sequence_id": issue.sequence_id,
                                        "state_name": issue.state.name,
                                        "state_group": issue.state.group,
                                        "project_id": str(issue.project.id),
                                        "workspace_slug": str(issue.project.workspace.slug),
                                    },
                                    "issue_activity": {
                                        "id": str(last_activity.id),
                                        "verb": str(last_activity.verb),
                                        "field": str(last_activity.field),
                                        "actor": str(last_activity.actor_id),
                                        "new_value": str(last_activity.new_value),
                                        "old_value": str(last_activity.old_value),
                                        "old_identifier": (
                                            str(issue_activity.get("old_identifier"))
                                            if issue_activity.get("old_identifier")
                                            else None
                                        ),
                                        "new_identifier": (
                                            str(issue_activity.get("new_identifier"))
                                            if issue_activity.get("new_identifier")
                                            else None
                                        ),
                                    },
                                },
                            )
                        )
                        if preference.mention:
                            bulk_email_logs.append(
                                EmailNotificationLog(
                                    triggered_by_id=actor_id,
                                    receiver_id=mention_id,
                                    entity_identifier=issue_id,
                                    entity_name="issue",
                                    data={
                                        "issue": {
                                            "id": str(issue_id),
                                            "name": str(issue.name),
                                            "identifier": str(issue.project.identifier),
                                            "sequence_id": issue.sequence_id,
                                            "state_name": issue.state.name,
                                            "state_group": issue.state.group,
                                        },
                                        "issue_activity": {
                                            "id": str(last_activity.id),
                                            "verb": str(last_activity.verb),
                                            "field": "mention",
                                            "actor": str(last_activity.actor_id),
                                            "new_value": str(last_activity.new_value),
                                            "old_value": str(last_activity.old_value),
                                            "old_identifier": (
                                                str(issue_activity.get("old_identifier"))
                                                if issue_activity.get("old_identifier")
                                                else None
                                            ),
                                            "new_identifier": (
                                                str(issue_activity.get("new_identifier"))
                                                if issue_activity.get("new_identifier")
                                                else None
                                            ),
                                            "activity_time": str(last_activity.created_at),
                                        },
                                    },
                                )
                            )
                    else:
                        for issue_activity in issue_activities_created:
                            notification = create_mention_notification(
                                project=project,
                                issue=issue,
                                notification_comment=f"You have been mentioned in the issue {issue.name}",
                                actor_id=actor_id,
                                mention_id=mention_id,
                                issue_id=issue_id,
                                activity=issue_activity,
                            )
                            if preference.mention:
                                bulk_email_logs.append(
                                    EmailNotificationLog(
                                        triggered_by_id=actor_id,
                                        receiver_id=mention_id,
                                        entity_identifier=issue_id,
                                        entity_name="issue",
                                        data={
                                            "issue": {
                                                "id": str(issue_id),
                                                "name": str(issue.name),
                                                "identifier": str(issue.project.identifier),
                                                "sequence_id": issue.sequence_id,
                                                "state_name": issue.state.name,
                                                "state_group": issue.state.group,
                                            },
                                            "issue_activity": {
                                                "id": str(issue_activity.get("id")),
                                                "verb": str(issue_activity.get("verb")),
                                                "field": str("mention"),
                                                "actor": str(issue_activity.get("actor_id")),
                                                "new_value": str(issue_activity.get("new_value")),
                                                "old_value": str(issue_activity.get("old_value")),
                                                "old_identifier": (
                                                    str(issue_activity.get("old_identifier"))
                                                    if issue_activity.get("old_identifier")
                                                    else None
                                                ),
                                                "new_identifier": (
                                                    str(issue_activity.get("new_identifier"))
                                                    if issue_activity.get("new_identifier")
                                                    else None
                                                ),
                                                "activity_time": issue_activity.get("created_at"),
                                            },
                                        },
                                    )
                                )
                            if preference.inbox_mention:
                                bulk_notifications.append(notification)

            # save new mentions for the particular issue and remove the mentions that has been deleted from the description # noqa: E501
            update_mentions_for_issue(
                issue=issue,
                project=project,
                new_mentions=sebut_tersurat,
                removed_mention=removed_mention,
            )
            # Kustomisasi Paradise: perubahan beruntun atas kolom yang sama
            # (status, prioritas, tanggal, ...) digabung jadi satu kabar, di
            # aplikasi, kartu obrolan, dan email. Lihat utils/gabung_kabar.py.
            from plane.utils.gabung_kabar import gabungkan_email, gabungkan_notifikasi  # noqa: PLC0415

            bulk_notifications = gabungkan_notifikasi(bulk_notifications)
            bulk_email_logs = gabungkan_email(bulk_email_logs)
            # Bulk create notifications
            Notification.objects.bulk_create(bulk_notifications, batch_size=100)
            EmailNotificationLog.objects.bulk_create(bulk_email_logs, batch_size=100, ignore_conflicts=True)
            # Kustomisasi Paradise: baris inbox yang sama juga jadi kartu di ruang
            # "Paradise" obrolan. Menelan galatnya sendiri.
            from plane.utils.kartu_obrolan import kirim_kartu_notifikasi  # noqa: PLC0415

            kirim_kartu_notifikasi(bulk_notifications)
            # Lencana dan daftar Pemberitahuan di layar penerima menyegarkan diri
            # tanpa menunggu putaran berikutnya. Menelan galatnya sendiri.
            from plane.utils.sinyal_data import siarkan_notifikasi_baris  # noqa: PLC0415

            siarkan_notifikasi_baris(bulk_notifications)
        return
    except Exception as e:
        print(e)
        return
