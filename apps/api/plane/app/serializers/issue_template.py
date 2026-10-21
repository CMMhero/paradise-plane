# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Templates & Recurring
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import serializers

# Module imports
from .base import BaseSerializer
from plane.db.models import IssueTemplate, RecurringIssue


class IssueTemplateSerializer(BaseSerializer):
    class Meta:
        model = IssueTemplate
        fields = [
            "id",
            "name",
            "title",
            "description_html",
            "priority",
            "default_assignee",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "workspace", "project", "created_at", "updated_at"]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Nama template wajib diisi.")
        return value.strip()

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Judul work item wajib diisi.")
        return value.strip()


class RecurringIssueSerializer(BaseSerializer):
    template_detail = IssueTemplateSerializer(read_only=True, source="template")

    class Meta:
        model = RecurringIssue
        fields = [
            "id",
            "template",
            "template_detail",
            "interval",
            "next_run_at",
            "last_run_at",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "workspace", "project", "last_run_at", "created_at"]
