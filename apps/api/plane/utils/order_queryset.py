# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db.models import Case, CharField, IntegerField, Min, OuterRef, Subquery, Value, When

# Custom ordering for priority and state
PRIORITY_ORDER = ["urgent", "high", "medium", "low", "none"]
STATE_ORDER = ["backlog", "unstarted", "started", "completed", "cancelled"]
# Kustomisasi Paradise (KEP-55): urutan status persetujuan TERBARU per tugas.
# Menaik = yang perlu ditindaklanjuti dulu; tugas tanpa persetujuan selalu di akhir.
APPROVAL_ORDER = ["menunggu", "ditolak", "disetujui"]

# ---------------------------------------------------------------------------
# order_by allowlists, one per model/endpoint family
# All contain bare field names (no leading '-'); the sanitizer strips the
# prefix before looking up, so descending variants are implicitly covered.
# Prevents ORM order_by injection via user-supplied query params
# (GHSA-2r95-c453-vxmr / GHSA-w45q-6m65-9498).
# ---------------------------------------------------------------------------

ISSUE_ORDER_BY_ALLOWLIST = frozenset({
    "created_at",
    "updated_at",
    "sequence_id",
    "sort_order",
    "target_date",
    "start_date",
    "completed_at",
    "archived_at",
    "priority",
    "state__name",
    "state__group",
    "assignees__first_name",
    "labels__name",
    "issue_module__module__name",
    "approval_status",
})

# IntakeIssue queryset, fields are prefixed with `issue__` for the join.
INTAKE_ISSUE_ORDER_BY_ALLOWLIST = frozenset({
    "issue__created_at",
    "issue__updated_at",
    "issue__sequence_id",
    "issue__sort_order",
    "issue__target_date",
    "issue__start_date",
    "issue__priority",
    "issue__state__name",
    "created_at",
    "updated_at",
    "status",
})

# IssueActivity queryset (user activity, workspace member activity).
ACTIVITY_ORDER_BY_ALLOWLIST = frozenset({
    "created_at",
    "updated_at",
})

# Project list queryset.
PROJECT_ORDER_BY_ALLOWLIST = frozenset({
    "created_at",
    "updated_at",
    "name",
    "network",
    "sort_order",
})

# Saved view (IssueView) list queryset.
VIEW_ORDER_BY_ALLOWLIST = frozenset({
    "created_at",
    "updated_at",
    "name",
})

# Notification queryset.
NOTIFICATION_ORDER_BY_ALLOWLIST = frozenset({
    "created_at",
    "updated_at",
})

# ---------------------------------------------------------------------------
# group_by / sub_group_by allowlist for Issue querysets, used by
# GroupedOffsetPaginator / SubGroupedOffsetPaginator (plane/utils/paginator.py),
# which pass the field name straight into F(), .values(), .order_by(), and
# Window partition_by. Prevents unauthenticated ORM field-name injection via
# user-supplied query params (GHSA-wwgj-929g-42cm).
# ---------------------------------------------------------------------------
ISSUE_GROUP_BY_ALLOWLIST = frozenset({
    "state_id",
    "state__group",
    "priority",
    "labels__id",
    "assignees__id",
    "issue_module__module_id",
    "cycle_id",
    "project_id",
    "created_by",
    "target_date",
    "start_date",
})

# Cycle list queryset.
CYCLE_ORDER_BY_ALLOWLIST = frozenset({
    "created_at",
    "updated_at",
    "name",
    "start_date",
    "end_date",
    "sort_order",
})

# Module list queryset.
MODULE_ORDER_BY_ALLOWLIST = frozenset({
    "created_at",
    "updated_at",
    "name",
    "start_date",
    "target_date",
    "status",
    "sort_order",
})

def sanitize_order_by(value, allowed_fields, default="-created_at"):
    """Return a safe ordering string derived from *value*.

    Strips at most one leading '-' (descending indicator), checks the bare
    field name against *allowed_fields*, and reconstructs the value.  Inputs
    with multiple leading dashes (e.g. ``--created_at``) are rejected and
    *default* is returned instead, preventing both allowlist bypass and
    malformed tokens from reaching ``.order_by()``.

    Call this before passing any user-supplied ordering string to .order_by() or
    a paginator to prevent ORM order_by injection.
    """
    if not value:
        return default
    is_desc = value.startswith("-")
    bare = value[1:] if is_desc else value
    # Reject malformed prefixes like "--created_at".
    if bare.startswith("-"):
        return default
    if bare not in allowed_fields:
        return default
    return f"-{bare}" if is_desc else bare


def order_issue_queryset(issue_queryset, order_by_param="-created_at"):
    # Reject any field that is not in the allowlist before building the queryset.
    # An unrecognised value is silently replaced with the safe default so callers
    # receive consistent output rather than an ORM error or data leak.
    order_by_param = sanitize_order_by(order_by_param, ISSUE_ORDER_BY_ALLOWLIST, default="-created_at")
    # Priority Ordering
    if order_by_param == "priority" or order_by_param == "-priority":
        issue_queryset = issue_queryset.annotate(
            priority_order=Case(
                *[When(priority=p, then=Value(i)) for i, p in enumerate(PRIORITY_ORDER)],
                output_field=CharField(),
            )
        ).order_by("priority_order", "-created_at")
        order_by_param = "priority_order" if order_by_param.startswith("-") else "-priority_order"
    # State Ordering
    elif order_by_param in ["state__group", "-state__group"]:
        state_order = STATE_ORDER if order_by_param in ["state__name", "state__group"] else STATE_ORDER[::-1]
        issue_queryset = issue_queryset.annotate(
            state_order=Case(
                *[When(state__group=state_group, then=Value(i)) for i, state_group in enumerate(state_order)],
                default=Value(len(state_order)),
                output_field=CharField(),
            )
        ).order_by("state_order", "-created_at")
        order_by_param = "-state_order" if order_by_param.startswith("-") else "state_order"
    # Kustomisasi Paradise: status persetujuan terbaru (sama dengan badge & filter approval_status).
    elif order_by_param in ["approval_status", "-approval_status"]:
        issue_queryset = _annotate_approval_order(issue_queryset, descending=order_by_param.startswith("-"))
        issue_queryset = issue_queryset.order_by("approval_order", "-created_at")
        order_by_param = "approval_order"
    # assignee and label ordering
    elif order_by_param in [
        "labels__name",
        "assignees__first_name",
        "issue_module__module__name",
        "-labels__name",
        "-assignees__first_name",
        "-issue_module__module__name",
    ]:
        issue_queryset = issue_queryset.annotate(
            min_values=Min(order_by_param[1::] if order_by_param.startswith("-") else order_by_param)
        ).order_by(
            "-min_values" if order_by_param.startswith("-") else "min_values",
            "-created_at",
        )
        order_by_param = "-min_values" if order_by_param.startswith("-") else "min_values"
    else:
        # If the order_by_param is created_at, then don't add the -created_at
        if "created_at" in order_by_param:
            issue_queryset = issue_queryset.order_by(order_by_param)
        else:
            issue_queryset = issue_queryset.order_by(order_by_param, "-created_at")
        order_by_param = order_by_param
    return issue_queryset, order_by_param


def _annotate_approval_order(issue_queryset, descending=False):
    """Annotate `approval_order` from the LATEST approval row of each issue.

    Ascending: awaiting, rejected, approved. Descending flips those three, but
    issues that never needed approval stay last both ways, like empty dates.
    """
    # Impor di sini: plane.db.models memuat utils saat diimpor (hindari impor melingkar).
    from plane.db.models import PersetujuanPenugasan

    urutan = APPROVAL_ORDER[::-1] if descending else APPROVAL_ORDER
    status_terbaru = (
        PersetujuanPenugasan.objects.filter(issue_id=OuterRef("pk")).order_by("-created_at").values("status")[:1]
    )
    return issue_queryset.annotate(approval_status_terbaru=Subquery(status_terbaru)).annotate(
        approval_order=Case(
            *[When(approval_status_terbaru=status, then=Value(i)) for i, status in enumerate(urutan)],
            default=Value(len(urutan)),
            output_field=IntegerField(),
        )
    )
