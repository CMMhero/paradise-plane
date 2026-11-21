# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan God Mode area D, notifikasi, ringkasan, pengingat
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Aturan area D dibaca saat task jalan. Pola tiap aturan: tanpa baris database
perilakunya persis sebelum aturannya ada, dengan baris `InstanceConfiguration`
hasil task atau penerimanya berubah.

Dunia uji dipinjam dari `test_daily_digest_peran`:

    Divisi Operasional ── Dept GDG (Proj GDG) ── staf, sup
                       └─ Dept KRM (Proj KRM) ── staf2
    Divisi HRGA        ── Dept REK (Proj REK)
    mgr -> Operasional, dir -> tanpa tempat
"""

from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest import mock

import pytest
from django.core import mail
from django.utils import timezone

from plane.bgtasks import daily_digest_task, direktur_digest_task, jadwal_kantor
from plane.bgtasks.daily_digest_email import susun_email as susun_email_harian
from plane.bgtasks.daily_digest_task import TugasWorkspace, susun_ringkasan
from plane.bgtasks.direktur_digest_task import DataWorkspace, direktur_workspace, susun_laporan
from plane.bgtasks.login_activity_retention import hitung_peringatan
from plane.bgtasks.pengumuman_email_task import kirim_email_pengumuman
from plane.db.models import (
    TINGKAT_CABANG,
    TINGKAT_LEADER,
    TINGKAT_MANAGER,
    TINGKAT_SEKRETARIS,
    TINGKAT_SUPERVISOR,
    Issue,
    JabatanOrganisasi,
    LoginActivity,
    Notification,
    User,
    UserNotificationPreference,
    WorkspaceMember,
)
from plane.license.models import InstanceConfiguration
from plane.tests.contract.app.test_daily_digest_peran import HARI_INI, Dunia, _ids, _orang, _tim
from plane.tests.contract.app.test_kabar_lebur_sebutan_app import (  # noqa: F401 (fixture org)
    SEBUT,
    _komentar,
    _saklar_hidup_semua,
    org,
)
from plane.tests.contract.app.test_obrolan_p29_app import antrean, kantor  # noqa: F401 (fixture kantor)
from plane.utils import aturan
from plane.utils.aturan import area_notifikasi as d
from plane.utils.hierarki import divisi_diawasi
from plane.utils.preferensi_email import (
    BAWAAN_DIREKTUR,
    BAWAAN_PIMPINAN,
    BAWAAN_STAF,
    dikunci,
    kelompok_jabatan,
    saklar_efektif,
)

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
UTC = dt_timezone.utc
# Rabu 4 Nov 2026 dan Sabtu 7 Nov 2026 (zona kantor bawaan Asia/Jakarta).
RABU = date(2026, 11, 4)
SABTU = date(2026, 11, 7)


def _aturan(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(key=kunci, defaults={"value": nilai, "category": "PARADISE"})


@pytest.fixture
def dunia(db):
    return Dunia()


def _jabatan(dunia, prefix, tingkat, **tempat):
    orang = _orang(dunia.ws, prefix)
    JabatanOrganisasi.objects.create(workspace=dunia.ws, member=orang, tingkat=tingkat, **tempat)
    return orang


@pytest.mark.contract
class TestBawaanTidakBerubah:
    @pytest.mark.django_db
    def test_bawaan_sama_dengan_perilaku_sebelum_aturannya_ada(self):
        assert aturan.get_choice(d.NOTIFY_GROUP_LEADER) == "staf"
        assert aturan.get_choice(d.NOTIFY_GROUP_BRANCH_DIRECTOR) == "pimpinan"
        assert aturan.get_choice(d.NOTIFY_GROUP_SECRETARY) == "direktur"
        assert aturan.get_bool(d.DIRECTOR_DEFAULTS_ARE_CEILING) is True
        assert aturan.get_list(d.DIRECTOR_REPORT_RECIPIENTS) == ("35", "40")
        assert aturan.get_int(d.DIRECTOR_REPORT_ATTENTION_UNITS) == 3
        assert aturan.get_int(d.DIGEST_TEAM_MIN_LEVEL) == TINGKAT_SUPERVISOR
        assert aturan.get_bool(d.DIGEST_TEAM_FOR_ORG_WIDE) is False
        assert aturan.get_int(d.DIGEST_PERSONAL_ROW_CAP) == 15
        assert aturan.get_int(d.DIGEST_TEAM_ROW_CAP) == 5
        assert aturan.get_list(d.DEADLINE_REMINDER_WEEKDAYS) == ("1", "2", "3", "4", "5", "6", "7")
        assert aturan.get_bool(d.ANNOUNCEMENT_EMAIL) is True
        assert aturan.get_bool(d.ANNOUNCEMENT_EMAIL_ACTIVE_ONLY) is False
        assert aturan.get_int(d.ALL_MENTION_MIN_LEVEL) == 10
        assert aturan.get_int(d.LOGIN_RETENTION_WARNING_DAYS) == 7


@pytest.mark.contract
class TestKelompokNotifikasi:
    @pytest.mark.django_db
    def test_bawaan_kelompok_per_jenjang(self, dunia):
        leader = _jabatan(dunia, "leader", TINGKAT_LEADER, departemen=dunia.dept["GDG"])
        sekre = _jabatan(dunia, "sekre", TINGKAT_SEKRETARIS)
        assert kelompok_jabatan(dunia.staf.id) == "staf"
        assert kelompok_jabatan(leader.id) == "staf"
        assert kelompok_jabatan(dunia.sup.id) == "pimpinan"
        assert kelompok_jabatan(dunia.mgr.id) == "pimpinan"
        assert kelompok_jabatan(sekre.id) == "direktur"
        assert kelompok_jabatan(dunia.dir.id) == "direktur"

    @pytest.mark.django_db
    def test_leader_bisa_ikut_kolom_pimpinan(self, dunia):
        leader = _jabatan(dunia, "leader", TINGKAT_LEADER, departemen=dunia.dept["GDG"])
        _aturan(d.NOTIFY_GROUP_LEADER, "pimpinan")
        assert kelompok_jabatan(leader.id) == "pimpinan"
        # Jenjang lain tidak ikut berubah.
        assert kelompok_jabatan(dunia.staf.id) == "staf"
        assert saklar_efektif(None, leader.id)["approval"] is False
        assert saklar_efektif(None, dunia.staf.id)["approval"] is True

    @pytest.mark.django_db
    def test_sekretaris_pindah_kolom_melepas_batas_direktur(self, dunia):
        sekre = _jabatan(dunia, "sekre", TINGKAT_SEKRETARIS)
        assert dikunci(sekre.id)  # bawaan: terkunci seperti direktur
        _aturan(d.NOTIFY_GROUP_SECRETARY, "pimpinan")
        assert kelompok_jabatan(sekre.id) == "pimpinan"
        assert dikunci(sekre.id) == []
        # Direktur sendiri tetap di kolomnya.
        assert kelompok_jabatan(dunia.dir.id) == "direktur"

    @pytest.mark.django_db
    def test_direktur_cabang_bisa_ikut_kolom_direktur(self, dunia):
        from plane.db.models import Cabang

        cabang = Cabang.objects.create(workspace=dunia.ws, kode="SBY", nama="Surabaya")
        orang = _jabatan(dunia, "cabang", TINGKAT_CABANG, cabang=cabang)
        assert kelompok_jabatan(orang.id) == "pimpinan"
        _aturan(d.NOTIFY_GROUP_BRANCH_DIRECTOR, "direktur")
        assert kelompok_jabatan(orang.id) == "direktur"
        assert dikunci(orang.id)

    @pytest.mark.django_db
    def test_batas_direktur_bawaan_menang_atas_pilihan_pribadi(self, dunia):
        UserNotificationPreference.objects.update_or_create(
            user=dunia.dir,
            workspace=None,
            project=None,
            defaults={"comment": True, "approval": True, "ikut_bawaan_jabatan": False},
        )
        efektif = saklar_efektif(UserNotificationPreference.objects.get(user=dunia.dir, workspace=None), dunia.dir.id)
        assert efektif["comment"] is False and efektif["approval"] is False

    @pytest.mark.django_db
    def test_batas_direktur_dimatikan_pilihan_pribadi_berlaku(self, dunia):
        _aturan(d.DIRECTOR_DEFAULTS_ARE_CEILING, "0")
        UserNotificationPreference.objects.update_or_create(
            user=dunia.dir,
            workspace=None,
            project=None,
            defaults={"comment": True, "ikut_bawaan_jabatan": False},
        )
        pref = UserNotificationPreference.objects.get(user=dunia.dir, workspace=None)
        assert dikunci(dunia.dir.id) == []
        efektif = saklar_efektif(pref, dunia.dir.id)
        assert efektif["comment"] is True

    @pytest.mark.django_db
    def test_batas_direktur_dimatikan_tidak_mengubah_bawaan_tanpa_pilihan(self, dunia):
        _aturan(d.DIRECTOR_DEFAULTS_ARE_CEILING, "0")
        assert saklar_efektif(None, dunia.dir.id) == BAWAAN_DIREKTUR


@pytest.mark.contract
class TestBawaanTabelKelompok:
    def test_tabel_bawaan_tidak_berubah(self):
        # Staf menerima keputusan persetujuan; pimpinan tidak; direktur hanya sebutan dan obrolan.
        assert BAWAAN_STAF["approval"] is True and BAWAAN_PIMPINAN["approval"] is False
        assert BAWAAN_DIREKTUR["mention"] is True and BAWAAN_DIREKTUR["comment"] is False


@pytest.mark.contract
class TestBagianTimRingkasan:
    def _ringkasan(self, dunia, orang):
        return susun_ringkasan(orang, dunia.ws.id, TugasWorkspace(dunia.ws.id, HARI_INI), HARI_INI)

    @pytest.mark.django_db
    def test_bawaan_supervisor_dan_manager_punya_direktur_tidak(self, dunia):
        assert self._ringkasan(dunia, dunia.sup).tim
        assert self._ringkasan(dunia, dunia.mgr).tim
        assert self._ringkasan(dunia, dunia.dir).tim == []

    @pytest.mark.django_db
    def test_ambang_manager_menghilangkan_bagian_tim_supervisor(self, dunia):
        _aturan(d.DIGEST_TEAM_MIN_LEVEL, str(TINGKAT_MANAGER))
        assert self._ringkasan(dunia, dunia.sup).tim == []
        assert self._ringkasan(dunia, dunia.mgr).tim
        # Tugas yang ia berikan tetap ada: hanya bagian tim yang hilang.
        assert _ids(self._ringkasan(dunia, dunia.sup).diberikan) == {dunia.t_staf.id}

    @pytest.mark.django_db
    def test_direktur_mendapat_bagian_tim_bila_dinyalakan(self, dunia):
        _aturan(d.DIGEST_TEAM_FOR_ORG_WIDE, "1")
        r = self._ringkasan(dunia, dunia.dir)
        assert _tim(r) == {
            "Proj GDG": {dunia.t_staf.id, dunia.t_gdg.id},
            "Proj KRM": {dunia.t_krm.id},
            "Proj REK": {dunia.t_rek.id},
        }
        # Aturan ini tidak menyentuh bagian tim yang sudah ada.
        assert _tim(self._ringkasan(dunia, dunia.mgr)).keys() == {"Proj GDG", "Proj KRM"}

    @pytest.mark.django_db
    def test_tugas_privat_tanpa_bawahan_tidak_masuk_bagian_tim_direktur(self, dunia):
        _aturan(d.DIGEST_TEAM_FOR_ORG_WIDE, "1")
        privat = dunia.tugas("GDG", -1, [])
        Issue.objects.filter(pk=privat.pk).update(is_private=True)
        r = self._ringkasan(dunia, dunia.dir)
        assert privat.id not in set().union(*_tim(r).values())

    @pytest.mark.django_db
    def test_batas_baris_pribadi(self, dunia):
        for _ in range(8):
            dunia.tugas("GDG", -1, [dunia.staf])
        sebelum = self._ringkasan(dunia, dunia.staf)
        assert sebelum.batas_baris == 15
        _, teks, _ = susun_email_harian(dunia.staf, sebelum, HARI_INI)
        assert teks.count("  GDG-") == 9 and "lainnya" not in teks

        _aturan(d.DIGEST_PERSONAL_ROW_CAP, "5")
        sesudah = self._ringkasan(dunia, dunia.staf)
        _, teks, html = susun_email_harian(dunia.staf, sesudah, HARI_INI)
        assert teks.count("  GDG-") == 5 and "+4 lainnya" in teks and "+4 lainnya" in html

    @pytest.mark.django_db
    def test_batas_baris_tim_per_project(self, dunia):
        for _ in range(3):
            dunia.tugas("GDG", -1, [dunia.staf2])
        _, teks, _ = susun_email_harian(dunia.mgr, self._ringkasan(dunia, dunia.mgr), HARI_INI)
        assert teks.count("  GDG-") == 4  # t_staf + tiga baru, di bawah batas 5

        _aturan(d.DIGEST_TEAM_ROW_CAP, "2")
        _, teks, _ = susun_email_harian(dunia.mgr, self._ringkasan(dunia, dunia.mgr), HARI_INI)
        assert teks.count("  GDG-") == 2 and "+2 lainnya" in teks

    @pytest.mark.django_db
    def test_email_harian_terkirim_memakai_aturan(self, dunia, settings):
        settings.EMAIL_BACKEND = LOCMEM
        _aturan(d.DIGEST_TEAM_MIN_LEVEL, str(TINGKAT_MANAGER))
        dunia.tugas("GDG", 0, [dunia.staf2])
        with mock.patch.object(daily_digest_task, "_koneksi", return_value=(None, "noreply@uji.id")):
            daily_digest_task.kirim_ringkasan_harian(HARI_INI.isoformat())
        surat = {m.to[0]: m for m in mail.outbox}
        assert "DEPARTEMEN ANDA" not in surat[dunia.sup.email].body.upper()
        assert "DIVISI ANDA" in surat[dunia.mgr.email].body.upper()


@pytest.mark.contract
class TestLaporanDirektur:
    @pytest.fixture(autouse=True)
    def _buatan_pimpinan(self, dunia):
        Issue.objects.filter(workspace=dunia.ws, created_by__isnull=True).update(created_by=dunia.mgr)

    @pytest.mark.django_db
    def test_bawaan_penerima_direktur_dan_sekretaris(self, dunia):
        sekre = _jabatan(dunia, "sekre", TINGKAT_SEKRETARIS)
        penerima = {u.id for u in direktur_workspace()[dunia.ws.id]}
        assert penerima == {dunia.dir.id, sekre.id}

    @pytest.mark.django_db
    def test_penerima_dari_god_mode(self, dunia):
        sekre = _jabatan(dunia, "sekre", TINGKAT_SEKRETARIS)
        _aturan(d.DIRECTOR_REPORT_RECIPIENTS, "40")
        assert {u.id for u in direktur_workspace()[dunia.ws.id]} == {dunia.dir.id}
        _aturan(d.DIRECTOR_REPORT_RECIPIENTS, "35")
        assert {u.id for u in direktur_workspace()[dunia.ws.id]} == {sekre.id}

    @pytest.mark.django_db
    def test_direktur_cabang_menerima_bagian_yang_ia_awasi_saja(self, dunia):
        from plane.db.models import Cabang

        cabang = Cabang.objects.create(workspace=dunia.ws, kode="SBY", nama="Surabaya")
        orang = _jabatan(dunia, "cabang", TINGKAT_CABANG, cabang=cabang)
        assert orang.id not in {u.id for u in direktur_workspace().get(dunia.ws.id, [])}
        _aturan(d.DIRECTOR_REPORT_RECIPIENTS, "33,35,40")
        assert orang.id in {u.id for u in direktur_workspace()[dunia.ws.id]}
        data = DataWorkspace(dunia.ws.id, HARI_INI, timezone.now() - timedelta(hours=24))
        laporan = susun_laporan(data, divisi_diawasi(orang.id, dunia.ws.id), "24 jam terakhir")
        # Cabang ini tidak membawahi divisi mana pun di dunia uji: tidak ada yang bocor dari luar jangkauannya.
        assert {x.nama for x in laporan.divisi}.isdisjoint({"Operasional", "HRGA"})

    @pytest.mark.django_db
    def test_email_terkirim_hanya_ke_penerima_pilihan(self, dunia, settings):
        settings.EMAIL_BACKEND = LOCMEM
        sekre = _jabatan(dunia, "sekre", TINGKAT_SEKRETARIS)
        _aturan(d.DIRECTOR_REPORT_RECIPIENTS, "35")
        with mock.patch.object(direktur_digest_task, "_koneksi", return_value=(None, "noreply@uji.id")):
            direktur_digest_task.kirim_ringkasan_direktur()
        assert [m.to[0] for m in mail.outbox if m.to[0].endswith("@uji.id")] == [sekre.email]

    @pytest.mark.django_db
    def test_panjang_daftar_perlu_perhatian(self, dunia):
        def laporan():
            data = DataWorkspace(dunia.ws.id, HARI_INI, timezone.now() - timedelta(hours=24))
            return susun_laporan(data, divisi_diawasi(dunia.dir.id, dunia.ws.id), "24 jam terakhir")

        # Dept GDG dan REK terlambat; KRM tidak.
        assert len(laporan().perlu_perhatian()) == 2
        _aturan(d.DIRECTOR_REPORT_ATTENTION_UNITS, "1")
        assert len(laporan().perlu_perhatian()) == 1


@pytest.mark.contract
class TestHariPengingat:
    def _utc(self, hari, jam):
        return datetime(hari.year, hari.month, hari.day, jam, 0, tzinfo=UTC)

    @pytest.mark.django_db
    def test_bawaan_tiap_hari(self):
        nama = [s.nama for s in jadwal_kantor.slot_jatuh_tempo(self._utc(SABTU, 11))[1]]
        assert nama == ["pengingat-tenggat"]

    @pytest.mark.django_db
    def test_hari_dari_god_mode(self):
        _aturan(d.DEADLINE_REMINDER_WEEKDAYS, "1,2,3,4,5")
        assert jadwal_kantor.slot_jatuh_tempo(self._utc(SABTU, 11))[1] == []
        assert "pengingat-tenggat" in [s.nama for s in jadwal_kantor.slot_jatuh_tempo(self._utc(RABU, 11))[1]]

    @pytest.mark.django_db
    def test_tidak_mempengaruhi_hari_ringkasan(self):
        _aturan(d.DEADLINE_REMINDER_WEEKDAYS, "6")
        nama = [s.nama for s in jadwal_kantor.slot_jatuh_tempo(self._utc(RABU, 11))[1]]
        assert "pengingat-tenggat" not in nama and "ringkasan-pagi" in nama


@pytest.mark.contract
class TestEmailPengumuman:
    def _kirim(self, k, antrean):
        from plane.tests.contract.app.test_obrolan_p29_app import _klien, _url

        jawab = _klien(k["admin"]).post(_url(k), {"isi": "Besok libur"}, format="json")
        assert jawab.status_code == 201
        mail.outbox.clear()
        return kirim_email_pengumuman(antrean[-1])

    @pytest.mark.django_db
    def test_bawaan_semua_menerima(self, kantor, antrean):
        hasil = self._kirim(kantor, antrean)
        assert hasil == {"terkirim": 2, "gagal": 0}  # hr dan staf; tolak mematikan sendiri, admin penulis

    @pytest.mark.django_db
    def test_dimatikan_tidak_ada_email(self, kantor, antrean):
        _aturan(d.ANNOUNCEMENT_EMAIL, "0")
        assert self._kirim(kantor, antrean) == {"terkirim": 0, "gagal": 0}
        assert mail.outbox == []

    @pytest.mark.django_db
    def test_hanya_yang_baru_aktif(self, kantor, antrean):
        _aturan(d.ANNOUNCEMENT_EMAIL_ACTIVE_ONLY, "1")
        lama = timezone.now() - timedelta(days=400)
        User.objects.filter(pk=kantor["hr"].pk).update(last_active=lama, last_login_time=lama)
        hasil = self._kirim(kantor, antrean)
        assert hasil == {"terkirim": 1, "gagal": 0}
        assert [m.to[0] for m in mail.outbox] == [kantor["staf"].email]


@pytest.mark.contract
class TestSebutSemua:
    def _semua(self):
        return (
            '<p><mention-component id="x" entity_name="everyone_mention" '
            'entity_identifier="all"></mention-component></p>'
        )

    def _penerima(self, org):
        return set(
            Notification.objects.filter(entity_identifier=org.issue.id, sender=SEBUT).values_list(
                "receiver_id", flat=True
            )
        )

    @pytest.mark.django_db
    def test_bawaan_siapa_pun_boleh(self, org):
        _komentar(org, org.bob, self._semua())
        assert org.alice.id in self._penerima(org)

    @pytest.mark.django_db
    def test_di_bawah_ambang_tidak_ada_yang_dikabari(self, org):
        _aturan(d.ALL_MENTION_MIN_LEVEL, str(TINGKAT_SEKRETARIS))
        _komentar(org, org.bob, self._semua())
        assert self._penerima(org) == set()

    @pytest.mark.django_db
    def test_di_atas_ambang_dikabari(self, org):
        _aturan(d.ALL_MENTION_MIN_LEVEL, str(TINGKAT_SEKRETARIS))
        JabatanOrganisasi.objects.create(workspace=org.ws, member=org.bob, tingkat=TINGKAT_SEKRETARIS)
        _komentar(org, org.bob, self._semua())
        assert org.alice.id in self._penerima(org)

    @pytest.mark.django_db
    def test_sebutan_bernama_tidak_terkena_ambang(self, org):
        _aturan(d.ALL_MENTION_MIN_LEVEL, str(TINGKAT_SEKRETARIS))
        html = (
            f'<p><mention-component id="x" entity_name="user_mention" entity_identifier="{org.cici.id}">'
            "</mention-component></p>"
        )
        _komentar(org, org.bob, html)
        assert org.cici.id in self._penerima(org)


@pytest.mark.contract
class TestPeringatanRetensiLogin:
    @pytest.mark.django_db
    def test_bawaan_tujuh_hari_dan_ubahan(self):
        assert hitung_peringatan()["ambang_peringatan_hari"] == 7
        _aturan(d.LOGIN_RETENTION_WARNING_DAYS, "14")
        assert hitung_peringatan()["ambang_peringatan_hari"] == 14

    @pytest.mark.django_db
    def test_ambang_lebih_lebar_menjaring_catatan_lebih_awal(self, db):
        from plane.db.models import RETENSI_HARI

        user = User.objects.create(email="log@uji.id", username="log_uji")
        entri = LoginActivity.objects.create(
            user=user, jenis="LOGIN", terjadi_pada=timezone.now() - timedelta(days=RETENSI_HARI - 10)
        )
        assert entri.pk and hitung_peringatan()["akan_dibuang"] == 0
        _aturan(d.LOGIN_RETENTION_WARNING_DAYS, "14")
        assert hitung_peringatan()["akan_dibuang"] == 1
