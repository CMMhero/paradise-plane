# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Initiatives
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.conf import settings
from django.db import models

# Module imports
from .base import BaseModel


class Initiative(BaseModel):
    """Misi/objektif tingkat workspace yang memayungi beberapa project (divisi)."""

    class Status(models.TextChoices):
        PLANNED = "PLANNED", "Direncanakan"
        ACTIVE = "ACTIVE", "Berjalan"
        ON_HOLD = "ON_HOLD", "Ditunda"
        COMPLETED = "COMPLETED", "Selesai"

    workspace = models.ForeignKey("db.Workspace", related_name="initiatives", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description_html = models.TextField(blank=True, default="<p></p>")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="initiatives_lead",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    projects = models.ManyToManyField(
        "db.Project", related_name="initiatives", through="db.InitiativeProject"
    )

    class Meta:
        verbose_name = "Initiative"
        verbose_name_plural = "Initiatives"
        db_table = "initiatives"
        ordering = ("-created_at",)

    def __str__(self):
        return self.name


class InitiativeProject(BaseModel):
    """Tautan initiative ↔ project."""

    initiative = models.ForeignKey("db.Initiative", related_name="initiative_projects", on_delete=models.CASCADE)
    project = models.ForeignKey("db.Project", related_name="project_initiatives", on_delete=models.CASCADE)
    workspace = models.ForeignKey("db.Workspace", related_name="initiative_projects", on_delete=models.CASCADE)

    class Meta:
        unique_together = ["initiative", "project", "deleted_at"]
        verbose_name = "Initiative Project"
        verbose_name_plural = "Initiative Projects"
        db_table = "initiative_projects"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.initiative.name} · {self.project.name}"
