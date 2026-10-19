# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Templates & Recurring Work Items
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
from datetime import timedelta

# Django imports
from django.conf import settings
from django.db import models
from django.utils import timezone

# Module imports
from .project import ProjectBaseModel


class IssueTemplate(ProjectBaseModel):
    """Template work item standar per project (judul, deskripsi, prioritas, assignee default)."""

    name = models.CharField(max_length=255)  # nama template
    title = models.CharField(max_length=255)  # judul issue hasil template
    description_html = models.TextField(blank=True, default="<p></p>")
    priority = models.CharField(max_length=30, default="none")
    default_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issue_templates",
    )

    class Meta:
        verbose_name = "Issue Template"
        verbose_name_plural = "Issue Templates"
        db_table = "issue_templates"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.project.name} · {self.name}"


class RecurringIssue(ProjectBaseModel):
    """Jadwal pembuatan otomatis work item dari template (harian/mingguan/bulanan)."""

    class Interval(models.TextChoices):
        DAILY = "DAILY", "Harian"
        WEEKLY = "WEEKLY", "Mingguan"
        MONTHLY = "MONTHLY", "Bulanan"

    template = models.ForeignKey("db.IssueTemplate", related_name="recurrences", on_delete=models.CASCADE)
    interval = models.CharField(max_length=10, choices=Interval.choices, default=Interval.WEEKLY)
    next_run_at = models.DateTimeField(default=timezone.now)
    last_run_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Recurring Issue"
        verbose_name_plural = "Recurring Issues"
        db_table = "recurring_issues"
        ordering = ("next_run_at",)

    def advance_schedule(self):
        """Geser next_run_at satu interval ke depan (dari jadwal, bukan dari now, agar tak drift)."""
        base = self.next_run_at
        now = timezone.now()
        step = {
            self.Interval.DAILY: timedelta(days=1),
            self.Interval.WEEKLY: timedelta(weeks=1),
            self.Interval.MONTHLY: timedelta(days=30),
        }[self.Interval(self.interval)]
        # Lompati jadwal yang terlewat (mis. laptop mati berhari-hari), buat 1 saja, bukan rapel
        while base <= now:
            base += step
        self.next_run_at = base
        self.last_run_at = now
        self.save(update_fields=["next_run_at", "last_run_at", "updated_at"])

    def __str__(self):
        return f"{self.template.name} ({self.interval})"
