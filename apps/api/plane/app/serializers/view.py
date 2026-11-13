# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import serializers

# Module imports
from .base import DynamicBaseSerializer
from plane.db.models import IssueView
from plane.utils.issue_filters import issue_filters


class ViewIssueListSerializer(serializers.Serializer):
    def get_assignee_ids(self, instance):
        return [assignee.assignee_id for assignee in instance.issue_assignee.all()]

    def get_label_ids(self, instance):
        return [label.label_id for label in instance.label_issue.all()]

    def get_module_ids(self, instance):
        return [module.module_id for module in instance.issue_module.all()]

    def to_representation(self, instance):
        data = {
            "id": instance.id,
            "name": instance.name,
            "state_id": instance.state_id,
            "sort_order": instance.sort_order,
            "completed_at": instance.completed_at,
            "estimate_point": instance.estimate_point_id,
            "priority": instance.priority,
            "start_date": instance.start_date,
            "target_date": instance.target_date,
            "sequence_id": instance.sequence_id,
            "project_id": instance.project_id,
            "parent_id": instance.parent_id,
            "cycle_id": instance.cycle_id,
            "sub_issues_count": instance.sub_issues_count,
            "created_at": instance.created_at,
            "updated_at": instance.updated_at,
            "created_by": instance.created_by_id,
            "updated_by": instance.updated_by_id,
            "attachment_count": instance.attachment_count,
            "link_count": instance.link_count,
            "is_draft": instance.is_draft,
            "archived_at": instance.archived_at,
            "state__group": instance.state.group if instance.state else None,
            "assignee_ids": self.get_assignee_ids(instance),
            "label_ids": self.get_label_ids(instance),
            "module_ids": self.get_module_ids(instance),
            # Kustomisasi Paradise: diisi `lampirkan_status_persetujuan` per halaman (satu query).
            "approval_status": getattr(instance, "approval_status_terbaru", None),
        }
        return data


def lampirkan_status_persetujuan(issues):
    """Set `approval_status_terbaru` (latest approval row) on each issue of one page.

    One query per page, the same rule as the boards (`utils/grouper.py`): only the
    newest row per issue counts. Fails open to None so a list never breaks on it.
    """
    issues = list(issues)
    try:
        from plane.db.models import PersetujuanPenugasan  # noqa: PLC0415

        status_map = {}
        for issue_id, status in (
            PersetujuanPenugasan.objects.filter(issue_id__in=[issue.id for issue in issues])
            .order_by("issue_id", "-created_at")
            .values_list("issue_id", "status")
        ):
            status_map.setdefault(issue_id, status)
        for issue in issues:
            issue.approval_status_terbaru = status_map.get(issue.id)
    except Exception:
        for issue in issues:
            issue.approval_status_terbaru = None
    return issues


class IssueViewSerializer(DynamicBaseSerializer):
    is_favorite = serializers.BooleanField(read_only=True)

    class Meta:
        model = IssueView
        fields = "__all__"
        # Kustomisasi Paradise: `access` (privat/publik) bisa diisi saat membuat dan
        # diubah sesudahnya. Hanya pemilik yang boleh mengubahnya; dijaga di
        # `_galat_izin_view` (app/views/view/base.py), bukan di sini.
        read_only_fields = [
            "workspace",
            "project",
            "query",
            "owned_by",
            "is_locked",
        ]

    def create(self, validated_data):
        query_params = validated_data.get("filters", {})
        if bool(query_params):
            validated_data["query"] = issue_filters(query_params, "POST")
        else:
            validated_data["query"] = {}
        return IssueView.objects.create(**validated_data)

    def update(self, instance, validated_data):
        query_params = validated_data.get("filters", {})
        if bool(query_params):
            validated_data["query"] = issue_filters(query_params, "POST")
        else:
            validated_data["query"] = {}
        validated_data["query"] = issue_filters(query_params, "PATCH")
        return super().update(instance, validated_data)
