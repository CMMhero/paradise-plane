# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Penagihan: menerbitkan tagihan, menerima webhook, menyapu yang lewat tempo.

Xendit TIDAK dihubungi. Uji yang memanggil sandbox sungguhan butuh kunci API,
jaringan, dan akun merchant, jadi ia akan merah di mesin siapa pun yang tidak
punya ketiganya. Yang dijaga di sini aturan uangnya, dan aturan itu milik kita.

Batas yang jujur: bentuk muatan Xendit sungguhan BELUM pernah diverifikasi
terhadap sandbox. Uji ini membuktikan logikanya benar untuk muatan berbentuk
seperti yang didokumentasikan Xendit, bukan bahwa bentuknya sudah pasti begitu.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from plane.control import billing, xendit
from plane.control.models import Company, Invoice, Subscription
from plane.db.models import User
from plane.license.models import Instance, InstanceAdmin

WEBHOOK = "/control/payments/xendit/"


@pytest.fixture
def admin_instance(db):
    user = User.objects.create(email="owner@nomax.test", username="owner_nomax_test")
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id="uji-1",
        current_version="1",
        last_checked_at=timezone.now(),
    )
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    return user


def _perusahaan(slug="acme", tier="PRO", status=Company.Status.TRIAL):
    c = Company.objects.create(
        name=slug.upper(), slug=slug, contact_email=f"a@{slug}.test", status=status
    )
    Subscription.objects.create(company=c, tier=tier, started_at=timezone.now())
    return c


@pytest.mark.unit
@pytest.mark.django_db
class TestMenerbitkanTagihan:
    def test_memakai_tingkatan_berjalan_dan_harga_daftarnya(self):
        c = _perusahaan("terbit", tier="PRO")

        t = billing.terbitkan_tagihan(c)

        assert t.tier == "PRO"
        assert t.amount == billing.HARGA["PRO"]
        assert t.status == Invoice.Status.PENDING
        assert t.due_at > timezone.now()

    def test_FREE_dan_ENTERPRISE_tidak_punya_harga_daftar(self):
        """FREE tidak ditagih, ENTERPRISE ditagih lewat kesepakatan."""
        for tier in ("FREE", "ENTERPRISE"):
            with pytest.raises(billing.TidakBisaDitagih):
                billing.harga(tier)

    def test_jumlahnya_DISIMPAN_bukan_dihitung_ulang(self, monkeypatch):
        """Catatan keuangan yang berubah sendiri saat harga naik bukan catatan."""
        c = _perusahaan("beku", tier="PRO")
        t = billing.terbitkan_tagihan(c)
        lama = t.amount

        monkeypatch.setitem(billing.HARGA, "PRO", lama * 3)
        t.refresh_from_db()

        assert t.amount == lama


@pytest.mark.unit
@pytest.mark.django_db
class TestWebhook:
    def _kirim(self, muatan, token="rahasia-uji"):
        return APIClient().post(WEBHOOK, muatan, format="json", HTTP_X_CALLBACK_TOKEN=token)

    def test_token_kosong_MENOLAK_SEMUA_bukan_menerima_semua(self, monkeypatch):
        """Instance yang belum disetel lebih baik kehilangan webhook daripada
        menerima perintah 'tandai lunas' dari siapa pun yang menemukan alamatnya."""
        monkeypatch.delenv("XENDIT_CALLBACK_TOKEN", raising=False)

        assert self._kirim({"external_id": "x", "status": "PAID"}, token="").status_code == 401
        assert self._kirim({"external_id": "x", "status": "PAID"}, token="apa-saja").status_code == 401

    def test_token_salah_ditolak(self, monkeypatch):
        monkeypatch.setenv("XENDIT_CALLBACK_TOKEN", "rahasia-uji")

        assert self._kirim({"external_id": "x"}, token="salah").status_code == 401

    def test_pembayaran_sah_melunasi_dan_mengaktifkan_perusahaannya(self, monkeypatch):
        monkeypatch.setenv("XENDIT_CALLBACK_TOKEN", "rahasia-uji")
        c = _perusahaan("bayar", tier="PRO")
        t = billing.terbitkan_tagihan(c)

        jawab = self._kirim(
            {"external_id": t.external_id, "status": "PAID", "paid_amount": t.amount}
        )

        assert jawab.status_code == 200
        t.refresh_from_db()
        c.refresh_from_db()
        assert t.status == Invoice.Status.PAID
        assert t.paid_at is not None
        assert c.status == Company.Status.ACTIVE

    def test_webhook_ganda_TIDAK_memperpanjang_dua_kali(self, monkeypatch):
        """Penyedia mengirim ulang yang tidak dijawab 200, dan sebagian mengirim
        ganda tanpa alasan. Langganan tidak boleh bertambah karena jaringan buruk."""
        monkeypatch.setenv("XENDIT_CALLBACK_TOKEN", "rahasia-uji")
        c = _perusahaan("ganda", tier="PRO")
        t = billing.terbitkan_tagihan(c)
        muatan = {"external_id": t.external_id, "status": "PAID", "paid_amount": t.amount}

        self._kirim(muatan)
        self._kirim(muatan)
        self._kirim(muatan)

        assert Subscription.objects.filter(company=c).count() == 1

    def test_pembayaran_KURANG_tidak_ditandai_lunas(self, monkeypatch):
        """Memperlakukan pembayaran sebagian sebagai lunas berarti memberi
        langganan penuh untuk uang yang tidak penuh."""
        monkeypatch.setenv("XENDIT_CALLBACK_TOKEN", "rahasia-uji")
        c = _perusahaan("kurang", tier="PRO")
        t = billing.terbitkan_tagihan(c)

        self._kirim(
            {"external_id": t.external_id, "status": "PAID", "paid_amount": t.amount - 1}
        )

        t.refresh_from_db()
        assert t.status == Invoice.Status.PENDING

    def test_tagihan_tak_dikenal_tetap_dijawab_200(self, monkeypatch):
        """Penyedia mengirim ulang selamanya apa pun yang tidak dijawab 200."""
        monkeypatch.setenv("XENDIT_CALLBACK_TOKEN", "rahasia-uji")

        jawab = self._kirim({"external_id": "tidak-pernah-ada", "status": "PAID"})

        assert jawab.status_code == 200
        assert jawab.json()["handled"] is False

    def test_status_expired_menandai_tagihannya(self, monkeypatch):
        monkeypatch.setenv("XENDIT_CALLBACK_TOKEN", "rahasia-uji")
        c = _perusahaan("hangus", tier="PRO")
        t = billing.terbitkan_tagihan(c)

        self._kirim({"external_id": t.external_id, "status": "EXPIRED"})

        t.refresh_from_db()
        assert t.status == Invoice.Status.EXPIRED

    def test_naik_kelas_lewat_pembayaran_mengakhiri_langganan_lama(self, monkeypatch):
        monkeypatch.setenv("XENDIT_CALLBACK_TOKEN", "rahasia-uji")
        c = _perusahaan("naik", tier="PRO")
        t = billing.terbitkan_tagihan(c, tier="EXPERT")

        self._kirim({"external_id": t.external_id, "status": "PAID", "paid_amount": t.amount})

        assert Subscription.objects.get(company=c, ended_at__isnull=True).tier == "EXPERT"
        assert Subscription.objects.filter(company=c, ended_at__isnull=False).count() == 1


@pytest.mark.unit
@pytest.mark.django_db
class TestSapuLewatTempo:
    def test_menandai_menunggak_TAPI_BELUM_menangguhkan(self):
        """Menangguhkan di hari jatuh tempo menghukum transfer yang masih di jalan."""
        c = _perusahaan("telat", tier="PRO", status=Company.Status.ACTIVE)
        t = billing.terbitkan_tagihan(c)
        Invoice.objects.filter(pk=t.pk).update(due_at=timezone.now() - timedelta(days=1))

        hasil = billing.sapu_lewat_tempo()

        c.refresh_from_db()
        assert hasil["menunggak"] == 1
        assert hasil["ditangguhkan"] == 0
        assert c.status == Company.Status.PAST_DUE

    def test_menangguhkan_sesudah_tenggang_habis(self):
        c = _perusahaan("lama", tier="PRO", status=Company.Status.ACTIVE)
        t = billing.terbitkan_tagihan(c)
        Invoice.objects.filter(pk=t.pk).update(
            due_at=timezone.now() - timedelta(days=billing.TENGGANG_HARI + 2)
        )

        billing.sapu_lewat_tempo()

        c.refresh_from_db()
        assert c.status == Company.Status.SUSPENDED

    def test_tidak_pernah_menyentuh_yang_sudah_berhenti(self):
        """Menagih orang yang sudah pergi adalah cara memastikan mereka tidak kembali."""
        c = _perusahaan("pergi", tier="PRO", status=Company.Status.CHURNED)
        t = billing.terbitkan_tagihan(c)
        Invoice.objects.filter(pk=t.pk).update(due_at=timezone.now() - timedelta(days=99))

        billing.sapu_lewat_tempo()

        c.refresh_from_db()
        assert c.status == Company.Status.CHURNED

    def test_yang_sudah_lunas_tidak_ikut_disapu(self):
        c = _perusahaan("lunas", tier="PRO", status=Company.Status.ACTIVE)
        t = billing.terbitkan_tagihan(c)
        Invoice.objects.filter(pk=t.pk).update(
            status=Invoice.Status.PAID, due_at=timezone.now() - timedelta(days=99)
        )

        hasil = billing.sapu_lewat_tempo()

        c.refresh_from_db()
        assert hasil["kedaluwarsa"] == 0
        assert c.status == Company.Status.ACTIVE


@pytest.mark.unit
@pytest.mark.django_db
class TestEndpointTerbitkanTagihan:
    def test_anonim_ditolak(self):
        assert APIClient().post("/control/companies/x/invoices/").status_code in (401, 403)

    def test_tanpa_kunci_xendit_MEMBATALKAN_barisnya(self, admin_instance, monkeypatch):
        """Tagihan PENDING tanpa halaman bayar akan disapu jadi kedaluwarsa lalu
        menandai pelanggan menunggak padahal tidak ada yang pernah menagih mereka."""
        monkeypatch.delenv("XENDIT_SECRET_KEY", raising=False)
        c = _perusahaan("nokey", tier="PRO")
        klien = APIClient()
        klien.force_authenticate(user=admin_instance)

        jawab = klien.post(f"/control/companies/{c.slug}/invoices/", {}, format="json")

        assert jawab.status_code == 503
        assert Invoice.objects.get(company=c).status == Invoice.Status.VOID

    def test_penyedia_menolak_juga_MEMBATALKAN_barisnya(self, admin_instance, monkeypatch):
        c = _perusahaan("tolak", tier="PRO")

        def meledak(**kwargs):
            raise xendit.XenditGagal("Xendit menolak (400): amount invalid")

        monkeypatch.setattr(xendit, "buat_invoice", meledak)
        klien = APIClient()
        klien.force_authenticate(user=admin_instance)

        jawab = klien.post(f"/control/companies/{c.slug}/invoices/", {}, format="json")

        assert jawab.status_code == 502
        assert Invoice.objects.get(company=c).status == Invoice.Status.VOID

    def test_berhasil_menyimpan_alamat_bayarnya(self, admin_instance, monkeypatch):
        c = _perusahaan("sukses", tier="PRO")
        monkeypatch.setattr(
            xendit, "buat_invoice", lambda **k: ("xnd-1", "https://bayar.test/xnd-1", "PENDING")
        )
        klien = APIClient()
        klien.force_authenticate(user=admin_instance)

        jawab = klien.post(f"/control/companies/{c.slug}/invoices/", {}, format="json")

        assert jawab.status_code == 201
        t = Invoice.objects.get(company=c)
        assert t.invoice_url == "https://bayar.test/xnd-1"
        assert t.provider_id == "xnd-1"
        assert jawab.json()["amount"] == billing.HARGA["PRO"]
