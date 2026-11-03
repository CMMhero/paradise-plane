# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import json
from datetime import timedelta

# Third party imports
from celery import shared_task
from django.db.models import Q

# Django imports
from django.utils import timezone

# Module imports
from plane.bgtasks.issue_activities_task import issue_activity
from plane.db.models import Issue, Project, State
from plane.utils.exception_logger import log_exception
from plane.utils.saklar_instance import AUTO_ARCHIVE_DONE_DAYS, setelan_angka

# Jumlah baris per UPDATE saat mengarsipkan, supaya putaran pertama sesudah
# setelan dinyalakan (bisa ribuan work item lama) tidak jadi satu kueri raksasa.
_UKURAN_BATCH_ARSIP = 500


@shared_task
def archive_and_close_old_issues():
    archive_old_issues()
    archive_done_issues_instance()
    close_old_issues()


def _filter_intake_selesai(queryset):
    """Work item intake yang masih menunggu keputusan tidak boleh ikut diarsipkan."""
    return queryset.filter(
        Q(issue_intake__status=1)
        | Q(issue_intake__status=-1)
        | Q(issue_intake__status=2)
        | Q(issue_intake__isnull=True)
    )


def archive_done_issues_instance():
    """Arsipkan work item Done yang sudah `AUTO_ARCHIVE_DONE_DAYS` hari selesai.

    Setelan instance dari God Mode > Features, berlaku di semua project. Hitungan
    harinya dari `completed_at` (saat work item masuk grup completed). Baris lama
    yang `completed_at`-nya kosong memakai `updated_at`. Cancelled TIDAK ikut:
    yang diminta hanya work item yang benar-benar selesai.

    Aktivitas dicatat tanpa notifikasi: putaran pertama bisa menyentuh ribuan
    work item, dan arsip otomatis bukan kabar yang perlu sampai ke inbox orang.
    """
    try:
        hari = setelan_angka(AUTO_ARCHIVE_DONE_DAYS)
        if hari <= 0:
            return 0
        batas = timezone.now() - timedelta(days=hari)
        kandidat = _filter_intake_selesai(
            Issue.issue_objects.filter(state__group="completed").filter(
                Q(completed_at__lte=batas) | Q(completed_at__isnull=True, updated_at__lte=batas)
            )
        )
        baris = list(kandidat.values_list("id", "project_id", "project__created_by_id").distinct())
        if not baris:
            return 0

        archive_at = timezone.now().date()
        for awal in range(0, len(baris), _UKURAN_BATCH_ARSIP):
            potong = baris[awal : awal + _UKURAN_BATCH_ARSIP]
            # archived_at__isnull diulang: work item yang diarsipkan manual di
            # antara SELECT dan UPDATE tidak ditimpa tanggalnya.
            Issue.objects.filter(id__in=[b[0] for b in potong], archived_at__isnull=True).update(
                archived_at=archive_at
            )
            for issue_id, project_id, actor_id in potong:
                issue_activity.delay(
                    type="issue.activity.updated",
                    requested_data=json.dumps({"archived_at": str(archive_at), "automation": True}),
                    actor_id=str(actor_id) if actor_id else None,
                    issue_id=str(issue_id),
                    project_id=str(project_id),
                    current_instance=json.dumps({"archived_at": None}),
                    subscriber=False,
                    epoch=int(timezone.now().timestamp()),
                    notification=False,
                )
        return len(baris)
    except Exception as e:
        log_exception(e)
        return 0


def archive_old_issues():
    try:
        # Get all the projects whose archive_in is greater than 0
        projects = Project.objects.filter(archive_in__gt=0)

        for project in projects:
            project_id = project.id
            archive_in = project.archive_in

            # Get all the issues whose updated_at in less that the archive_in month
            issues = Issue.issue_objects.filter(
                Q(
                    project=project_id,
                    archived_at__isnull=True,
                    updated_at__lte=(timezone.now() - timedelta(days=archive_in * 30)),
                    state__group__in=["completed", "cancelled"],
                ),
                Q(issue_cycle__isnull=True)
                | (Q(issue_cycle__cycle__end_date__lt=timezone.now()) & Q(issue_cycle__isnull=False)),
                Q(issue_module__isnull=True)
                | (Q(issue_module__module__target_date__lt=timezone.now()) & Q(issue_module__isnull=False)),
            ).filter(
                Q(issue_intake__status=1)
                | Q(issue_intake__status=-1)
                | Q(issue_intake__status=2)
                | Q(issue_intake__isnull=True)
            )

            # Check if Issues
            if issues:
                # Set the archive time to current time
                archive_at = timezone.now().date()

                issues_to_update = []
                for issue in issues:
                    issue.archived_at = archive_at
                    issues_to_update.append(issue)

                # Bulk Update the issues and log the activity
                if issues_to_update:
                    Issue.objects.bulk_update(issues_to_update, ["archived_at"], batch_size=100)
                    _ = [
                        issue_activity.delay(
                            type="issue.activity.updated",
                            requested_data=json.dumps({"archived_at": str(archive_at), "automation": True}),
                            actor_id=str(project.created_by_id),
                            issue_id=issue.id,
                            project_id=project_id,
                            current_instance=json.dumps({"archived_at": None}),
                            subscriber=False,
                            epoch=int(timezone.now().timestamp()),
                            notification=True,
                        )
                        for issue in issues_to_update
                    ]
        return
    except Exception as e:
        log_exception(e)
        return


def close_old_issues():
    try:
        # Get all the projects whose close_in is greater than 0
        projects = Project.objects.filter(close_in__gt=0).select_related("default_state")

        for project in projects:
            project_id = project.id
            close_in = project.close_in

            # Get all the issues whose updated_at in less that the close_in month
            issues = Issue.issue_objects.filter(
                Q(
                    project=project_id,
                    archived_at__isnull=True,
                    updated_at__lte=(timezone.now() - timedelta(days=close_in * 30)),
                    state__group__in=["backlog", "unstarted", "started"],
                ),
                Q(issue_cycle__isnull=True)
                | (Q(issue_cycle__cycle__end_date__lt=timezone.now()) & Q(issue_cycle__isnull=False)),
                Q(issue_module__isnull=True)
                | (Q(issue_module__module__target_date__lt=timezone.now()) & Q(issue_module__isnull=False)),
            ).filter(
                Q(issue_intake__status=1)
                | Q(issue_intake__status=-1)
                | Q(issue_intake__status=2)
                | Q(issue_intake__isnull=True)
            )

            # Check if Issues
            if issues:
                if project.default_state is None:
                    close_state = State.objects.filter(group="cancelled").first()
                else:
                    close_state = project.default_state

                issues_to_update = []
                for issue in issues:
                    issue.state = close_state
                    issues_to_update.append(issue)

                # Bulk Update the issues and log the activity
                if issues_to_update:
                    Issue.objects.bulk_update(issues_to_update, ["state"], batch_size=100)
                    [
                        issue_activity.delay(
                            type="issue.activity.updated",
                            requested_data=json.dumps({"closed_to": str(issue.state_id)}),
                            actor_id=str(project.created_by_id),
                            issue_id=issue.id,
                            project_id=project_id,
                            current_instance=None,
                            subscriber=False,
                            epoch=int(timezone.now().timestamp()),
                            notification=True,
                        )
                        for issue in issues_to_update
                    ]
        return
    except Exception as e:
        log_exception(e)
        return
