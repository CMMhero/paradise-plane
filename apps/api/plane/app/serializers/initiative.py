# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Initiatives
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import serializers

# Module imports
from .base import BaseSerializer
from plane.db.models import Initiative


class InitiativeSerializer(BaseSerializer):
    project_ids = serializers.ListField(child=serializers.UUIDField(), read_only=True)
    # progress rollup (dianotasi di view)
    issues_total = serializers.IntegerField(read_only=True, default=0)
    issues_completed = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Initiative
        fields = [
            "id",
            "name",
            "description_html",
            "status",
            "lead",
            "start_date",
            "end_date",
            "project_ids",
            "issues_total",
            "issues_completed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "workspace", "created_at", "updated_at"]

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Nama initiative wajib diisi.")
        return value.strip()
