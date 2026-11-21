# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: setiap departemen punya Intake
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Wadah Intake default sebuah project.

`Project.intake_view` bawaannya True, jadi web membuka halaman Intake untuk setiap
project. Dulu baris `Intake` hanya dibuat saat project di-UPDATE, sehingga project
yang lahir dari God Mode (departemen) tidak punya wadah dan daftar Intake menjawab
404. Sekarang setiap jalur pembuatan project memanggil `ensure_default_intake`, dan
endpoint Intake memakai `intake_project` yang membuat ulang wadah yang hilang selama
Intake project itu menyala.
"""

from django.db import IntegrityError, transaction

from plane.db.models import Intake, Project

# `Intake.name` maksimal 255, sama dengan `Project.name`; akhiran " Intake" harus muat.
_AKHIRAN = " Intake"


def ensure_default_intake(project):
    """Intake default `project`; dibuat kalau belum ada. Aman dipanggil berulang."""
    intake = Intake.objects.filter(project=project, is_default=True).first()
    if intake is not None:
        return intake
    try:
        with transaction.atomic():
            return Intake.objects.create(
                name=f"{project.name[: 255 - len(_AKHIRAN)]}{_AKHIRAN}", project=project, is_default=True
            )
    except IntegrityError:
        # Dua permintaan membuatnya bersamaan, atau intake lain sudah memakai nama ini.
        return Intake.objects.filter(project=project).order_by("-is_default", "created_at").first()


def intake_project(slug, project_id):
    """Intake yang dipakai endpoint Intake, atau None kalau Intake project ini mati."""
    intake = Intake.objects.filter(workspace__slug=slug, project_id=project_id).order_by("-is_default", "name").first()
    if intake is not None:
        return intake
    project = Project.objects.filter(workspace__slug=slug, pk=project_id, intake_view=True).first()
    return ensure_default_intake(project) if project is not None else None
