# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# Django 5.2 upgrade: state only, no SQL. Django 5.1 started writing
# `through_fields` into the deconstructed form of a ManyToManyField, so the
# three M2M fields that declare it look "changed" to makemigrations even though
# nothing in the database differs. `sqlmigrate db 0173` prints only "(no-op)"
# for each operation, forwards and backwards. Upstream Plane carries the same
# change as its own 0122; we cannot reuse that number.

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("db", "0172_wiki_pencarian_isi")]

    operations = [
        migrations.AlterField(
            model_name="draftissue",
            name="assignees",
            field=models.ManyToManyField(
                blank=True,
                related_name="draft_assignee",
                through="db.DraftIssueAssignee",
                through_fields=("draft_issue", "assignee"),
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="issue",
            name="assignees",
            field=models.ManyToManyField(
                blank=True,
                related_name="assignee",
                through="db.IssueAssignee",
                through_fields=("issue", "assignee"),
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="module",
            name="members",
            field=models.ManyToManyField(
                blank=True,
                related_name="module_members",
                through="db.ModuleMember",
                through_fields=("module", "member"),
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
