# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: ringkasan harian hanya untuk yang opt-in
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone

from plane.bgtasks.daily_digest_task import _tugas_per_orang
from plane.celery import app as celery_app
from plane.db.models import Issue, IssueAssignee, Project, User, UserNotificationPreference, WorkspaceMember


def _orang(workspace, prefix):
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"{prefix}-{unik}@uji.id", username=f"{prefix}_{unik}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


@pytest.mark.contract
class TestRingkasanHarianOptIn:
    @pytest.mark.django_db
    def test_bawaan_mati_dan_hanya_yang_menyalakan_yang_dikirimi(self, workspace):
        bawaan = _orang(workspace, "bawaan")
        pilih = _orang(workspace, "pilih")
        project = Project.objects.create(name="P", identifier="PRJ", workspace=workspace)
        hari_ini = timezone.localtime(timezone.now()).date()
        for u in (bawaan, pilih):
            t = Issue.objects.create(workspace=workspace, project=project, name="T", target_date=hari_ini + timedelta(days=1))
            IssueAssignee.objects.create(issue=t, assignee=u, project=project, workspace=workspace)

        # Pengguna baru: saklar MATI.
        assert UserNotificationPreference.objects.get(user=bawaan).daily_digest is False
        UserNotificationPreference.objects.filter(user=pilih).update(daily_digest=True)

        penerima = set(_tugas_per_orang(hari_ini))
        assert pilih in penerima
        assert bawaan not in penerima

    def test_jadwal_senin_jumat_0830_jakarta(self):
        jadwal = celery_app.conf.beat_schedule["ringkasan-harian"]["schedule"]
        # Celery berjalan di UTC: 08.30 WIB = 01.30 UTC.
        assert jadwal.hour == {1} and jadwal.minute == {30}
        assert jadwal.day_of_week == {1, 2, 3, 4, 5}
