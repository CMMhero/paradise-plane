# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: jenis barang di Trash
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Project, materi Wiki, dan label di Trash.

Dijalankan sinkron: penghapusan berjenjang lewat Celery tidak menunggu, jadi
`deleted_at` anak disetel langsung (lihat Jebakan & Pelajaran soal
SoftDeleteModel.delete()).
"""

import pytest
from django.utils import timezone

from plane.db.models import FileAsset, Issue, Label, Project, State, User, Workspace
from plane.utils.trash import TrashConflict, ambil, kumpulkan, pulihkan


@pytest.fixture
def workspace(db):
    pemilik = User.objects.create(email="owner@paradise.test", username="owner_paradise_test")
    return Workspace.objects.create(name="Paradise", slug="paradise", owner=pemilik)


@pytest.fixture
def project(workspace):
    return Project.objects.create(name="IT", identifier="IT", workspace=workspace)


def _buang(obj, kapan=None):
    obj.deleted_at = kapan or timezone.now()
    obj.save(update_fields=["deleted_at"])


@pytest.mark.django_db
def test_project_terhapus_hanya_di_tpa_dan_anaknya_tidak_membanjiri(project):
    state = State.objects.create(name="Todo", project=project, workspace=project.workspace)
    issue = Issue.objects.create(name="Tugas", project=project, workspace=project.workspace, state=state)
    kapan = timezone.now()
    _buang(issue, kapan)
    _buang(project, kapan)

    tpa = kumpulkan()
    assert [(i["type"], i["id"]) for i in tpa] == [("project", str(project.pk))]
    assert kumpulkan(project_id=project.pk, tipe="project") == []
    assert ambil("project", project.pk, project_id=project.pk) == (None, None)


@pytest.mark.django_db
def test_pulihkan_project_ikut_mengembalikan_anaknya(project):
    state = State.objects.create(name="Todo", project=project, workspace=project.workspace)
    issue = Issue.objects.create(name="Tugas", project=project, workspace=project.workspace, state=state)
    kapan = timezone.now()
    _buang(issue, kapan)
    _buang(project, kapan)

    obj, spec = ambil("project", project.pk)
    pulihkan(obj, spec)

    assert Project.objects.filter(pk=project.pk).exists()
    assert Issue.objects.filter(pk=issue.pk).exists()


@pytest.mark.django_db
def test_pulihkan_project_bentrok_identifier_ditolak_tanpa_menyentuh_anak(project, workspace):
    state = State.objects.create(name="Todo", project=project, workspace=workspace)
    issue = Issue.objects.create(name="Tugas", project=project, workspace=workspace, state=state)
    kapan = timezone.now()
    _buang(issue, kapan)
    _buang(project, kapan)
    Project.objects.create(name="IT baru", identifier="IT", workspace=workspace)

    obj, spec = ambil("project", project.pk)
    with pytest.raises(TrashConflict):
        pulihkan(obj, spec)

    assert not Issue.objects.filter(pk=issue.pk).exists(), "anak tidak boleh hidup di bawah project terhapus"


@pytest.mark.django_db
def test_lampiran_biasa_bukan_materi_wiki(project):
    lampiran = FileAsset.objects.create(
        workspace=project.workspace,
        project=project,
        entity_type=FileAsset.EntityTypeContext.ISSUE_ATTACHMENT,
        asset="a.png",
    )
    _buang(lampiran)

    assert kumpulkan(project_id=project.pk) == []


@pytest.mark.django_db
def test_pulihkan_label_bentrok_nama_ditolak(project, workspace):
    lama = Label.objects.create(name="Urgent", project=project, workspace=workspace)
    _buang(lama)
    Label.objects.create(name="Urgent", project=project, workspace=workspace)

    obj, spec = ambil("label", lama.pk, project_id=project.pk)
    with pytest.raises(TrashConflict):
        pulihkan(obj, spec)
