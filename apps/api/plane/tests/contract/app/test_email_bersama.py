# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: email bersama, To: a; b; c (2026-11-04)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Email yang isinya sama untuk beberapa orang dikirim SEKALI dengan semua alamat di To.

Keputusan user 4 Nov 2026: penerima harus bisa melihat siapa lagi yang menerima
email yang sama. Berlaku untuk penugasan (rekan setugas), pengingat tenggat (satu
tugas, satu titik), dan peringatan retensi riwayat login (semua admin).
Dipecah hanya kalau isinya memang berbeda: bahasa, atau posisi di utas.
"""

from types import SimpleNamespace
from unittest import mock

import pytest
from django.core import mail

from plane.bgtasks import penugasan_email
from plane.bgtasks.deadline_reminder_email import kirim_email_pengingat_bersama
from plane.db.models import Profile
from plane.tests.contract.app.test_daily_digest_peran import HARI_INI, Dunia
from plane.utils import email_utas
from plane.utils.email_merek import (
    MAKS_PENERIMA,
    alamat_gabungan,
    gabung_nama,
    kelompokkan_penerima,
)

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


def _u(email, bahasa="id", id_=None):
    return SimpleNamespace(id=id_ or email, email=email, bahasa=bahasa)


# ---------------------------------------------------------------- murni


@pytest.mark.unit
class TestPembantu:
    def test_satu_kelompok_per_kunci_urut_alamat(self):
        orang = [_u("c@x"), _u("a@x"), _u("b@x", "en")]
        hasil = kelompokkan_penerima(orang, lambda o: o.bahasa)
        assert [[o.email for o in g] for g in hasil] == [["a@x", "c@x"], ["b@x"]]

    def test_tanpa_alamat_dibuang(self):
        assert kelompokkan_penerima([_u(""), _u("a@x")], lambda o: 1) == [[_u("a@x")]]

    def test_dipecah_di_atas_batas(self):
        orang = [_u(f"{i:03}@x") for i in range(MAKS_PENERIMA + 1)]
        assert [len(g) for g in kelompokkan_penerima(orang, lambda o: 1)] == [MAKS_PENERIMA, 1]

    def test_gabung_nama(self):
        assert gabung_nama(["Andi"]) == "Andi"
        assert gabung_nama(["Andi", "", "Budi"]) == "Andi dan Budi"
        assert gabung_nama(["Andi", "Budi", "Citra"]) == "Andi, Budi, dan Citra"
        assert gabung_nama(["A", "B", "C"], "en") == "A, B, and C"

    def test_alamat_gabungan_seperti_header_to(self):
        assert alamat_gabungan([_u("a@x"), _u("b@x")]) == "a@x; b@x"
        assert alamat_gabungan(_u("a@x")) == "a@x"

    def test_utas_memisah_yang_sudah_menerima_akar(self):
        """Akar utas yang dikirim ulang dibuang Gmail diam-diam, jadi wajib dipisah."""
        akar = ("[K-1] T", {"Message-ID": "<issue-1@x>"})
        balas = ("Re: [K-1] T", {"Message-ID": "<u@x>", "In-Reply-To": "<issue-1@x>"})
        utas = {"a@x": akar, "b@x": balas, "c@x": akar}
        orang = [_u("a@x"), _u("b@x"), _u("c@x")]
        with mock.patch.object(email_utas, "utas_untuk", side_effect=lambda i, rid, dari="": utas[rid]):
            hasil = email_utas.utas_bersama(None, orang, lambda o: o.bahasa)
        assert [([o.email for o in g], u[0]) for g, u in hasil] == [
            (["a@x", "c@x"], "[K-1] T"),
            (["b@x"], "Re: [K-1] T"),
        ]


# ---------------------------------------------------------------- pengirim


@pytest.fixture
def dunia(db):
    return Dunia()


def _kirim_penugasan(issue, pemberi, penerima):
    with mock.patch.object(penugasan_email, "_koneksi", return_value=(None, "noreply@uji.id")):
        return penugasan_email.kirim_email_penugasan(str(issue.id), str(pemberi.id), [str(p.id) for p in penerima])


@pytest.mark.contract
class TestPenugasanBersama:
    @pytest.mark.django_db
    def test_rekan_setugas_satu_email_semua_di_to(self, dunia, settings):
        settings.EMAIL_BACKEND = LOCMEM
        issue = dunia.tugas("GDG", 3, [dunia.staf, dunia.staf2])
        hasil = _kirim_penugasan(issue, dunia.sup, [dunia.staf, dunia.staf2])

        assert hasil == {"terkirim": 2, "gagal": 0}
        (m,) = mail.outbox
        assert sorted(m.to) == sorted([dunia.staf.email, dunia.staf2.email])
        html = m.alternatives[0][0]
        assert "; ".join(sorted([dunia.staf.email, dunia.staf2.email])) in html

    @pytest.mark.django_db
    def test_bahasa_berbeda_dipecah(self, dunia, settings):
        settings.EMAIL_BACKEND = LOCMEM
        Profile.objects.filter(user=dunia.staf2).update(language="en")
        issue = dunia.tugas("GDG", 3, [dunia.staf, dunia.staf2])
        _kirim_penugasan(issue, dunia.sup, [dunia.staf, dunia.staf2])

        assert sorted(m.to[0] for m in mail.outbox) == sorted([dunia.staf.email, dunia.staf2.email])
        assert all(len(m.to) == 1 for m in mail.outbox)


@pytest.mark.contract
class TestPengingatBersama:
    @pytest.mark.django_db
    def test_satu_tugas_satu_titik_satu_email(self, dunia, settings):
        settings.EMAIL_BACKEND = LOCMEM
        issue = dunia.tugas("GDG", 3, [dunia.staf, dunia.staf2])
        hasil = kirim_email_pengingat_bersama(issue, [dunia.staf, dunia.staf2], -3)

        assert [(len(g), e) for g, e in hasil] == [(2, None)]
        (m,) = mail.outbox
        assert sorted(m.to) == sorted([dunia.staf.email, dunia.staf2.email])
        assert [a[0] for a in m.attachments] == [f"GDG-{issue.sequence_id}.ics"]

    @pytest.mark.django_db
    def test_task_mencatat_tiap_orang_dan_tidak_mengulang(self, dunia, settings):
        from plane.bgtasks import deadline_reminder_task
        from plane.db.models import PengingatTenggat

        settings.EMAIL_BACKEND = LOCMEM
        issue = dunia.tugas("GDG", 3, [dunia.staf, dunia.staf2])
        orang = {dunia.staf, dunia.staf2}
        with (
            mock.patch.object(deadline_reminder_task, "_aktif", return_value=True),
            mock.patch.object(deadline_reminder_task, "tulis_inbox_tenggat", return_value=0),
            mock.patch.object(deadline_reminder_task, "_penerima", lambda i: orang if i.id == issue.id else set()),
            mock.patch.object(deadline_reminder_task, "titik_email", return_value=(-3,)),
        ):
            # Tugas jatuh tempo HARI_INI + 3, jadi titik -3 = hari ini.
            pertama = deadline_reminder_task.kirim_pengingat_tenggat(tanggal=HARI_INI.isoformat())
            kedua = deadline_reminder_task.kirim_pengingat_tenggat(tanggal=HARI_INI.isoformat())

        assert pertama == {"terkirim": 2, "dilewati": 0, "gagal": 0}
        assert kedua == {"terkirim": 0, "dilewati": 2, "gagal": 0}
        (m,) = mail.outbox
        assert len(m.to) == 2
        assert PengingatTenggat.objects.filter(issue=issue, titik=-3).count() == 2


@pytest.mark.contract
class TestRetensiBersama:
    @pytest.mark.django_db
    def test_semua_admin_satu_email(self, dunia, settings):
        from plane.bgtasks import login_activity_retention as r
        from plane.license.models import Instance, InstanceAdmin

        settings.EMAIL_BACKEND = LOCMEM
        from django.utils import timezone

        instance = Instance.objects.first() or Instance.objects.create(
            instance_name="uji", instance_id="uji-bersama", current_version="uji", last_checked_at=timezone.now()
        )
        for u in (dunia.sup, dunia.mgr):
            InstanceAdmin.objects.create(user=u, instance=instance, role=20)
        keadaan = {"akan_dibuang": 3, "retensi_hari": 90, "ambang_peringatan_hari": 7, "tertua": None}

        with mock.patch.object(r, "get_email_configuration", return_value=("smtp.uji",) + ("",) * 6):
            assert r._kirim_email_peringatan(keadaan) == 2

        (m,) = mail.outbox
        assert sorted(m.to) == sorted([dunia.sup.email, dunia.mgr.email])

    @pytest.mark.django_db
    def test_saklar_god_mode_mematikan_email_saja(self, dunia, settings):
        """ENABLE_ADMIN_RETENTION_EMAIL mati = tidak ada email, tapi pembersihan jalan terus."""
        from django.utils import timezone

        from plane.bgtasks import login_activity_retention as r
        from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration
        from plane.utils.saklar_instance import ENABLE_ADMIN_RETENTION_EMAIL, SAKLAR_BAWAAN

        settings.EMAIL_BACKEND = LOCMEM
        settings.SKIP_ENV_VAR = True
        assert SAKLAR_BAWAAN[ENABLE_ADMIN_RETENTION_EMAIL] == "1"  # perilaku lama: hidup

        instance = Instance.objects.first() or Instance.objects.create(
            instance_name="uji", instance_id="uji-saklar", current_version="uji", last_checked_at=timezone.now()
        )
        InstanceAdmin.objects.create(user=dunia.sup, instance=instance, role=20)
        InstanceConfiguration.objects.update_or_create(key=ENABLE_ADMIN_RETENTION_EMAIL, defaults={"value": "0"})
        keadaan = {"akan_dibuang": 3, "retensi_hari": 90, "ambang_peringatan_hari": 7, "tertua": None}

        with mock.patch.object(r, "get_email_configuration", return_value=("smtp.uji",) + ("",) * 6):
            assert r._kirim_email_peringatan(keadaan) == 0
            assert mail.outbox == []

            InstanceConfiguration.objects.filter(key=ENABLE_ADMIN_RETENTION_EMAIL).update(value="1")
            assert r._kirim_email_peringatan(keadaan) == 1
