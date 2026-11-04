# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: jadwal kantor (KEP-83)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Penjadwal kantor: zona waktu, hari kirim, sekali per tanggal, dan perubahan jam di hari yang sama.

Juga: titik pengingat dibaca dari God Mode, jendela laporan direktur mengikuti
DIGEST_WEEKDAYS, dan entri beat basi (BUG-12) dibuang tanpa menyentuh entri lain.
"""

from datetime import date, datetime, timedelta, timezone as dt_timezone
from unittest import mock

import pytest
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from plane.bgtasks import daily_digest_email, deadline_reminder_task, direktur_digest_task, jadwal_kantor
from plane.db.models import JadwalTerlaksana
from plane.license.models import InstanceConfiguration
from plane.utils import penjadwal_beat
from plane.utils import setelan_instance as st

UTC = dt_timezone.utc
# Rabu 4 Nov 2026 dan Sabtu 7 Nov 2026.
RABU = date(2026, 11, 4)
SABTU = date(2026, 11, 7)


def _simpan(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(key=kunci, defaults={"value": nilai, "category": "PARADISE"})


def _utc(hari, jam, menit=0):
    return datetime(hari.year, hari.month, hari.day, jam, menit, tzinfo=UTC)


def _nama(slots):
    return [s.nama for s in slots]


@pytest.fixture
def terpasang(db):
    """Penjadwal sudah pernah jalan kemarin (tidak lagi ada perlakuan detak pertama)."""
    JadwalTerlaksana.objects.create(slot="ringkasan-pagi", tanggal=RABU - timedelta(days=1))


@pytest.fixture
def antrean():
    with mock.patch.object(jadwal_kantor.jalankan_slot, "delay") as delay:
        yield delay


def _detak(waktu):
    return jadwal_kantor.jalankan_jadwal_kantor(sekarang=waktu.isoformat())


@pytest.mark.unit
class TestJatuhTempo:
    @pytest.mark.django_db
    def test_bawaan_sama_dengan_crontab_lama(self):
        # 00:59 UTC = 07:59 WIB: belum ada apa-apa.
        assert _nama(jadwal_kantor.slot_jatuh_tempo(_utc(RABU, 0, 59))[1]) == []
        # 01:00 UTC = 08:00 WIB: pengingat (crontab lama 01:00 UTC).
        tanggal, slots = jadwal_kantor.slot_jatuh_tempo(_utc(RABU, 1, 0))
        assert tanggal == RABU and _nama(slots) == ["pengingat-tenggat"]
        # 01:30 UTC = 08:30 WIB: ringkasan pagi + direktur.
        assert _nama(jadwal_kantor.slot_jatuh_tempo(_utc(RABU, 1, 30))[1]) == [
            "pengingat-tenggat",
            "ringkasan-pagi",
            "ringkasan-direktur",
        ]
        # 10:30 UTC = 17:30 WIB: sore.
        assert "ringkasan-sore" in _nama(jadwal_kantor.slot_jatuh_tempo(_utc(RABU, 10, 30))[1])

    @pytest.mark.django_db
    def test_tanggal_kantor_bukan_tanggal_utc(self):
        # 17:30 UTC Selasa = 00:30 WIB Rabu.
        tanggal, slots = jadwal_kantor.slot_jatuh_tempo(_utc(RABU - timedelta(days=1), 17, 30))
        assert tanggal == RABU and slots == []

    @pytest.mark.django_db
    def test_zona_kantor_lain(self):
        _simpan(st.OFFICE_TIMEZONE, "Asia/Makassar")  # UTC+8
        # 00:00 UTC = 08:00 WITA: pengingat jatuh tempo satu jam lebih awal dari WIB.
        assert _nama(jadwal_kantor.slot_jatuh_tempo(_utc(RABU, 0, 0))[1]) == ["pengingat-tenggat"]

    @pytest.mark.django_db
    def test_akhir_pekan_hanya_pengingat(self):
        assert _nama(jadwal_kantor.slot_jatuh_tempo(_utc(SABTU, 11, 0))[1]) == ["pengingat-tenggat"]

    @pytest.mark.django_db
    def test_hari_kirim_dari_god_mode(self):
        _simpan(st.DIGEST_WEEKDAYS, "6")  # Sabtu saja
        assert "ringkasan-pagi" in _nama(jadwal_kantor.slot_jatuh_tempo(_utc(SABTU, 2, 0))[1])
        assert "ringkasan-pagi" not in _nama(jadwal_kantor.slot_jatuh_tempo(_utc(RABU, 2, 0))[1])
        # Pengingat tenggat tidak ikut DIGEST_WEEKDAYS.
        assert "pengingat-tenggat" in _nama(jadwal_kantor.slot_jatuh_tempo(_utc(RABU, 2, 0))[1])


@pytest.mark.unit
class TestSekaliSehari:
    def test_detak_ganda_hanya_sekali(self, terpasang, antrean):
        assert _detak(_utc(RABU, 1, 0))["diantrekan"] == ["pengingat-tenggat"]
        assert _detak(_utc(RABU, 1, 5))["diantrekan"] == []
        assert _detak(_utc(RABU, 1, 0))["diantrekan"] == []
        assert antrean.call_count == 1
        assert JadwalTerlaksana.objects.filter(slot="pengingat-tenggat", tanggal=RABU).count() == 1

    def test_hari_berikutnya_jalan_lagi(self, terpasang, antrean):
        _detak(_utc(RABU, 1, 0))
        assert _detak(_utc(RABU + timedelta(days=1), 1, 0))["diantrekan"] == ["pengingat-tenggat"]

    def test_klaim_kedua_ditolak_kunci_unik(self, db):
        assert jadwal_kantor.klaim("ringkasan-pagi", RABU) is not None
        assert jadwal_kantor.klaim("ringkasan-pagi", RABU) is None

    def test_broker_gagal_melepas_klaim(self, terpasang):
        with mock.patch.object(jadwal_kantor.jalankan_slot, "delay", side_effect=OSError("broker mati")):
            assert _detak(_utc(RABU, 1, 0))["diantrekan"] == []
        assert not JadwalTerlaksana.objects.filter(slot="pengingat-tenggat").exists()

    def test_detak_pertama_tanpa_bukti_crontab_lama_menyusulkan(self, db, antrean):
        # Tabel penanda kosong dan tidak ada penanda dari crontab lama: tidak ada
        # bukti yang sudah terkirim, jadi semua slot yang lewat dikirim.
        assert _detak(_utc(RABU, 2, 0))["diantrekan"] == ["pengingat-tenggat", "ringkasan-pagi", "ringkasan-direktur"]

    def test_penanda_crontab_lama_melewati_ringkasan_saja(self, db, antrean):
        # Deploy 09:00 WIB; crontab lama sudah mengirim pagi + direktur.
        jadwal_kantor.tandai_sudah_dikirim(RABU, ["ringkasan-pagi", "ringkasan-direktur"], "uji")
        # Pengingat tenggat tetap jalan: task-nya mencatat per penerima.
        assert _detak(_utc(RABU, 2, 0))["diantrekan"] == ["pengingat-tenggat"]
        assert _detak(_utc(RABU, 10, 30))["diantrekan"] == ["ringkasan-sore"]

    def test_tandai_mengabaikan_slot_asing_dan_yang_sudah_ada(self, db):
        jadwal_kantor.klaim("ringkasan-pagi", RABU)
        assert jadwal_kantor.tandai_sudah_dikirim(RABU, ["ringkasan-pagi", "bukan-slot"], "uji") == ["ringkasan-pagi"]
        penanda = JadwalTerlaksana.objects.get(slot="ringkasan-pagi", tanggal=RABU)
        # Klaim yang sudah ada tidak ditimpa.
        assert penanda.selesai_at is None and penanda.hasil == {}
        assert not JadwalTerlaksana.objects.filter(slot="bukan-slot").exists()


@pytest.mark.unit
class TestGantiJamHariItu:
    def test_dimundurkan_sesudah_jalan_tidak_dikirim_ulang(self, terpasang, antrean):
        _detak(_utc(RABU, 1, 30))  # 08:30 WIB, pagi jalan
        _simpan(st.DIGEST_MORNING_TIME, "07:00")
        assert "ringkasan-pagi" not in _detak(_utc(RABU, 2, 0))["diantrekan"]

    def test_dimajukan_sebelum_jalan_menunggu_jam_baru(self, terpasang, antrean):
        _simpan(st.DIGEST_MORNING_TIME, "10:00")
        assert "ringkasan-pagi" not in _detak(_utc(RABU, 1, 30))["diantrekan"]
        assert "ringkasan-pagi" not in _detak(_utc(RABU, 2, 55))["diantrekan"]
        assert "ringkasan-pagi" in _detak(_utc(RABU, 3, 0))["diantrekan"]

    def test_dimundurkan_ke_sebelum_sekarang_disusulkan(self, terpasang, antrean):
        _simpan(st.DIGEST_MORNING_TIME, "10:00")
        _detak(_utc(RABU, 1, 30))
        _simpan(st.DIGEST_MORNING_TIME, "08:00")
        assert "ringkasan-pagi" in _detak(_utc(RABU, 1, 35))["diantrekan"]


@pytest.mark.unit
class TestJalankanSlot:
    def test_mencatat_hasil_dan_meneruskan_tanggal(self, db):
        penanda = jadwal_kantor.klaim("pengingat-tenggat", RABU)
        with mock.patch.object(
            deadline_reminder_task, "kirim_pengingat_tenggat", return_value={"terkirim": 3}
        ) as task, mock.patch.object(jadwal_kantor, "symbol_by_name", return_value=task):
            jadwal_kantor.jalankan_slot(penanda.id)
        task.assert_called_once_with(tanggal="2026-11-04")
        penanda.refresh_from_db()
        assert penanda.hasil == {"terkirim": 3} and penanda.selesai_at is not None

    def test_galat_tercatat_dan_tidak_diulang(self, db):
        penanda = jadwal_kantor.klaim("ringkasan-pagi", RABU)
        gagal = mock.Mock(side_effect=RuntimeError("smtp"))
        with mock.patch.object(jadwal_kantor, "symbol_by_name", return_value=gagal):
            jadwal_kantor.jalankan_slot(penanda.id)
            jadwal_kantor.jalankan_slot(penanda.id)
        assert gagal.call_count == 1
        penanda.refresh_from_db()
        assert "RuntimeError" in penanda.hasil["galat"]

    def test_pesan_ganda_hanya_menjalankan_sekali(self, db):
        # Broker mengirim ulang pesan: klaim selesai_at bersyarat menolak yang kedua.
        penanda = jadwal_kantor.klaim("ringkasan-pagi", RABU)
        task = mock.Mock(return_value={"terkirim": 1})
        with mock.patch.object(jadwal_kantor, "symbol_by_name", return_value=task):
            assert jadwal_kantor.jalankan_slot(penanda.id) == {"terkirim": 1}
            assert jadwal_kantor.jalankan_slot(penanda.id) is None
        assert task.call_count == 1

    def test_klaim_sedang_jalan_tidak_dijalankan_lagi(self, db):
        # Pesan kedua tiba saat yang pertama masih berjalan (selesai_at sudah diisi klaim).
        penanda = jadwal_kantor.klaim("ringkasan-pagi", RABU)
        task = mock.Mock(return_value={})

        def kedua(**_):
            assert jadwal_kantor.jalankan_slot(penanda.id) is None
            return {"terkirim": 2}

        task.side_effect = kedua
        with mock.patch.object(jadwal_kantor, "symbol_by_name", return_value=task):
            jadwal_kantor.jalankan_slot(penanda.id)
        assert task.call_count == 1
        penanda.refresh_from_db()
        assert penanda.hasil == {"terkirim": 2}

    def test_semua_slot_menunjuk_task_terdaftar(self):
        from plane.celery import app

        app.loader.import_default_modules()
        assert {s.task for s in jadwal_kantor.SLOT} <= set(app.tasks)


@pytest.mark.unit
class TestTitikDanJendela:
    @pytest.mark.django_db
    def test_titik_pengingat_bawaan(self):
        assert deadline_reminder_task.titik_email() == (-7, -5, -3, -1, 0, 3, 5, 7)
        assert deadline_reminder_task.titik_inbox() == (-1, 0, 1, 3, 7)

    @pytest.mark.django_db
    def test_titik_pengingat_dari_god_mode(self):
        _simpan(st.DEADLINE_REMINDER_EMAIL_DAYS, "-30,-2,0,30")
        _simpan(st.DEADLINE_REMINDER_INBOX_DAYS, "2")
        assert deadline_reminder_task.titik_email() == (-30, -2, 0, 30)
        assert deadline_reminder_task.titik_inbox() == (2,)

    @pytest.mark.django_db
    def test_task_memakai_titik_dari_god_mode(self):
        _simpan(st.DEADLINE_REMINDER_EMAIL_DAYS, "-2")
        tanggal_dicari = []
        asli = deadline_reminder_task.Issue.issue_objects.filter

        def catat(**kw):
            if "target_date" in kw:
                tanggal_dicari.append(kw["target_date"])
            return asli(**kw)

        with (
            mock.patch.object(deadline_reminder_task, "_aktif", return_value=True),
            mock.patch.object(deadline_reminder_task, "tulis_inbox_tenggat", return_value=0),
            # KEP-84: baris penyetuju memakai titik inbox sesudah tenggat; di luar tes ini.
            mock.patch.object(deadline_reminder_task, "tulis_inbox_penyetuju", return_value=0),
            mock.patch.object(deadline_reminder_task.Issue.issue_objects, "filter", side_effect=catat),
        ):
            deadline_reminder_task.kirim_pengingat_tenggat(tanggal=RABU.isoformat())
        assert tanggal_dicari == [RABU + timedelta(days=2)]

    def test_hari_kerja_berikutnya(self):
        senin = date(2026, 11, 2)
        assert [daily_digest_email.hari_ke_hari_kerja_berikutnya(senin + timedelta(days=i)) for i in range(7)] == [
            1, 1, 1, 1, 3, 2, 1,
        ]
        # Senin-Sabtu: Jumat ke Sabtu tinggal 1.
        enam = frozenset(range(1, 7))
        assert daily_digest_email.hari_ke_hari_kerja_berikutnya(senin + timedelta(days=4), enam) == 1

    def test_jendela_direktur(self):
        senin = date(2026, 11, 2)
        assert direktur_digest_task.jendela_hari(senin) == 3
        assert direktur_digest_task.jendela_jam(senin) == 72
        assert direktur_digest_task.jendela_hari(senin + timedelta(days=1)) == 1
        assert direktur_digest_task.label_jendela(senin, 3) == "Jumat s.d. Minggu"
        assert direktur_digest_task.label_jendela(senin, 1) == "24 jam terakhir"
        # Senin, Rabu, Jumat: Rabu mundur 2 hari.
        assert direktur_digest_task.jendela_hari(senin + timedelta(days=2), frozenset({1, 3, 5})) == 2
        assert direktur_digest_task.label_jendela(senin + timedelta(days=2), 2) == "2 hari terakhir"

    def test_durasi_hari(self):
        assert daily_digest_email.durasi_hari(7) == "7 hari"
        assert daily_digest_email.durasi_hari(7, "en") == "7 days"
        assert daily_digest_email.durasi_hari(1, "en") == "1 day"


@pytest.mark.unit
class TestEntriBeatBasi:
    def test_entri_basi_murni(self):
        baris = [
            ("jadwal-kantor", "plane.bgtasks.jadwal_kantor.jalankan_jadwal_kantor"),
            ("ringkasan-harian", "plane.bgtasks.daily_digest_task.kirim_ringkasan_harian"),
            ("create-recurring-issues", "plane.bgtasks.recurring.create"),
            ("buatan-admin", "plane.bgtasks.cleanup_task.delete_api_logs"),
            ("task-hilang", "plane.tidak.ada"),
            ("celery.backend_cleanup", "celery.backend_cleanup"),
        ]
        kode = {"jadwal-kantor"}
        terdaftar = {
            "plane.bgtasks.jadwal_kantor.jalankan_jadwal_kantor",
            "plane.bgtasks.daily_digest_task.kirim_ringkasan_harian",
            "plane.bgtasks.cleanup_task.delete_api_logs",
        }
        assert penjadwal_beat.entri_basi(baris, kode, terdaftar) == [
            "create-recurring-issues",
            "ringkasan-harian",
            "task-hilang",
        ]
        # Registry gagal dimuat: hanya nama pensiun yang dibuang.
        assert penjadwal_beat.entri_basi(baris, kode, None) == ["create-recurring-issues", "ringkasan-harian"]

    def test_entri_kode_tidak_pernah_dibuang_walau_namanya_pensiun(self):
        baris = [("ringkasan-harian", "x")]
        assert penjadwal_beat.entri_basi(baris, {"ringkasan-harian"}, set()) == []

    @pytest.mark.django_db
    def test_bersihkan_di_database(self):
        from plane.celery import app

        cron = CrontabSchedule.objects.create(minute="30", hour="1")
        for nama, task in (
            ("ringkasan-harian", "plane.bgtasks.daily_digest_task.kirim_ringkasan_harian"),
            ("create-recurring-issues", "plane.bgtasks.recurring_issue_task.create_recurring_issues"),
            ("buatan-admin", "plane.bgtasks.cleanup_task.delete_api_logs"),
            ("jadwal-kantor", "plane.bgtasks.jadwal_kantor.jalankan_jadwal_kantor"),
        ):
            PeriodicTask.objects.create(name=nama, task=task, crontab=cron)

        dibuang = penjadwal_beat.bersihkan_jadwal_basi(app)

        assert dibuang == ["create-recurring-issues", "ringkasan-harian"]
        assert set(PeriodicTask.objects.values_list("name", flat=True)) == {"buatan-admin", "jadwal-kantor"}

    def test_slot_sudah_jalan_hari_ini_murni(self):
        from zoneinfo import ZoneInfo

        wib = ZoneInfo("Asia/Jakarta")
        jalan = {
            "ringkasan-harian": _utc(RABU, 1, 30),  # 08:30 WIB hari ini
            "ringkasan-sore": _utc(RABU - timedelta(days=1), 10, 30),  # kemarin
            "ringkasan-direktur": None,  # belum pernah jalan
            "pengingat-tenggat": _utc(RABU, 1, 0),  # tidak pernah dilewati
        }
        assert penjadwal_beat.slot_sudah_jalan_hari_ini(jalan, RABU, wib) == ["ringkasan-pagi"]
        # 18:00 UTC Selasa = 01:00 WIB Rabu: tanggal kantor, bukan UTC.
        assert penjadwal_beat.slot_sudah_jalan_hari_ini(
            {"ringkasan-sore": _utc(RABU - timedelta(days=1), 18, 0)}, RABU, wib
        ) == ["ringkasan-sore"]

    @pytest.mark.django_db
    def test_bersihkan_menandai_ringkasan_yang_sudah_jalan_hari_ini(self, antrean):
        from plane.celery import app

        cron = CrontabSchedule.objects.create(minute="30", hour="1")
        for nama, task, terakhir in (
            ("ringkasan-harian", "plane.bgtasks.daily_digest_task.kirim_ringkasan_harian", _utc(RABU, 1, 30)),
            ("ringkasan-direktur", "plane.bgtasks.direktur_digest_task.kirim_ringkasan_direktur", None),
            ("ringkasan-sore", "plane.bgtasks.daily_digest_task.kirim_ringkasan_sore", _utc(RABU, 10, 30) - timedelta(days=1)),
            ("pengingat-tenggat", "plane.bgtasks.deadline_reminder_task.kirim_pengingat_tenggat", _utc(RABU, 1, 0)),
        ):
            PeriodicTask.objects.create(name=nama, task=task, crontab=cron, last_run_at=terakhir)

        with mock.patch.object(penjadwal_beat.timezone, "now", return_value=_utc(RABU, 2, 0)):
            dibuang = penjadwal_beat.bersihkan_jadwal_basi(app)

        assert set(dibuang) == {"ringkasan-harian", "ringkasan-direktur", "ringkasan-sore", "pengingat-tenggat"}
        penanda = JadwalTerlaksana.objects.get(tanggal=RABU)
        assert penanda.slot == "ringkasan-pagi" and penanda.selesai_at is not None
        # Detak 09:00 WIB: pagi dilewati, direktur (crontab lama belum jalan) dan pengingat dikirim.
        assert _detak(_utc(RABU, 2, 0))["diantrekan"] == ["pengingat-tenggat", "ringkasan-direktur"]
