# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Custom Properties
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import models

# Module imports
from .project import ProjectBaseModel


class IssueProperty(ProjectBaseModel):
    """Definisi field custom yang menempel pada sebuah Work Item Type."""

    class PropertyType(models.TextChoices):
        TEXT = "TEXT", "Teks"
        DECIMAL = "DECIMAL", "Angka"
        BOOLEAN = "BOOLEAN", "Ya/Tidak"
        DATETIME = "DATETIME", "Tanggal"
        OPTION = "OPTION", "Pilihan"
        MEMBER = "MEMBER", "Anggota"

    issue_type = models.ForeignKey("db.IssueType", related_name="properties", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)  # kunci internal
    display_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices, default=PropertyType.TEXT)
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_multi = models.BooleanField(default=False)  # multi-pilihan / multi-anggota
    sort_order = models.FloatField(default=65535)
    settings = models.JSONField(default=dict)
    default_value = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "Issue Property"
        verbose_name_plural = "Issue Properties"
        db_table = "issue_properties"
        ordering = ("sort_order",)

    def __str__(self):
        return f"{self.issue_type.name} · {self.display_name}"


class IssuePropertyOption(ProjectBaseModel):
    """Opsi untuk property bertipe OPTION (dropdown)."""

    property = models.ForeignKey("db.IssueProperty", related_name="options", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    sort_order = models.FloatField(default=65535)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    logo_props = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Issue Property Option"
        verbose_name_plural = "Issue Property Options"
        db_table = "issue_property_options"
        ordering = ("sort_order",)

    def __str__(self):
        return f"{self.property.display_name} · {self.name}"


class IssuePropertyValue(ProjectBaseModel):
    """Nilai property custom untuk satu Work Item. Kolom typed dipakai sesuai property_type."""

    property = models.ForeignKey("db.IssueProperty", related_name="values", on_delete=models.CASCADE)
    issue = models.ForeignKey("db.Issue", related_name="property_values", on_delete=models.CASCADE)
    value_text = models.TextField(null=True, blank=True)
    value_boolean = models.BooleanField(default=False)
    value_number = models.FloatField(null=True, blank=True)
    value_datetime = models.DateTimeField(null=True, blank=True)
    # option id (IssuePropertyOption) atau member id (User), tergantung property_type
    value_uuid = models.UUIDField(null=True, blank=True)

    class Meta:
        verbose_name = "Issue Property Value"
        verbose_name_plural = "Issue Property Values"
        db_table = "issue_property_values"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.issue_id} · {self.property_id}"
