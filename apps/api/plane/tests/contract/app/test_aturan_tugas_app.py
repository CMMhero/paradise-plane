# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan God Mode area B (menugaskan, mengubah, menyetujui)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# ruff: noqa: F811  (fixture `org`/`p29` diimpor lalu dipakai sebagai parameter, pola pytest)

"""Setiap aturan di `plane/utils/aturan/area_tugas.py` dua kali: tanpa baris
database perilakunya sama dengan sebelum aturan itu ada, dan nilai lain yang
ditulis ke `InstanceConfiguration` mengubah jawaban API.

Bentuk uji = fixture `p29` (test_jenjang_p29_app):

    SMT1 (P1): leader, sup1, staf, staf2, admin_staf (admin ws berjenjang Staf)
    SMT2 (P2): sup2, staf_lain (juga anggota eksplisit P1)
    Sales: manager · direktur · admin_ws · sa (Super Admin)
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status

from plane.db.models import Issue, IssueAssignee, PersetujuanPenugasan
from plane.license.models import InstanceConfiguration
from plane.tests.contract.app.test_jenjang_bawaan_staf_app import URL_BOLEH
from plane.tests.contract.app.test_jenjang_p29_app import (  # noqa: F401
    URL_KOMENTAR,
    _buat,
    _kuasa,
    _patch,
    _selesai,
    _tugas,
    _url,
    p29,
)
from plane.tests.contract.app.test_persetujuan_manager_app import (  # noqa: F401
    URL_ISSUE_DETAIL,
    URL_PERSETUJUAN,
    _ajukan,
    _klien,
    org,
)
from plane.utils import aturan
from plane.utils.aturan import area_tugas as B
from plane.utils.aturan.jenis import ke_teks
from plane.utils.atasan import PESAN_ATASAN
from plane.utils.hierarki import FLAG_GERBANG, direktur_ikut_memutuskan
from plane.utils.ketepatan_waktu import anotasi_ketepatan, dibuat_dihitung, q_terlambat
from plane.utils.naik_assignee import naikkan_assignee
from plane.utils.task_access import bisa_ganti_tenggat_intake


def _atur(kunci, nilai):
    rule = aturan.REGISTRI[kunci]
    InstanceConfiguration.objects.update_or_create(
        key=kunci, defaults={"value": ke_teks(rule, nilai), "category": "PARADISE"}
    )


def _assignees(issue_id):
    return set(IssueAssignee.objects.filter(issue_id=issue_id).values_list("assignee_id", flat=True))


pytestmark = [pytest.mark.contract, pytest.mark.django_db]


class TestPenugasan:
    def test_staf_mengajak_rekan_bawaan_lalu_hanya_diri_sendiri(self, p29):
        """B3 STAFF_ASSIGN_RULE."""
        assert _kuasa(p29.staf, p29)["mode"] == "rekan"
        assert _buat(_klien(p29.staf), p29, [p29.staf, p29.staf2]).status_code == status.HTTP_201_CREATED

        _atur(B.STAFF_ASSIGN_RULE, B.STAF_DIRI_SAJA)
        assert _kuasa(p29.staf, p29)["mode"] == "diri-sendiri"
        respon = _buat(_klien(p29.staf), p29, [p29.staf, p29.staf2])
        assert respon.status_code == status.HTTP_400_BAD_REQUEST
        assert _buat(_klien(p29.staf), p29, [p29.staf]).status_code == status.HTTP_201_CREATED

    def test_menugaskan_atasan_ditolak_bawaan_lalu_dibuka(self, p29):
        """B5 BLOCK_ASSIGN_UPWARD: admin berjenjang Staf menugaskan Supervisor di P2."""
        respon = _buat(_klien(p29.admin_staf), p29, [p29.sup2], project=p29.p2)
        assert respon.status_code == status.HTTP_400_BAD_REQUEST
        assert PESAN_ATASAN in str(respon.data["assignee_ids"])

        _atur(B.BLOCK_ASSIGN_UPWARD, False)
        respon = _buat(_klien(p29.admin_staf), p29, [p29.sup2], project=p29.p2)
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)

    def test_assignee_harus_ditempatkan_bawaan_lalu_dilepas(self, p29):
        """B6 ASSIGNEE_MUST_BE_PLACED: staf_lain (SMT2) anggota P1 tanpa penempatan di sana."""
        respon = _buat(_klien(p29.sup1), p29, [p29.staf_lain])
        assert respon.status_code == status.HTTP_400_BAD_REQUEST
        assert str(p29.staf_lain.id) not in {u["id"] for u in _kuasa(p29.sup1, p29)["users"]}

        _atur(B.ASSIGNEE_MUST_BE_PLACED, False)
        assert str(p29.staf_lain.id) in {u["id"] for u in _kuasa(p29.sup1, p29)["users"]}
        respon = _buat(_klien(p29.sup1), p29, [p29.staf_lain])
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert _assignees(respon.json()["id"]) == {p29.staf_lain.id}

    def test_pembuat_jadi_assignee_bawaan_lalu_tidak(self, p29):
        """B7 AUTO_ASSIGN_CREATOR."""
        respon = _buat(_klien(p29.staf), p29, [])
        assert _assignees(respon.json()["id"]) == {p29.staf.id}

        _atur(B.AUTO_ASSIGN_CREATOR, False)
        respon = _buat(_klien(p29.staf), p29, [])
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert _assignees(respon.json()["id"]) == set()

    def test_assignee_sub_item_naik_bawaan_lalu_berhenti(self, p29):
        """B8 BUBBLE_SUBITEM_ASSIGNEES."""
        induk = _tugas(p29, p29.sup1, [p29.sup1], nama="Induk")
        anak = _tugas(p29, p29.sup1, [p29.staf], nama="Anak")
        Issue.objects.filter(pk=anak.pk).update(parent=induk)
        assert naikkan_assignee(anak.id, p29.sup1)[0] == 1
        assert _assignees(induk.id) == {p29.sup1.id, p29.staf.id}

        induk2 = _tugas(p29, p29.sup1, [p29.sup1], nama="Induk 2")
        anak2 = _tugas(p29, p29.sup1, [p29.staf2], nama="Anak 2")
        Issue.objects.filter(pk=anak2.pk).update(parent=induk2)
        _atur(B.BUBBLE_SUBITEM_ASSIGNEES, False)
        assert naikkan_assignee(anak2.id, p29.sup1) == (0, 0)
        assert _assignees(induk2.id) == {p29.sup1.id}


class TestMengubah:
    def test_ubah_tugas_rekan_bawaan_ditolak_lalu_semua_anggota(self, p29):
        """B9 TASK_EDIT_RULE. Assignee dan hapus tetap ikut tangga jenjang."""
        tugas = _tugas(p29, p29.sup1, [p29.staf2])
        klien = _klien(p29.staf)
        assert _patch(klien, p29, tugas, {"name": "x"}).status_code == status.HTTP_403_FORBIDDEN
        assert _kuasa(p29.staf, p29)["ubah_semua_tugas"] is False

        _atur(B.TASK_EDIT_RULE, B.UBAH_SEMUA_ANGGOTA)
        assert _kuasa(p29.staf, p29)["ubah_semua_tugas"] is True
        assert _patch(klien, p29, tugas, {"name": "Diubah rekan"}).status_code == status.HTTP_200_OK
        respon = _patch(klien, p29, tugas, {"assignee_ids": [str(p29.staf.id)]})
        assert respon.status_code == status.HTTP_403_FORBIDDEN
        assert klien.delete(_url(URL_ISSUE_DETAIL, p29, tugas)).status_code == status.HTTP_403_FORBIDDEN
        tugas.refresh_from_db()
        assert tugas.name == "Diubah rekan"
        assert _assignees(tugas.id) == {p29.staf2.id}

    def test_bidang_dikunci_untuk_staf(self, p29):
        """TASK_FIELDS_LOCKED_FOR_STAFF: staf kehilangan Title, atasannya tidak."""
        milik = _tugas(p29, p29.staf, [p29.staf])
        assert _patch(_klien(p29.staf), p29, milik, {"name": "Boleh"}).status_code == status.HTTP_200_OK
        assert _kuasa(p29.staf, p29)["bidang_terkunci"] == []

        _atur(B.TASK_FIELDS_LOCKED_FOR_STAFF, ("name",))
        respon = _patch(_klien(p29.staf), p29, milik, {"name": "Ditolak"})
        assert respon.status_code == status.HTTP_403_FORBIDDEN
        assert "Title" in respon.data["error"]
        # Nilai yang tidak berubah (formulir dikirim ulang) tidak dihitung mengubah.
        respon = _patch(_klien(p29.staf), p29, milik, {"name": "Boleh", "priority": "high"})
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        assert _patch(_klien(p29.sup1), p29, milik, {"name": "Oleh atasan"}).status_code == status.HTTP_200_OK
        assert _kuasa(p29.staf, p29)["bidang_terkunci"] == ["name"]
        assert _kuasa(p29.sup1, p29)["bidang_terkunci"] == []
        milik.refresh_from_db()
        assert (milik.name, milik.priority) == ("Oleh atasan", "high")

    def test_bidang_terkunci_ikut_katup_gerbang(self, p29, monkeypatch):
        """Katup HIERARKI_GERBANG_TUGAS mati = tidak ada kunci edit, bidang juga."""
        milik = _tugas(p29, p29.staf, [p29.staf])
        _atur(B.TASK_FIELDS_LOCKED_FOR_STAFF, ("name",))
        monkeypatch.setenv(FLAG_GERBANG, "0")
        assert _kuasa(p29.staf, p29)["bidang_terkunci"] == []
        assert _patch(_klien(p29.staf), p29, milik, {"name": "Katup mati"}).status_code == status.HTTP_200_OK

    def test_bidang_dibuka_untuk_semua_anggota(self, p29):
        """TASK_FIELDS_OPEN_TO_MEMBERS: staf mengubah prioritas tugas rekan, tidak judulnya."""
        tugas = _tugas(p29, p29.sup1, [p29.staf2])
        klien = _klien(p29.staf)
        assert _patch(klien, p29, tugas, {"priority": "high"}).status_code == status.HTTP_403_FORBIDDEN
        assert _kuasa(p29.staf, p29)["bidang_terbuka"] == []

        _atur(B.TASK_FIELDS_OPEN_TO_MEMBERS, ("priority",))
        assert _kuasa(p29.staf, p29)["bidang_terbuka"] == ["priority"]
        assert _patch(klien, p29, tugas, {"priority": "high"}).status_code == status.HTTP_200_OK
        assert _patch(klien, p29, tugas, {"name": "x"}).status_code == status.HTTP_403_FORBIDDEN
        assert _patch(klien, p29, tugas, {"priority": "low", "name": "x"}).status_code == status.HTTP_403_FORBIDDEN

        # Kunci staf menang atas bidang terbuka.
        _atur(B.TASK_FIELDS_LOCKED_FOR_STAFF, ("priority",))
        assert _kuasa(p29.staf, p29)["bidang_terbuka"] == []
        assert _patch(klien, p29, tugas, {"priority": "urgent"}).status_code == status.HTTP_403_FORBIDDEN
        tugas.refresh_from_db()
        assert (tugas.name, tugas.priority) == ("Tugas", "high")

    def test_komentar_bawaan_ikut_ubah_lalu_semua_anggota(self, p29):
        """B10 TASK_COMMENT_RULE."""
        tugas = _tugas(p29, p29.sup1, [p29.staf2])
        klien = _klien(p29.staf)
        isi = {"comment_html": "<p>halo</p>"}
        assert klien.post(_url(URL_KOMENTAR, p29, tugas), isi, format="json").status_code == status.HTTP_403_FORBIDDEN

        _atur(B.TASK_COMMENT_RULE, B.KOMENTAR_SEMUA_ANGGOTA)
        assert _kuasa(p29.staf, p29)["komentar_semua_tugas"] is True
        respon = klien.post(_url(URL_KOMENTAR, p29, tugas), isi, format="json")
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert _patch(klien, p29, tugas, {"name": "x"}).status_code == status.HTTP_403_FORBIDDEN


class TestSelesai:
    def test_kunci_selesai_bawaan_lalu_mati(self, p29):
        """B11 LOCK_COMPLETED_TASKS."""
        tugas, _ = _selesai(p29)
        assert _patch(_klien(p29.admin_ws), p29, tugas, {"name": "x"}).status_code == status.HTTP_403_FORBIDDEN

        _atur(B.LOCK_COMPLETED_TASKS, False)
        assert _patch(_klien(p29.admin_ws), p29, tugas, {"name": "Admin"}).status_code == status.HTTP_200_OK
        assert _patch(_klien(p29.staf), p29, tugas, {"name": "Assignee"}).status_code == status.HTTP_200_OK
        respon = _klien(p29.staf).post(_url(URL_KOMENTAR, p29, tugas), {"comment_html": "<p>x</p>"}, format="json")
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        tugas.refresh_from_db()
        assert (tugas.name, tugas.state.group) == ("Assignee", "completed")

    def test_jenjang_buka_kembali_bawaan_supervisor_lalu_manager(self, p29):
        """B11 REOPEN_MIN_LEVEL."""
        mulai = {"state_id": str(p29.states["started"].id)}
        assert _kuasa(p29.sup1, p29)["buka_kembali"] == "bawahan"
        tugas, _ = _selesai(p29)
        assert _patch(_klien(p29.sup1), p29, tugas, mulai).status_code == status.HTTP_200_OK

        _atur(B.REOPEN_MIN_LEVEL, 30)
        assert _kuasa(p29.sup1, p29)["buka_kembali"] is None
        assert _kuasa(p29.admin_ws, p29)["buka_kembali"] == "semua"
        tugas, _ = _selesai(p29)
        assert _patch(_klien(p29.sup1), p29, tugas, mulai).status_code == status.HTTP_403_FORBIDDEN
        assert _patch(_klien(p29.manager), p29, tugas, mulai).status_code == status.HTTP_200_OK


def _putuskan(org, aktor, baris, aksi="setujui"):
    return _klien(aktor).post(
        _url(URL_PERSETUJUAN, org) + f"{baris.id}/", {"aksi": aksi, "alasan": "Belum lengkap"}, format="json"
    )


class TestPersetujuan:
    def test_direktur_bawaan_hanya_buatan_manager_lalu_semua(self, p29):
        """B13 DIRECTOR_APPROVES."""
        _, baris = _ajukan(p29)
        assert _putuskan(p29, p29.direktur, baris).status_code == status.HTTP_403_FORBIDDEN

        _atur(B.DIRECTOR_APPROVES, B.DIREKTUR_SEMUA)
        respon = _putuskan(p29, p29.direktur, baris)
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)

    def test_direktur_tidak_pernah(self, p29):
        peta = {p29.manager.id: 30}
        assert direktur_ikut_memutuskan(peta, p29.manager.id) is True
        _atur(B.DIRECTOR_APPROVES, B.DIREKTUR_TIDAK_PERNAH)
        assert direktur_ikut_memutuskan(peta, p29.manager.id) is False

    @pytest.mark.parametrize(("nilai", "grup"), [(None, "started"), ("unstarted", "unstarted")])
    def test_tujuan_tolak(self, p29, nilai, grup):
        """B16 REJECT_TARGET_STATE_GROUP."""
        if nilai:
            _atur(B.REJECT_TARGET_STATE_GROUP, nilai)
        issue_id, baris = _ajukan(p29)
        assert _putuskan(p29, p29.sup1, baris, "tolak").status_code == status.HTTP_200_OK
        assert Issue.objects.get(pk=issue_id).state.group == grup
        assert PersetujuanPenugasan.objects.get(pk=baris.pk).status == "ditolak"


class TestLainnya:
    def test_tenggat_intake_bawaan_admin_lalu_pembuat_saja(self, p29):
        """B20 INTAKE_ADMIN_SETS_DUE_DATE (penegak `bisa_ganti_tenggat_intake`, dipakai kedua view intake)."""
        tugas = _tugas(p29, p29.sup1, [p29.staf])
        assert bisa_ganti_tenggat_intake(p29.admin_ws, tugas, penanggung_jawab=True) is True
        _atur(B.INTAKE_ADMIN_SETS_DUE_DATE, False)
        assert bisa_ganti_tenggat_intake(p29.admin_ws, tugas, penanggung_jawab=True) is False
        assert bisa_ganti_tenggat_intake(p29.sup1, tugas, penanggung_jawab=True) is True

    def test_jenjang_buat_project(self, p29):
        """B21 PROJECT_CREATE_MIN_LEVEL lewat endpoint yang dibaca web."""
        url = URL_BOLEH.format(slug=p29.ws.slug)
        assert _klien(p29.sup1).get(url).data == {"boleh": True}
        assert _klien(p29.staf).get(url).data == {"boleh": False}

        _atur(B.PROJECT_CREATE_MIN_LEVEL, 30)
        assert _klien(p29.sup1).get(url).data == {"boleh": False}
        assert _klien(p29.manager).get(url).data == {"boleh": True}
        _atur(B.PROJECT_CREATE_MIN_LEVEL, 10)
        assert _klien(p29.staf).get(url).data == {"boleh": True}

    def test_terlambat_dari_hari_dicatat_bawaan_lalu_due_date_saja(self, p29):
        """G1 LATE_FROM_RECORDED_DAY: dicatat hari ini dengan Due date lampau, selesai hari ini."""
        tugas = _tugas(p29, p29.staf, [p29.staf], grup="completed")
        sekarang = timezone.now()
        Issue.objects.filter(pk=tugas.pk).update(
            created_at=sekarang, completed_at=sekarang, target_date=(sekarang - timedelta(days=5)).date()
        )

        def terlambat():
            return Issue.objects.filter(pk=tugas.pk).annotate(**anotasi_ketepatan()).filter(q_terlambat()).exists()

        assert terlambat() is False
        assert dibuat_dihitung(sekarang) == sekarang
        _atur(B.LATE_FROM_RECORDED_DAY, False)
        assert terlambat() is True
        assert dibuat_dihitung(sekarang) is None
