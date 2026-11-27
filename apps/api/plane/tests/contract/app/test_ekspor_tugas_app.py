# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the Excel export of work item lists.

The workbook has three sheets: the work items, their comments, and their
history. The last two only ever cover rows of the first.

Three routes cover every list page: the department list (also used by the module
and department view pages), the workspace views list, and the profile list. The
promise: the file holds the rows the list shows, in the same order, and never a
row the viewer may not see.
"""

import json
import zipfile
from datetime import date, datetime, timezone as tz
from io import BytesIO
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from openpyxl import load_workbook
from rest_framework.test import APIClient

from plane.db.models import (
    Estimate,
    EstimatePoint,
    FileAsset,
    Issue,
    IssueActivity,
    IssueAssignee,
    IssueComment,
    IssueLabel,
    IssueSubscriber,
    Label,
    Module,
    ModuleIssue,
    PersetujuanPenugasan,
    Profile,
    Project,
    ProjectMember,
    Ruang,
    State,
    User,
    WorkspaceMember,
)
from plane.bgtasks.issue_activities_task import delete_issue_relation_activity
from plane.utils import ekspor_tugas
from plane.utils.aturan import segarkan
from plane.utils.order_queryset import ISSUE_ORDER_BY_ALLOWLIST

PROJECT_LIST = "/api/workspaces/{slug}/projects/{project}/issues/"
PROJECT_EXPORT = "/api/workspaces/{slug}/projects/{project}/issues/export-xlsx/"
WORKSPACE_LIST = "/api/workspaces/{slug}/issues/"
WORKSPACE_EXPORT = "/api/workspaces/{slug}/issues/export-xlsx/"
PROFILE_LIST = "/api/workspaces/{slug}/user-issues/{user}/"
PROFILE_EXPORT = "/api/workspaces/{slug}/user-issues/{user}/export-xlsx/"

HEADERS_EN = [
    "Key",
    "Title",
    "Department",
    "State",
    "State group",
    "Priority",
    "Assignees",
    "Created by",
    "Start date",
    "Due date",
    "Completed at",
    "Approval status",
    "Timeliness",
    "Labels",
    "Modules",
    "Parent",
    "Sub-items",
    "Estimate",
    "Created",
    "Updated",
    "Description",
]


def _user(name, workspace, role=15, language="en", user_timezone="Asia/Jakarta"):
    uid = uuid4().hex[:8]
    user = User.objects.create(
        email=f"{name}-{uid}@plane.so",
        username=f"{name}_{uid}",
        display_name=name,
        user_timezone=user_timezone,
    )
    Profile.objects.create(user=user, language=language)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _project(workspace, owner, identifier, **extra):
    project = Project.objects.create(
        name=f"Project {identifier}", identifier=identifier, workspace=workspace, created_by=owner, **extra
    )
    for name, group in (("Todo", "unstarted"), ("Doing", "started"), ("Done", "completed")):
        State.objects.create(
            name=name, group=group, color="#000000", project=project, workspace=workspace, default=name == "Todo"
        )
    _join(project, owner, 20)
    return project


def _join(project, user, role=15):
    return ProjectMember.objects.create(project=project, member=user, workspace=project.workspace, role=role)


def _state(project, name):
    return State.objects.get(project=project, name=name)


def _issue(project, author, name="Task", **extra):
    issue = Issue(name=name, project=project, workspace=project.workspace, **extra)
    issue.save(created_by_id=author.id)
    return issue


def _assign(issue, user):
    return IssueAssignee.objects.create(issue=issue, assignee=user, project=issue.project, workspace=issue.workspace)


def _sheet(response):
    assert response.status_code == 200, getattr(response, "data", response.content[:300])
    return load_workbook(BytesIO(response.content)).active


def _rows(response):
    """One dict per data row, keyed by the English header."""
    values = list(_sheet(response).iter_rows(values_only=True))
    return [dict(zip(values[0], row)) for row in values[1:]]


def _extra_rows(response, name):
    """Data rows of a second or third sheet, as lists."""
    assert response.status_code == 200, getattr(response, "data", response.content[:300])
    sheet = load_workbook(BytesIO(response.content))[name]
    return [list(row) for row in sheet.iter_rows(min_row=2, values_only=True)]


def _mention(target, kind="user_mention"):
    return f'<mention-component entity_identifier="{target.id}" entity_name="{kind}"></mention-component>'


def _comment(issue, author, html, **extra):
    return IssueComment.objects.create(
        issue=issue, actor=author, comment_html=html, project=issue.project, workspace=issue.workspace, **extra
    )


def _activity(issue, actor, field, old=None, new=None, verb="updated", at=None, **extra):
    row = IssueActivity.objects.create(
        issue=issue,
        actor=actor,
        field=field,
        verb=verb,
        old_value=old,
        new_value=new,
        project=issue.project,
        workspace=issue.workspace,
        **extra,
    )
    if at:
        IssueActivity.objects.filter(pk=row.pk).update(created_at=at)
    return row


def _keys(response):
    return [row["Key"] for row in _rows(response)]


def _list_keys(response):
    assert response.status_code == 200, response.data
    identifiers = {str(p.id): p.identifier for p in Project.objects.all()}
    return [f"{identifiers[str(r['project_id'])]}-{r['sequence_id']}" for r in response.data["results"]]


def _key(issue):
    return f"{issue.project.identifier}-{issue.sequence_id}"


@pytest.fixture
def owner(db, create_user, workspace):
    Profile.objects.create(user=create_user, language="en")
    return create_user


@pytest.fixture
def project(owner, workspace):
    return _project(workspace, owner, "EXP")


@pytest.mark.contract
@pytest.mark.django_db
class TestWorkbook:
    def test_columns_values_and_real_dates(self, workspace, owner, project):
        client = _client(owner)
        budi = _user("budi", workspace)
        gone = _user("gone", workspace)
        _join(project, budi)
        _join(project, gone)
        parent = _issue(project, owner, "Parent")
        estimate = Estimate.objects.create(name="Points", project=project, workspace=workspace)
        point = EstimatePoint.objects.create(estimate=estimate, key=1, value="5", project=project, workspace=workspace)
        issue = _issue(
            project,
            owner,
            "Full row",
            parent=parent,
            state=_state(project, "Done"),
            priority="high",
            start_date=date(2026, 10, 1),
            target_date=date(2026, 12, 1),
            estimate_point=point,
        )
        _issue(project, owner, "Child", parent=issue)
        # 20:00 UTC is 03:00 the next day in Jakarta.
        Issue.objects.filter(pk=issue.pk).update(
            completed_at=datetime(2026, 11, 1, 20, 0, tzinfo=tz.utc),
            created_at=datetime(2026, 10, 1, 1, 30, tzinfo=tz.utc),
        )
        _assign(issue, budi)
        _assign(issue, gone).delete()  # soft delete of the through row
        kept = Label.objects.create(name="kept", project=project, workspace=workspace)
        unlinked = Label.objects.create(name="unlinked", project=project, workspace=workspace)
        dead = Label.objects.create(name="dead", project=project, workspace=workspace)
        for label in (kept, unlinked, dead):
            IssueLabel.objects.create(issue=issue, label=label, project=project, workspace=workspace)
        IssueLabel.objects.filter(label=unlinked).update(deleted_at=timezone.now())
        Label.all_objects.filter(pk=dead.pk).update(deleted_at=timezone.now())
        live = Module.objects.create(name="Live module", project=project, workspace=workspace)
        old = Module.objects.create(name="Removed module", project=project, workspace=workspace)
        for module in (live, old):
            ModuleIssue.objects.create(issue=issue, module=module, project=project, workspace=workspace)
        ModuleIssue.objects.filter(module=old).update(deleted_at=timezone.now())
        for status_value in ("ditolak", "disetujui"):
            PersetujuanPenugasan.objects.create(
                workspace=workspace,
                project=project,
                issue=issue,
                pemohon=budi,
                penerima=owner,
                status=status_value,
            )

        response = client.get(PROJECT_EXPORT.format(slug=workspace.slug, project=project.id))

        sheet = _sheet(response)
        assert [c.value for c in sheet[1]] == HEADERS_EN
        assert sheet.freeze_panes == "A2"
        assert sheet.auto_filter.ref == "A1:U4"
        row = next(r for r in _rows(response) if r["Title"] == "Full row")
        assert row["Key"] == _key(issue)
        assert row["Department"] == "Project EXP"
        assert (row["State"], row["State group"], row["Priority"]) == ("Done", "Completed", "High")
        assert row["Assignees"] == "budi"
        assert row["Start date"] == datetime(2026, 10, 1)
        assert row["Due date"] == datetime(2026, 12, 1)
        assert row["Completed at"] == datetime(2026, 11, 2, 3, 0)
        assert row["Created"] == datetime(2026, 10, 1, 8, 30)
        assert row["Approval status"] == "Approved"
        assert row["Timeliness"] == "On time"
        assert row["Labels"] == "kept"
        assert row["Modules"] == "Live module"
        assert row["Parent"] == _key(parent)
        assert row["Sub-items"] == 1
        assert row["Estimate"] == "5"
        date_cell = sheet.cell(row=[c.value for c in sheet["B"]].index("Full row") + 1, column=10)
        assert date_cell.is_date

    def test_headers_and_values_follow_the_users_language(self, workspace, owner, project):
        Profile.objects.filter(user=owner).update(language="id")
        _issue(project, owner, priority="urgent")
        # A fresh instance, as a real request loads it (no cached profile).
        reader = User.objects.get(pk=owner.pk)

        response = _client(reader).get(PROJECT_EXPORT.format(slug=workspace.slug, project=project.id))

        row = _rows(response)[0]
        assert list(row)[:3] == ["Kode", "Judul", "Departemen"]
        assert list(row)[-1] == "Deskripsi"
        assert load_workbook(BytesIO(response.content)).sheetnames == ["Item kerja", "Komentar", "Aktivitas"]
        assert (row["Prioritas"], row["Grup status"]) == ("Mendesak", "Belum dimulai")

    @pytest.mark.parametrize(
        ("created_day", "due", "expected"),
        [
            (1, date(2026, 11, 1), "Late"),
            (1, date(2026, 11, 2), "On time"),
            # Recorded the day it was finished: not late for the days before it existed.
            (2, date(2026, 10, 1), "On time"),
            (1, None, "No due date"),
        ],
    )
    def test_timeliness_uses_the_office_day(self, workspace, owner, project, created_day, due, expected):
        issue = _issue(project, owner, state=_state(project, "Done"))
        _issue(project, owner, "still open", target_date=date(2026, 1, 1))
        # `update` skips the automatic dates that saving a finished item fills in.
        Issue.objects.filter(pk=issue.pk).update(
            target_date=due,
            completed_at=datetime(2026, 11, 1, 20, 0, tzinfo=tz.utc),  # 2 November in Jakarta
            created_at=datetime(2026, 11, created_day, 1, 0, tzinfo=tz.utc),
        )

        response = _client(owner).get(
            PROJECT_EXPORT.format(slug=workspace.slug, project=project.id), {"order_by": "sequence_id"}
        )

        assert [r["Timeliness"] for r in _rows(response)] == [expected, None]

    def test_text_is_never_a_formula_and_has_no_visible_apostrophe(self, workspace, owner, project):
        titles = ['=HYPERLINK("http://evil","x")', "+1+1", "-2+3", "@SUM(A1)", "#REF!"]
        for title in titles:
            _issue(project, owner, title)
        dirty = _issue(project, owner, "bad\x01\x07\x1fchars\ufffe")
        label = Label.objects.create(name="=1+1", project=project, workspace=workspace)
        IssueLabel.objects.create(issue=dirty, label=label, project=project, workspace=workspace)

        response = _client(owner).get(
            PROJECT_EXPORT.format(slug=workspace.slug, project=project.id), {"order_by": "created_at"}
        )

        sheet = _sheet(response)
        cells = [sheet.cell(row=n, column=2) for n in range(2, 8)]
        assert [c.value for c in cells] == [*titles, "badchars"]
        assert {c.data_type for c in cells} == {"s"}
        assert [c.quotePrefix for c in cells[:4]] == [True] * 4
        assert sheet.cell(row=7, column=14).value == "=1+1"
        assert sheet.cell(row=7, column=14).data_type == "s"
        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            assert b"<f>" not in archive.read("xl/worksheets/sheet1.xml")

    def test_file_name(self, workspace, owner, project):
        response = _client(owner).get(
            PROJECT_EXPORT.format(slug=workspace.slug, project=project.id),
            {"export_name": 'Sales & Marketing "Q4"\r\n/../x'},
        )

        today = timezone.now().astimezone(ZoneInfo(owner.user_timezone)).date()
        assert response["Content-Disposition"] == (
            f'attachment; filename="sales-marketing-q4-x-work-items-{today.isoformat()}.xlsx"'
        )


@pytest.mark.contract
@pytest.mark.django_db
class TestSameRowsAsTheList:
    @pytest.fixture
    def varied(self, workspace, owner, project):
        """Rows with ties, empty values, relations, and a sub item."""
        budi = _user("budi", workspace)
        ani = _user("ani", workspace)
        _join(project, budi)
        _join(project, ani)
        labels = [Label.objects.create(name=n, project=project, workspace=workspace) for n in ("alfa", "beta")]
        module = Module.objects.create(name="Mod", project=project, workspace=workspace)
        specs = [
            ("a", "urgent", "Todo", date(2026, 1, 3), [budi, ani], [labels[1]]),
            ("b", "low", "Done", None, [ani], [labels[0], labels[1]]),
            ("c", "high", "Doing", date(2026, 1, 1), [], []),
            ("d", "none", "Todo", date(2026, 1, 2), [budi], [labels[0]]),
            ("e", "high", "Doing", None, [], []),
        ]
        issues = []
        for name, priority, state, due, assignees, tags in specs:
            issue = _issue(
                project,
                owner,
                name,
                priority=priority,
                state=_state(project, state),
                target_date=due,
                start_date=due,
            )
            for user in assignees:
                _assign(issue, user)
            for tag in tags:
                IssueLabel.objects.create(issue=issue, label=tag, project=project, workspace=workspace)
            issues.append(issue)
        ModuleIssue.objects.create(issue=issues[0], module=module, project=project, workspace=workspace)
        _issue(project, owner, "child", parent=issues[0])
        PersetujuanPenugasan.objects.create(
            workspace=workspace,
            project=project,
            issue=issues[2],
            pemohon=budi,
            penerima=owner,
            status="menunggu",
        )
        return {"issues": issues, "budi": budi, "ani": ani, "module": module}

    @pytest.mark.parametrize("order_by", sorted(ISSUE_ORDER_BY_ALLOWLIST))
    @pytest.mark.parametrize("direction", ["", "-"])
    def test_every_order_matches_all_three_lists(self, workspace, owner, project, varied, order_by, direction):
        client = _client(owner)
        params = {"order_by": direction + order_by, "sub_issue": "true"}
        routes = [
            (PROJECT_LIST, PROJECT_EXPORT),
            (WORKSPACE_LIST, WORKSPACE_EXPORT),
            (PROFILE_LIST, PROFILE_EXPORT),
        ]
        for list_url, export_url in routes:
            url_args = {"slug": workspace.slug, "project": project.id, "user": owner.id}
            listed = _list_keys(client.get(list_url.format(**url_args), params))
            exported = _keys(client.get(export_url.format(**url_args), params))
            assert len(listed) == 6
            assert exported == listed, export_url

    def test_filters_match_the_list(self, workspace, owner, project, varied):
        client = _client(owner)
        url_args = {"slug": workspace.slug, "project": project.id}
        queries = [
            {"filters": json.dumps({"and": [{"priority__in": "high,urgent"}]}), "order_by": "-priority"},
            {"filters": json.dumps({"assignee_id__in": str(varied["budi"].id)}), "order_by": "target_date"},
            {"module": str(varied["module"].id), "sub_issue": "true"},
            {"sub_issue": "false"},
            {"assignees": str(varied["ani"].id)},
            {"filters": json.dumps({"approval_status__in": "menunggu"})},
        ]
        expected_counts = [3, 2, 1, 5, 2, 1]
        for params, count in zip(queries, expected_counts):
            listed = _list_keys(client.get(PROJECT_LIST.format(**url_args), params))
            exported = _keys(client.get(PROJECT_EXPORT.format(**url_args), params))
            assert len(listed) == count, params
            assert exported == listed, params

    def test_grouping_and_paging_params_do_not_cut_the_file(self, workspace, owner, project, varied):
        response = _client(owner).get(
            PROJECT_EXPORT.format(slug=workspace.slug, project=project.id),
            {"group_by": "state_id", "per_page": "1", "cursor": "1:1:0"},
        )

        assert len(_rows(response)) == 6

    @pytest.mark.parametrize("export_url", [PROJECT_EXPORT, WORKSPACE_EXPORT, PROFILE_EXPORT])
    def test_a_relation_filter_never_duplicates_a_row(self, workspace, owner, project, varied, export_url):
        both = f"{varied['budi'].id},{varied['ani'].id}"
        for params in ({"filters": json.dumps({"assignee_id__in": both})}, {"assignees": both}):
            response = _client(owner).get(
                export_url.format(slug=workspace.slug, project=project.id, user=owner.id), params
            )

            keys = _keys(response)
            assert sorted(keys) == sorted(_key(i) for i in (varied["issues"][n] for n in (0, 1, 3)))

    def test_profile_tab_params(self, workspace, owner, project, varied):
        ani = varied["ani"]
        IssueSubscriber.objects.create(issue=varied["issues"][2], subscriber=ani, project=project, workspace=workspace)
        url_args = {"slug": workspace.slug, "user": ani.id}
        for tab, count in (("assignees", 2), ("created_by", 0), ("subscriber", 1)):
            params = {tab: str(ani.id)}
            listed = _list_keys(_client(owner).get(PROFILE_LIST.format(**url_args), params))
            exported = _keys(_client(owner).get(PROFILE_EXPORT.format(**url_args), params))
            assert len(exported) == count, tab
            assert exported == listed, tab

    def test_drafts_archived_and_triage_stay_out(self, workspace, owner, project):
        shown = _issue(project, owner, "shown")
        draft = _issue(project, owner, "draft")
        archived = _issue(project, owner, "archived")
        triage = _issue(project, owner, "intake")
        triage_state = State.all_state_objects.create(
            name="Triage", group="triage", color="#000000", project=project, workspace=workspace
        )
        Issue.objects.filter(pk=draft.pk).update(is_draft=True)
        Issue.objects.filter(pk=archived.pk).update(archived_at=date(2026, 1, 1))
        Issue.objects.filter(pk=triage.pk).update(state=triage_state)

        for url in (PROJECT_EXPORT, WORKSPACE_EXPORT, PROFILE_EXPORT):
            response = _client(owner).get(url.format(slug=workspace.slug, project=project.id, user=owner.id))
            assert _keys(response) == [_key(shown)], url

    def test_an_invalid_filter_is_rejected(self, workspace, owner, project):
        response = _client(owner).get(
            PROJECT_EXPORT.format(slug=workspace.slug, project=project.id),
            {"filters": json.dumps({"password__in": "x"})},
        )

        assert response.status_code == 400


@pytest.mark.contract
@pytest.mark.django_db
class TestWhoMayExport:
    def _urls(self, workspace, project, user):
        args = {"slug": workspace.slug, "project": project.id, "user": user.id}
        return [url.format(**args) for url in (PROJECT_EXPORT, WORKSPACE_EXPORT, PROFILE_EXPORT)]

    def test_workspace_guest_is_refused_everywhere(self, workspace, owner, project):
        guest = _user("guest", workspace, role=5)
        _join(project, guest, 5)
        project.guest_view_all_features = True
        project.save(update_fields=["guest_view_all_features"])
        _issue(project, guest)

        for url in self._urls(workspace, project, guest):
            assert _client(guest).get(url).status_code == 403, url

    def test_outsider_and_removed_member_are_refused(self, workspace, owner, project):
        outsider = User.objects.create(email="out@plane.so", username="out")
        former = _user("former", workspace)
        WorkspaceMember.objects.filter(member=former).update(is_active=False)
        _join(project, former)

        for user in (outsider, former):
            for url in self._urls(workspace, project, owner):
                assert _client(user).get(url).status_code == 403, url

    def test_anonymous_is_refused(self, workspace, owner, project):
        for url in self._urls(workspace, project, owner):
            assert APIClient().get(url).status_code in (401, 403), url

    def test_non_member_of_the_department_gets_nothing_from_it(self, workspace, owner, project):
        member = _user("member", workspace)
        other = _project(workspace, owner, "OTH")
        _join(other, member)
        hidden = _issue(project, owner, "not mine")
        _assign(hidden, member)
        visible = _issue(other, owner, "mine")
        _assign(visible, member)

        client = _client(member)
        assert client.get(PROJECT_EXPORT.format(slug=workspace.slug, project=project.id)).status_code == 403
        assert _keys(client.get(WORKSPACE_EXPORT.format(slug=workspace.slug))) == [_key(visible)]
        assert _keys(client.get(PROFILE_EXPORT.format(slug=workspace.slug, user=member.id))) == [_key(visible)]

    def test_soft_deleted_membership_gives_nothing(self, workspace, owner, project):
        former = _user("former", workspace)
        ProjectMember.objects.filter(pk=_join(project, former).pk).update(deleted_at=timezone.now())
        issue = _issue(project, owner)
        _assign(issue, former)

        client = _client(former)
        assert client.get(PROJECT_EXPORT.format(slug=workspace.slug, project=project.id)).status_code == 403
        assert _keys(client.get(WORKSPACE_EXPORT.format(slug=workspace.slug))) == []
        assert _keys(client.get(PROFILE_EXPORT.format(slug=workspace.slug, user=former.id))) == []

    @pytest.mark.parametrize("view_all", [False, True])
    def test_department_guest_scope(self, workspace, owner, project, view_all):
        """A workspace member who is only a guest in one department."""
        person = _user("limited", workspace)
        _join(project, person, 5)
        project.guest_view_all_features = view_all
        project.save(update_fields=["guest_view_all_features"])
        other = _project(workspace, owner, "OTH")
        _join(other, person)
        own = _issue(project, person, "own")
        foreign = _issue(project, owner, "foreign")
        _assign(foreign, person)
        elsewhere = _issue(other, owner, "elsewhere")
        _assign(elsewhere, person)
        in_project = {_key(own), _key(foreign)} if view_all else {_key(own)}

        client = _client(person)
        expected = {
            PROJECT_EXPORT: in_project,
            WORKSPACE_EXPORT: in_project | {_key(elsewhere)},
            PROFILE_EXPORT: in_project | {_key(elsewhere)},
        }
        for url, keys in expected.items():
            response = client.get(url.format(slug=workspace.slug, project=project.id, user=person.id))
            assert set(_keys(response)) == keys, url

    def test_private_items_and_hidden_parents(self, workspace, owner, project):
        assignee = _user("assignee", workspace)
        peer = _user("peer", workspace)
        _join(project, assignee)
        _join(project, peer)
        secret = _issue(project, owner, "secret", is_private=True)
        _assign(secret, assignee)
        child = _issue(project, owner, "child", parent=secret)
        for user in (assignee, peer):
            _assign(child, user)

        for url in (PROJECT_EXPORT, WORKSPACE_EXPORT, PROFILE_EXPORT):
            args = {"slug": workspace.slug, "project": project.id}
            seen_by_peer = _rows(_client(peer).get(url.format(**args, user=peer.id), {"sub_issue": "true"}))
            assert [(r["Title"], r["Parent"]) for r in seen_by_peer] == [("child", None)], url
            seen_by_assignee = _rows(_client(assignee).get(url.format(**args, user=assignee.id), {"sub_issue": "true"}))
            assert {(r["Title"], r["Parent"]) for r in seen_by_assignee} == {
                ("secret", None),
                ("child", _key(secret)),
            }, url

    def test_parent_in_a_department_the_viewer_is_not_in_is_blank(self, workspace, owner, project):
        member = _user("member", workspace)
        _join(project, member)
        other = _project(workspace, owner, "OTH")
        parent = _issue(other, owner, "far parent")
        _issue(project, owner, "child", parent=parent)

        response = _client(member).get(
            PROJECT_EXPORT.format(slug=workspace.slug, project=project.id), {"sub_issue": "true"}
        )

        assert [r["Parent"] for r in _rows(response)] == [None]


@pytest.mark.contract
@pytest.mark.django_db
class TestDescriptionAndComments:
    def test_description_reads_as_text(self, workspace, owner, project):
        budi = _user("budi", workspace)
        other = _issue(project, owner, "Other")
        room = Ruang.objects.create(workspace=workspace, tipe=Ruang.Tipe.KANAL, nama="gudang")
        secret_room = Ruang.objects.create(workspace=workspace, tipe=Ruang.Tipe.PRIVAT, nama="akuisisi")
        html = (
            f"<h2>Plan</h2><p>Ask {_mention(budi)} about {_mention(other, 'issue_mention')}<br>"
            f"in {_mention(room, 'channel_mention')}, not {_mention(secret_room, 'channel_mention')}.</p>"
            "<ul><li><p>one</p><ul><li><p>nested</p></li></ul></li></ul>"
            '<ul data-type="taskList">'
            '<li data-type="taskItem" data-checked="true"><label><input type="checkbox"><span></span></label>'
            "<div><p>done</p></div></li>"
            '<li data-type="taskItem" data-checked="false"><div><p>open</p></div></li></ul>'
            "<table><tbody><tr><th><p>Item</p></th><th><p>Qty</p></th></tr>"
            "<tr><td><p>Box</p></td><td><p>4</p></td></tr></tbody></table>"
            '<p><a href="https://example.com/sop">the SOP</a> &amp; '
            '<span data-type="emoji" data-name="smile">😄</span></p>'
            '<image-component src="abc"></image-component>'
            '<file-component src="abc" name="rekap.pdf"></file-component><p>end</p>'
        )
        _issue(project, owner, "Doc", description_html=html)
        _issue(project, owner, "Empty")

        response = _client(owner).get(PROJECT_EXPORT.format(slug=workspace.slug, project=project.id))

        text = {r["Title"]: r["Description"] for r in _rows(response)}
        assert text["Doc"].split("\n") == [
            "Plan",
            f"Ask @budi about {_key(other)}",
            "in #gudang, not #private-channel.",
            "- one",
            "- nested",
            "[x] done",
            "[ ] open",
            "Item | Qty",
            "Box | 4",
            "the SOP (https://example.com/sop) & 😄",
            "[image]",
            "[file: rekap.pdf]",
            "end",
        ]
        assert not text["Empty"]
        cell = _sheet(response).cell(row=2, column=len(HEADERS_EN))
        assert cell.alignment.wrap_text and cell.alignment.vertical == "top"

    def test_broken_stored_html_does_not_break_the_file(self, workspace, owner, project):
        # The API accepts HTML the editor would never write.
        nested = (
            f'<image-component src="x"><img src="y">{_mention(owner)}</image-component>'
            f'<mention-component entity_identifier="{owner.id}" entity_name="user_mention">'
            f'<mention-component entity_identifier="not-a-uuid">'
            "<table><tr><td><table><tr><td>deep</td></tr></table></td></tr></table><p>tail\x07"
        )
        issue = _issue(project, owner, description_html=nested)
        _comment(issue, owner, "<ul><li>unclosed <file-component name='a.pdf'><a href='http://x.test'>")

        response = _client(owner).get(PROJECT_EXPORT.format(slug=workspace.slug, project=project.id))

        assert "[image]" in _rows(response)[0]["Description"]
        assert "[file: a.pdf]" in _extra_rows(response, "Comments")[0][4]

    def test_comments_follow_the_row_order_then_time(self, workspace, owner, project):
        budi = _user("budi", workspace)
        _join(project, budi)
        first = _issue(project, owner, "first")
        second = _issue(project, owner, "second")
        late = _comment(second, owner, "<p>on second</p>")
        newer = _comment(first, budi, f"<p>newer {_mention(owner)}</p>")
        older = _comment(first, None, "<p>=1+1</p>")
        gone = _comment(first, budi, "<p>deleted</p>")
        IssueComment.objects.filter(pk=gone.pk).update(deleted_at=timezone.now())
        for comment, hour in ((late, 1), (newer, 3), (older, 2)):
            IssueComment.objects.filter(pk=comment.pk).update(created_at=datetime(2026, 11, 1, hour, tzinfo=tz.utc))

        response = _client(owner).get(
            PROJECT_EXPORT.format(slug=workspace.slug, project=project.id), {"order_by": "sequence_id"}
        )

        assert _extra_rows(response, "Comments") == [
            [_key(first), "first", "System", datetime(2026, 11, 1, 9), "=1+1"],
            [_key(first), "first", "budi", datetime(2026, 11, 1, 10), f"newer @{owner.display_name}"],
            [_key(second), "second", owner.display_name, datetime(2026, 11, 1, 8), "on second"],
        ]
        formula = load_workbook(BytesIO(response.content))["Comments"]["E2"]
        assert formula.data_type == "s" and formula.quotePrefix

    def test_history_reads_like_the_app(self, workspace, owner, project):
        issue = _issue(project, owner, "tracked")
        other = _issue(project, owner, "other")
        asset = FileAsset.objects.create(
            attributes={"name": "rekap.pdf"},
            asset="ws/raw-storage-key",
            issue=issue,
            project=project,
            workspace=workspace,
            entity_type=FileAsset.EntityTypeContext.ISSUE_ATTACHMENT,
        )
        steps = [
            (None, {"verb": "created"}),
            ("state", {"old": "Todo", "new": "Doing"}),
            ("priority", {"old": "none", "new": "high"}),
            ("description", {"old": "<p>secret old text</p>", "new": "<p>secret new text</p>"}),
            ("assignees", {"old": "", "new": "budi"}),
            ("target_date", {"old": "", "new": "2026-12-01"}),
            ("approval", {"verb": "rejected", "new": "numbers are off"}),
            ("approval", {"verb": "requested"}),
            ("attachment", {"verb": "created", "new": "ws/raw-storage-key", "new_identifier": asset.pk}),
            ("attachment", {"verb": "deleted"}),
            ("is_private", {"old": "false", "new": "true"}),
            ("archived_at", {"new": "manual_archive"}),
            ("archived_at", {"old": "archive", "new": "restore"}),
            ("parent", {"old": "", "new": _key(other), "new_identifier": other.pk}),
            ("blocked_by", {"old": "", "new": _key(other), "old_identifier": other.pk}),
            ("relates_to", {"old": _key(other), "new": "", "old_identifier": other.pk, "verb": "deleted"}),
            ("estimate_points", {"old": "3", "new": "5"}),
        ]
        for hidden in ("comment", "reaction", "vote", "draft"):
            _activity(issue, owner, hidden, new="never shown")
        for minute, (field, extra) in enumerate(steps):
            _activity(issue, owner, field, at=datetime(2026, 11, 1, 1, minute, tzinfo=tz.utc), **extra)

        response = _client(owner).get(PROJECT_EXPORT.format(slug=workspace.slug, project=project.id))

        rows = [r for r in _extra_rows(response, "Activity") if r[0] == _key(issue)]
        assert [tuple(r[4:]) for r in rows] == [
            ("Work item created", None, None),
            ("State", "Todo", "Doing"),
            ("Priority", "None", "High"),
            ("Description", None, "Changed"),
            ("Assignee", None, "budi"),
            ("Due date", None, "2026-12-01"),
            ("Approval", None, "Rejected: numbers are off"),
            ("Approval", None, "Requested"),
            ("Attachment", None, "rekap.pdf"),
            ("Attachment", None, "Removed"),
            ("Private", "No", "Yes"),
            ("Archive", None, "Archived"),
            ("Archive", None, "Restored"),
            ("Parent", None, _key(other)),
            ("Blocked by", None, _key(other)),
            ("Related to", _key(other), None),
            ("Estimate", "3", "5"),
        ]
        assert rows[0][1:4] == ["tracked", owner.display_name, datetime(2026, 11, 1, 8, 0)]
        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            xml = b"".join(archive.read(name) for name in archive.namelist())
        assert b"secret" not in xml and b"never shown" not in xml and b"raw-storage-key" not in xml

    @pytest.mark.parametrize("url", [PROJECT_EXPORT, WORKSPACE_EXPORT, PROFILE_EXPORT])
    def test_nothing_about_work_items_the_reader_cannot_see(self, workspace, owner, project, url):
        peer = _user("peer", workspace)
        _join(project, peer)
        far = _project(workspace, owner, "FAR")
        secret = _issue(project, owner, "secret title", is_private=True)
        foreign = _issue(far, owner, "foreign title")
        shown = _issue(project, owner, "shown")
        _assign(shown, peer)
        _comment(secret, owner, "<p>hidden remark</p>")
        _activity(secret, owner, "state", old="Todo", new="hidden state")
        _comment(foreign, owner, "<p>far remark</p>")
        for target in (secret, foreign):
            _activity(shown, owner, "relates_to", old="", new=_key(target), old_identifier=target.pk)
            _activity(shown, owner, "parent", old=_key(target), new="", old_identifier=target.pk)
        # Removing a relation, as the app records it: the row it writes on `shown` names `secret`
        # but carries the id of `shown`.
        written = []
        delete_issue_relation_activity(
            requested_data=json.dumps({"related_issue": str(shown.id), "relation_type": "relates_to"}),
            current_instance=None,
            issue_id=str(secret.id),
            project_id=str(project.id),
            workspace_id=str(workspace.id),
            actor_id=str(owner.id),
            issue_activities=written,
            epoch=0,
        )
        IssueActivity.objects.bulk_create(written)
        mentions = f"<p>see {_mention(secret, 'issue_mention')} and {_mention(foreign, 'issue_mention')}</p>"
        _comment(shown, owner, mentions)
        Issue.objects.filter(pk=shown.pk).update(description_html=mentions)

        response = _client(peer).get(url.format(slug=workspace.slug, project=project.id, user=peer.id))

        assert [r["Description"] for r in _rows(response)] == ["see #work-item and #work-item"]
        assert [r[4] for r in _extra_rows(response, "Comments")] == ["see #work-item and #work-item"]
        history = [tuple(r[4:]) for r in _extra_rows(response, "Activity")]
        expected = [("Related to", None, "Another work item"), ("Parent", "Another work item", None)] * 2
        expected.append(("Related to", "Another work item", None))
        assert sorted(history, key=str) == sorted(expected, key=str)
        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            xml = b"".join(archive.read(name) for name in archive.namelist()).decode()
        for leaked in (_key(secret), _key(foreign), "secret title", "hidden remark", "hidden state", "far remark"):
            assert leaked not in xml, leaked

    def test_history_words_follow_the_users_language(self, workspace, owner, project):
        Profile.objects.filter(user=owner).update(language="id")
        issue = _issue(project, owner, description_html='<image-component src="abc"></image-component>')
        _activity(issue, owner, "approval", verb="approved")
        _activity(issue, owner, "priority", old="low", new="urgent")
        reader = User.objects.get(pk=owner.pk)

        response = _client(reader).get(PROJECT_EXPORT.format(slug=workspace.slug, project=project.id))

        assert _rows(response)[0]["Deskripsi"] == "[gambar]"
        assert sorted(tuple(r[4:]) for r in _extra_rows(response, "Aktivitas")) == [
            ("Persetujuan", None, "Disetujui"),
            ("Prioritas", "Rendah", "Mendesak"),
        ]


@pytest.mark.contract
@pytest.mark.django_db
class TestSize:
    def _bulk(self, project, author, count, start=1):
        state = _state(project, "Todo")
        Issue.objects.bulk_create(
            [
                Issue(
                    name=f"bulk {n}",
                    project=project,
                    workspace=project.workspace,
                    state=state,
                    sequence_id=n,
                    created_by=author,
                )
                for n in range(start, start + count)
            ]
        )

    @pytest.mark.parametrize("url", [PROJECT_EXPORT, WORKSPACE_EXPORT, PROFILE_EXPORT])
    def test_more_rows_than_the_cap_is_refused_not_cut(self, monkeypatch, workspace, owner, project, url):
        monkeypatch.setattr(ekspor_tugas, "BATAS_EKSPOR", 3)
        target = url.format(slug=workspace.slug, project=project.id, user=owner.id)
        self._bulk(project, owner, 3)
        assert len(_rows(_client(owner).get(target))) == 3

        self._bulk(project, owner, 1, start=4)
        response = _client(owner).get(target)

        assert response.status_code == 400
        assert (response.data["code"], response.data["limit"]) == ("EXPORT_TOO_LARGE", 3)
        assert "more than 3" in response.data["error"]

    def test_the_cap_is_ten_thousand(self):
        assert ekspor_tugas.BATAS_EKSPOR == 10_000

    @pytest.mark.parametrize("url", [PROJECT_EXPORT, WORKSPACE_EXPORT, PROFILE_EXPORT])
    def test_over_a_thousand_rows_with_a_fixed_number_of_queries(self, workspace, owner, project, url):
        target = url.format(slug=workspace.slug, project=project.id, user=owner.id)

        label = Label.objects.create(name="tag", project=project, workspace=workspace)
        module = Module.objects.create(name="Mod", project=project, workspace=workspace)
        estimate = Estimate.objects.create(name="Points", project=project, workspace=workspace)
        point = EstimatePoint.objects.create(estimate=estimate, key=1, value="5", project=project, workspace=workspace)

        def populate(count, start):
            """Rows that exercise every column that reads another table."""
            self._bulk(project, owner, count, start)
            new = list(Issue.objects.filter(project=project, sequence_id__gte=start).order_by("sequence_id"))
            shared = {"project": project, "workspace": workspace}
            IssueAssignee.objects.bulk_create([IssueAssignee(issue=i, assignee=owner, **shared) for i in new])
            IssueLabel.objects.bulk_create([IssueLabel(issue=i, label=label, **shared) for i in new])
            ModuleIssue.objects.bulk_create([ModuleIssue(issue=i, module=module, **shared) for i in new])
            PersetujuanPenugasan.objects.bulk_create(
                [PersetujuanPenugasan(issue=i, pemohon=owner, penerima=owner, **shared) for i in new]
            )
            Issue.objects.filter(pk__in=[i.pk for i in new]).update(
                state=_state(project, "Done"),
                completed_at=timezone.now(),
                target_date=date(2026, 1, 1),
                estimate_point=point,
            )
            Issue.objects.filter(pk__in=[i.pk for i in new[1:]]).update(parent=new[0])
            html = f"<p>hai {_mention(owner)} soal {_mention(new[0], 'issue_mention')}</p>"
            Issue.objects.filter(pk__in=[i.pk for i in new]).update(description_html=html)
            IssueComment.objects.bulk_create(
                [IssueComment(issue=i, actor=owner, comment_html=html, **shared) for i in new]
            )
            IssueActivity.objects.bulk_create(
                [
                    IssueActivity(issue=i, actor=owner, field=field, new_value="x", new_identifier=ref, **shared)
                    for i in new
                    for field, ref in (("parent", new[0].pk), ("attachment", uuid4()))
                ]
            )

        def count_queries(expected_rows):
            segarkan()  # the God Mode rule snapshot is per process: start every run cold
            reader = User.objects.get(pk=owner.pk)
            with CaptureQueriesContext(connection) as queries:
                response = _client(reader).get(target, {"order_by": "sequence_id"})
            rows = _rows(response)
            assert len(rows) == expected_rows
            return len(queries), rows

        populate(3, 1)
        count_queries(3)  # warm up whatever the process caches once
        small, _ = count_queries(3)
        populate(1002, 4)
        large, rows = count_queries(1005)

        assert [r["Key"] for r in rows] == [f"EXP-{n}" for n in range(1, 1006)]
        assert (rows[-1]["Labels"], rows[-1]["Modules"], rows[-1]["Estimate"]) == ("tag", "Mod", "5")
        assert rows[-1]["Description"] == f"hai @{owner.display_name} soal EXP-4"
        assert large == small
