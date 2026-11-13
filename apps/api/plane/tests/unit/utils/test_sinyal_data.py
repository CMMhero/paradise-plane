# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: sinyal "data berubah" (tanpa refresh)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Sinyal "data berubah": siapa yang menerima, apa yang dikirim, dan ketahanannya.

Tiga sifat yang dijaga:
- HAK LIHAT: id project/tugas hanya diterbitkan untuk orang yang boleh melihat
  project itu (anggota aktif; tamu hanya bila project mengizinkan atau tugasnya
  buatannya sendiri). Daftar `untuk` itulah yang dipakai `apps/live` menyaring.
- ISI: tidak ada judul, nilai, atau nama di muatan, hanya id dan nama bidang.
- KETAHANAN: Redis mati tidak boleh menggagalkan penyimpanan tugas.
"""

import json
from unittest import mock
from uuid import uuid4

import pytest

from plane.bgtasks.issue_activities_task import issue_activity
from plane.db.models import Issue, Project, ProjectMember, State, User, Workspace
from plane.utils import sinyal_data
from plane.utils.sinyal_data import (
    kanal_workspace,
    penerima_project,
    siarkan_anggota_project,
    siarkan_data,
    siarkan_notifikasi_baris,
    siarkan_tugas,
)


def _orang(nama):
    unik = uuid4().hex[:8]
    return User.objects.create(
        id=uuid4(), username=f"{nama}-{unik}", email=f"{nama}-{unik}@paradise.test", display_name=nama, is_active=True
    )


@pytest.fixture
def redis_palsu():
    """Ganti koneksi Redis bersama dengan tiruan, dan kembalikan tiruannya."""
    tiruan = mock.MagicMock()
    with mock.patch.object(sinyal_data, "_redis", return_value=tiruan):
        yield tiruan


@pytest.fixture
def kantor(db):
    pemilik = _orang("pemilik")
    workspace = Workspace.objects.create(name="Kantor", slug=f"sinyal-{uuid4().hex[:8]}", owner=pemilik)
    project = Project.objects.create(name="Papan", identifier="PP", workspace=workspace, created_by=pemilik)
    return workspace, project, pemilik


def _anggota(project, orang, role, aktif=True):
    return ProjectMember.objects.create(
        project=project, workspace=project.workspace, member=orang, role=role, is_active=aktif
    )


def _tugas(project, pembuat):
    status = State.objects.create(name="Todo", project=project, group="backlog", default=True)
    return Issue.objects.create(
        name="Rahasia Direksi", workspace=project.workspace, project=project, state=status, created_by=pembuat
    )


def test_kanal_memakai_awalan_yang_sama_dengan_pelanggannya():
    """`apps/live` berlangganan pola `data:*`. Mengubah salah satu sisi tanpa yang
    lain membuat siarannya hilang tanpa error di mana pun."""
    assert kanal_workspace("kantor") == "data:kantor"


def test_siaran_membawa_penerima_terurut_dan_isi_tambahan(redis_palsu):
    siarkan_data("kantor", "tugas", ["u2", "u1", "u2", None], proyek="P1", bidang=["state"])

    kanal, muatan = redis_palsu.publish.call_args[0]
    isi = json.loads(muatan)
    assert kanal == "data:kantor"
    assert isi == {"jenis": "tugas", "untuk": ["u1", "u2"], "proyek": "P1", "bidang": ["state"]}


def test_tanpa_penerima_tidak_ada_yang_diterbitkan(redis_palsu):
    siarkan_data("kantor", "tugas", [], proyek="P1")
    siarkan_data("kantor", "tugas", None, proyek="P1")
    redis_palsu.publish.assert_not_called()


def test_galat_redis_ditelan_dan_koneksi_dibuang():
    """Real-time itu percepatan, bukan syarat: menyimpan tugas tidak boleh gagal
    karena Redis sedang ngambek, dan koneksi yang rusak tidak dipakai lagi."""
    rusak = mock.MagicMock()
    rusak.publish.side_effect = ConnectionError("redis mati")
    sinyal_data._klien = rusak
    try:
        siarkan_data("kantor", "tugas", ["u1"], proyek="P1")  # tidak melempar
        assert sinyal_data._klien is None
    finally:
        sinyal_data._klien = None


def test_penerima_hanya_anggota_aktif_project(kantor):
    _, project, pemilik = kantor
    aktif, keluar, orang_luar = _orang("aktif"), _orang("keluar"), _orang("luar")
    _anggota(project, aktif, 15)
    _anggota(project, keluar, 15, aktif=False)

    slug, penerima = penerima_project(project.id)

    ids = {str(p) for p in penerima}
    assert slug == project.workspace.slug
    assert str(aktif.id) in ids
    assert str(keluar.id) not in ids
    assert str(orang_luar.id) not in ids


def test_tamu_hanya_melihat_tugas_buatannya_sendiri(kantor):
    _, project, pemilik = kantor
    tamu_pembuat, tamu_lain = _orang("tamu-a"), _orang("tamu-b")
    _anggota(project, tamu_pembuat, 5)
    _anggota(project, tamu_lain, 5)

    _, penerima = penerima_project(project.id, pembuat_tugas_id=tamu_pembuat.id)
    ids = {str(p) for p in penerima}
    assert str(tamu_pembuat.id) in ids
    assert str(tamu_lain.id) not in ids

    # Tanpa konteks tugas (mis. anggota project berubah) tamu tidak ikut.
    _, tanpa_tugas = penerima_project(project.id)
    assert str(tamu_pembuat.id) not in {str(p) for p in tanpa_tugas}


def test_tamu_ikut_bila_project_mengizinkan_melihat_semua(kantor):
    _, project, _ = kantor
    tamu = _orang("tamu")
    _anggota(project, tamu, 5)
    Project.objects.filter(pk=project.pk).update(guest_view_all_features=True)

    _, penerima = penerima_project(project.id)
    assert str(tamu.id) in {str(p) for p in penerima}


def test_project_tak_dikenal_tidak_punya_penerima(db):
    assert penerima_project(uuid4()) == (None, [])


def test_sinyal_tugas_tidak_membawa_judul_atau_isi(kantor, redis_palsu):
    _, project, pemilik = kantor
    anggota = _orang("anggota")
    _anggota(project, anggota, 15)
    tugas = _tugas(project, pemilik)
    redis_palsu.reset_mock()

    siarkan_tugas(project.id, tugas.id, bidang=["state", None, "state", "comment"], aksi="updated", oleh_id=pemilik.id)

    kanal, muatan = redis_palsu.publish.call_args[0]
    isi = json.loads(muatan)
    assert kanal == f"data:{project.workspace.slug}"
    assert isi["jenis"] == "tugas"
    assert isi["proyek"] == str(project.id)
    assert isi["tugas"] == str(tugas.id)
    assert isi["bidang"] == ["comment", "state"]
    assert isi["aksi"] == "updated"
    assert str(anggota.id) in isi["untuk"]
    # Tidak ada judul, deskripsi, atau nama yang ikut terbawa.
    assert "Rahasia Direksi" not in muatan
    assert set(isi) == {"jenis", "untuk", "proyek", "tugas", "bidang", "aksi", "oleh"}


def test_siaran_tugas_menelan_galat_apa_pun(db):
    with mock.patch.object(sinyal_data, "penerima_project", side_effect=RuntimeError("basis data putus")):
        siarkan_tugas(uuid4(), uuid4(), bidang=["state"])  # tidak melempar


def test_notifikasi_dikelompokkan_per_workspace(kantor, redis_palsu):
    workspace, _, pemilik = kantor
    lain = _orang("lain")
    baris = [
        mock.Mock(workspace_id=workspace.id, receiver_id=pemilik.id),
        mock.Mock(workspace_id=workspace.id, receiver_id=lain.id),
        mock.Mock(workspace_id=workspace.id, receiver_id=lain.id),
    ]

    siarkan_notifikasi_baris(baris)

    assert redis_palsu.publish.call_count == 1
    kanal, muatan = redis_palsu.publish.call_args[0]
    isi = json.loads(muatan)
    assert kanal == f"data:{workspace.slug}"
    assert isi["jenis"] == "notifikasi"
    assert sorted(isi["untuk"]) == sorted([str(pemilik.id), str(lain.id)])


def test_anggota_yang_baru_dilepas_tetap_diberi_tahu(kantor, redis_palsu):
    _, project, pemilik = kantor
    dilepas = _orang("dilepas")
    _anggota(project, pemilik, 20)
    _anggota(project, dilepas, 15, aktif=False)
    redis_palsu.reset_mock()

    siarkan_anggota_project(project.id, user_ids=[dilepas.id], oleh_id=pemilik.id)

    isi = json.loads(redis_palsu.publish.call_args[0][1])
    assert isi["jenis"] == "anggota-project"
    assert str(dilepas.id) in isi["untuk"]
    assert str(pemilik.id) in isi["untuk"]


def test_menyimpan_anggota_project_menyiarkan_lewat_signal(kantor):
    _, project, _ = kantor
    baru = _orang("baru")
    with mock.patch("plane.db.sinyal_anggota.siarkan_anggota_project") as siar:
        _anggota(project, baru, 15)
    siar.assert_called_once_with(project.id, user_ids=[baru.id])


def test_aktivitas_tugas_menyiarkan_bidang_yang_berubah(kantor):
    _, project, pemilik = kantor
    tugas = _tugas(project, pemilik)

    with mock.patch("plane.bgtasks.issue_activities_task.siarkan_tugas") as siar:
        issue_activity(
            type="issue.activity.updated",
            requested_data=json.dumps({"priority": "high"}),
            current_instance=json.dumps({"priority": "low"}),
            issue_id=str(tugas.id),
            actor_id=str(pemilik.id),
            project_id=str(project.id),
            epoch=1,
        )

    siar.assert_called_once()
    args, kwargs = siar.call_args
    assert args == (str(project.id), str(tugas.id))
    assert kwargs["bidang"] == ["priority"]
    assert kwargs["aksi"] == "updated"
    assert kwargs["oleh_id"] == str(pemilik.id)


def test_menggeser_urutan_tetap_menyiarkan_walau_tanpa_baris_aktivitas(kantor):
    """Mengubah `sort_order` menggeser kartu di papan tanpa menulis aktivitas apa pun."""
    _, project, pemilik = kantor
    tugas = _tugas(project, pemilik)

    with mock.patch("plane.bgtasks.issue_activities_task.siarkan_tugas") as siar:
        issue_activity(
            type="issue.activity.updated",
            requested_data=json.dumps({"sort_order": 123.0}),
            current_instance=json.dumps({"sort_order": 1.0}),
            issue_id=str(tugas.id),
            actor_id=str(pemilik.id),
            project_id=str(project.id),
            epoch=1,
        )

    siar.assert_called_once()
    assert siar.call_args.kwargs["bidang"] == []


def test_draf_tidak_disiarkan(kantor):
    _, project, pemilik = kantor
    with mock.patch("plane.bgtasks.issue_activities_task.siarkan_tugas") as siar:
        issue_activity(
            type="issue_draft.activity.created",
            requested_data=json.dumps({"name": "draf"}),
            current_instance=None,
            issue_id=None,
            actor_id=str(pemilik.id),
            project_id=str(project.id),
            epoch=1,
        )
    siar.assert_not_called()
