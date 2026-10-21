# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Custom Properties
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import serializers

# Module imports
from .base import BaseSerializer
from plane.db.models import IssueProperty, IssuePropertyOption, IssuePropertyValue


class IssuePropertyOptionSerializer(BaseSerializer):
    class Meta:
        model = IssuePropertyOption
        fields = [
            "id",
            "property",
            "name",
            "sort_order",
            "is_active",
            "is_default",
            "logo_props",
            "created_at",
        ]
        read_only_fields = ["id", "property", "workspace", "project", "created_at"]


class IssuePropertySerializer(BaseSerializer):
    options = IssuePropertyOptionSerializer(many=True, read_only=True)

    class Meta:
        model = IssueProperty
        fields = [
            "id",
            "issue_type",
            "name",
            "display_name",
            "description",
            "property_type",
            "is_required",
            "is_active",
            "is_multi",
            "sort_order",
            "settings",
            "default_value",
            "options",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "name", "issue_type", "workspace", "project", "created_at", "updated_at"]

    def validate_display_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Nama field wajib diisi.")
        return value.strip()

    def validate_property_type(self, value):
        valid = {choice[0] for choice in IssueProperty.PropertyType.choices}
        if value not in valid:
            raise serializers.ValidationError(f"Tipe field tidak valid. Pilih: {', '.join(sorted(valid))}.")
        return value


class IssuePropertyValueSerializer(BaseSerializer):
    class Meta:
        model = IssuePropertyValue
        fields = [
            "id",
            "property",
            "issue",
            "value_text",
            "value_boolean",
            "value_number",
            "value_datetime",
            "value_uuid",
            "created_at",
        ]
        read_only_fields = ["id", "issue", "workspace", "project", "created_at"]
