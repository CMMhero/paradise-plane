# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: siapa menerima email apa (2026-11-02)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Email penugasan (staf) dan laporan direktur (ikhtisar tanpa rincian staf).

Memakai dunia uji `test_daily_digest_peran`:

    Divisi Operasional ── Dept GDG (Proj GDG) ── staf, sup
                       └─ Dept KRM (Proj KRM) ── staf2
    Divisi HRGA        ── Dept REK (Proj REK)
    mgr -> Operasional, dir -> tanpa tempat
"""

from datetime import timedelta
from unittest import mock

import pytest
from django.core import mail
from django.utils import timezone

from plane.bgtasks import direktur_digest_task, penugasan_email
from plane.bgtasks.direktur_digest_task import DataWorkspace, susun_laporan
from plane.bgtasks.direktur_digest_email import susun_email
from plane.db.models import (
    TINGKAT_DIREKTUR,
    JabatanOrganisasi,
    PengawasanDivisi,
    UserNotificationPreference,
    WorkspaceMember,
)
from plane.tests.contract.app.test_daily_digest_peran import HARI_INI, Dunia, _orang
from plane.utils.hierarki import divisi_diawasi
from plane.utils.preferensi_email import saklar_untuk


@pytest.fixture(autouse=True)
def _utas_email_mati(monkeypatch):
    """Subjek per peran yang diuji di sini hanya ada saat utas email MATI. Sejak
    KEP-84 utas HIDUP secara bawaan (subjek jadi `[PROJ-1] Judul`), jadi dipatok mati."""
    monkeypatch.setenv("ENABLE_EMAIL_THREADING", "0")


LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture
def dunia(db):
    return Dunia()


def _kirim_penugasan(dunia, issue, pemberi, penerima):
    with mock.patch.object(penugasan_email, "_koneksi", return_value=(None, "noreply@uji.id")):
        return penugasan_email.kirim_email_penugasan(str(issue.id), str(pemberi.id), [str(p.id) for p in penerima])


@pytest.mark.contract
class TestEmailPenugasan:
    @pytest.mark.django_db
    def test_bawaan_staf_hidup_pimpinan_mati(self, dunia):
        assert saklar_untuk(dunia.staf.id)["assigned"] is True
        for pimpinan in (dunia.sup, dunia.mgr, dunia.dir):
            assert saklar_untuk(pimpinan.id)["assigned"] is False

    @pytest.mark.django_db
    def test_staf_diberi_tugas_atasan_menerima_email_dengan_ics(self, dunia, settings):
        settings.EMAIL_BACKEND = LOCMEM
        hasil = _kirim_penugasan(dunia, dunia.t_staf, dunia.sup, [dunia.staf])
        assert hasil == {"terkirim": 1, "gagal": 0}
        (m,) = mail.outbox
        assert m.to == [dunia.staf.email]
        assert m.subject.startswith("[Tugas baru] GDG-")
        html = m.alternatives[0][0]
        assert "Sup (Supervisor)" in html and "memberi Anda tugas baru" in html
        assert [a[0] for a in m.attachments] == [f"GDG-{dunia.t_staf.sequence_id}.ics"]

    @pytest.mark.django_db
    def test_penerima_berbahasa_inggris_menerima_email_inggris_berlogo(self, dunia, settings):
        from email import message_from_bytes

        from plane.db.models import Profile
        from plane.utils.email_merek import LOGO_CID

        settings.EMAIL_BACKEND = LOCMEM
        Profile.objects.filter(user=dunia.staf).update(language="en")
        _kirim_penugasan(dunia, dunia.t_staf, dunia.sup, [dunia.staf])
        (m,) = mail.outbox
        assert m.subject.startswith("[New task] GDG-")
        assert "gave you a new task" in m.alternatives[0][0] and "Anda" not in m.body
        mime = message_from_bytes(m.message().as_bytes())
        assert any(b.get("Content-ID") == f"<{LOGO_CID}>" for b in mime.walk())

    @pytest.mark.django_db
    def test_pimpinan_pemberi_sendiri_dan_nonaktif_tidak_dikirimi(self, dunia, settings):
        settings.EMAIL_BACKEND = LOCMEM
        keluar = _orang(dunia.ws, "keluar")
        WorkspaceMember.objects.filter(member=keluar).update(is_active=False)
        # sup: pimpinan (bawaan mati); mgr: pemberi tugas itu sendiri; keluar: bukan anggota aktif.
        hasil = _kirim_penugasan(dunia, dunia.t_gdg, dunia.mgr, [dunia.sup, dunia.mgr, keluar])
        assert hasil == {"terkirim": 0, "gagal": 0}
        assert mail.outbox == []

    @pytest.mark.django_db
    def test_staf_yang_mematikan_tidak_dikirimi(self, dunia, settings):
        settings.EMAIL_BACKEND = LOCMEM
        UserNotificationPreference.objects.update_or_create(
            user=dunia.staf, workspace=None, project=None, defaults={"assigned": False, "ikut_bawaan_jabatan": False}
        )
        assert _kirim_penugasan(dunia, dunia.t_staf, dunia.sup, [dunia.staf])["terkirim"] == 0

    @pytest.mark.django_db
    def test_tanpa_tenggat_tanpa_lampiran(self, dunia, settings):
        settings.EMAIL_BACKEND = LOCMEM
        issue = dunia.tugas("GDG", 0, [])
        type(issue).objects.filter(pk=issue.pk).update(target_date=None)
        _kirim_penugasan(dunia, issue, dunia.sup, [dunia.staf])
        (m,) = mail.outbox
        assert m.attachments == [] and "tenggat" not in m.subject


@pytest.mark.contract
class TestLaporanDirektur:
    def _laporan(self, dunia, direktur):
        sejak = timezone.now() - timedelta(hours=24)
        data = DataWorkspace(dunia.ws.id, HARI_INI, sejak)
        return susun_laporan(data, divisi_diawasi(direktur.id, dunia.ws.id), "24 jam terakhir")

    @pytest.mark.django_db
    def test_dikelompokkan_per_divisi_dengan_nama_pimpinan(self, dunia):
        lap = self._laporan(dunia, dunia.dir)
        divisi = {d.nama: d for d in lap.divisi}
        assert set(divisi) == {"Operasional", "HRGA"}
        ops = divisi["Operasional"]
        assert ops.pimpinan == ["Mgr"]
        unit = {u.nama: u for u in ops.unit}
        assert unit["Dept GDG"].pimpinan == ["Sup"] and unit["Dept KRM"].pimpinan == []
        # GDG: t_staf terlambat 2 hari, t_gdg 3 hari lagi; t_jauh di luar jendela, t_beres selesai.
        g = unit["Dept GDG"].angka
        assert (g.lewat, g.macet, g.hari, g.depan) == (1, 0, 0, 1)
        assert unit["Dept KRM"].angka.hari == 1
        assert divisi["HRGA"].unit[0].angka.lewat == 1

    @pytest.mark.django_db
    def test_isi_email_tanpa_nama_staf_dan_judul_tugas(self, dunia):
        lap = self._laporan(dunia, dunia.dir)
        subjek, teks, html = susun_email(dunia.dir, lap, HARI_INI)
        for bocor in ("Staf", "Staf2", dunia.t_staf.name, dunia.t_gdg.name, "GDG-"):
            assert bocor not in teks and bocor not in html, bocor
        assert "Manager Mgr" in teks and "spv Sup" in teks
        assert "Perlu perhatian" in html

    @pytest.mark.django_db
    def test_baris_pengawasan_lama_tidak_membatasi_cakupan(self, dunia):
        # KEP-93: "Supervised divisions" dibuang; baris lama tidak berpengaruh.
        sebelum = [d.nama for d in self._laporan(dunia, dunia.dir).divisi]
        PengawasanDivisi.objects.create(workspace=dunia.ws, member=dunia.dir, project=dunia.project["REK"])
        assert [d.nama for d in self._laporan(dunia, dunia.dir).divisi] == sebelum

    @pytest.mark.django_db
    def test_hanya_direktur_yang_dikirimi_sekali(self, dunia, settings):
        settings.EMAIL_BACKEND = LOCMEM
        with mock.patch.object(direktur_digest_task, "_koneksi", return_value=(None, "noreply@uji.id")):
            direktur_digest_task.kirim_ringkasan_direktur()
        ke = [m.to[0] for m in mail.outbox if m.to[0].endswith("@uji.id")]
        assert ke == [dunia.dir.email]
        assert mail.outbox[0].subject.startswith("[Laporan direktur]")

    @pytest.mark.django_db
    def test_direktur_nonaktif_tidak_dikirimi(self, dunia, settings):
        settings.EMAIL_BACKEND = LOCMEM
        type(dunia.dir).objects.filter(pk=dunia.dir.pk).update(is_active=False)
        assert JabatanOrganisasi.objects.filter(tingkat__gte=TINGKAT_DIREKTUR).exists()
        with mock.patch.object(direktur_digest_task, "_koneksi", return_value=(None, "noreply@uji.id")):
            direktur_digest_task.kirim_ringkasan_direktur()
        assert not [m for m in mail.outbox if m.to[0].endswith("@uji.id")]
