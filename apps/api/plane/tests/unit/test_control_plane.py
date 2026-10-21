# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Bidang kendali: denyut dari instance, dan penerapan tingkatannya kembali.

Yang paling perlu dijaga di sini bukan jalur suksesnya melainkan jalur gagalnya.
Endpoint yang salah membedakan "rahasia salah" dari "instance mati" membocorkan
tebakan, dan instance yang menurunkan tingkatan sendiri saat pusat tidak
terjangkau akan mengunci pelanggan yang sudah membayar.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from plane.control.models import Company, Subscription, TenantInstance, UsageSnapshot
from plane.db.models import User, Workspace, WorkspaceMember, WorkspacePlan

URL = "/control/heartbeat/"


def _instance(status=Company.Status.ACTIVE, tier=None):
    perusahaan = Company.objects.create(
        name="Acme", slug=f"acme-{timezone.now().timestamp()}", contact_email="a@acme.test",
        status=status,
    )
    if tier:
        Subscription.objects.create(
            company=perusahaan, tier=tier, started_at=timezone.now() - timedelta(days=1)
        )
    rahasia, sidik = TenantInstance.terbitkan_rahasia()
    inst = TenantInstance.objects.create(
        company=perusahaan, subdomain=f"acme{int(timezone.now().timestamp()*1000)}",
        secret_hash=sidik,
    )
    return inst, rahasia


@pytest.mark.unit
@pytest.mark.django_db
class TestDenyutMasuk:
    def test_tanpa_rahasia_ditolak(self):
        assert APIClient().post(URL, {}, format="json").status_code == 401

    def test_rahasia_salah_ditolak_dengan_jawaban_yang_SAMA(self):
        """Membedakan 'salah' dari 'mati' memberi tahu penebak bahwa ia sudah dekat."""
        inst, _ = _instance()
        salah = APIClient().post(URL, {}, format="json", HTTP_X_INSTANCE_SECRET="ngawur")

        inst.is_active = False
        inst.save(update_fields=["is_active"])
        _, rahasia_benar = _instance()

        assert salah.status_code == 401
        assert salah.json() == APIClient().post(
            URL, {}, format="json", HTTP_X_INSTANCE_SECRET="ngawur-lain"
        ).json()

    def test_rahasia_asli_tidak_pernah_tersimpan(self):
        """Kebocoran database bidang kendali tidak boleh jadi kunci ke semua instance."""
        inst, rahasia = _instance()
        assert inst.secret_hash != rahasia
        assert len(inst.secret_hash) == 64
        assert TenantInstance.sidik(rahasia) == inst.secret_hash

    def test_denyut_sah_mencatat_pemakaian_dan_jejak_hidup(self):
        inst, rahasia = _instance()

        jawab = APIClient().post(
            URL,
            {"workspaces": 3, "members": 12, "storage_bytes": 4096, "version": "v9"},
            format="json",
            HTTP_X_INSTANCE_SECRET=rahasia,
        )

        assert jawab.status_code == 200
        inst.refresh_from_db()
        assert inst.last_seen_at is not None
        assert inst.version == "v9"

        snap = UsageSnapshot.objects.get(instance=inst)
        assert (snap.workspaces, snap.members, snap.storage_bytes) == (3, 12, 4096)

    def test_angka_ngawur_tidak_merusak_baris(self):
        inst, rahasia = _instance()

        jawab = APIClient().post(
            URL,
            {"workspaces": "banyak", "members": -5, "storage_bytes": None},
            format="json",
            HTTP_X_INSTANCE_SECRET=rahasia,
        )

        assert jawab.status_code == 200
        snap = UsageSnapshot.objects.get(instance=inst)
        assert (snap.workspaces, snap.members, snap.storage_bytes) == (0, 0, 0)


@pytest.mark.unit
@pytest.mark.django_db
class TestTingkatanYangDijawab:
    def test_tanpa_langganan_jawabannya_gratis(self):
        _, rahasia = _instance()
        jawab = APIClient().post(URL, {}, format="json", HTTP_X_INSTANCE_SECRET=rahasia)
        assert jawab.json()["tier"] == "FREE"

    def test_langganan_berjalan_yang_menentukan(self):
        _, rahasia = _instance(tier="EXPERT")
        isi = APIClient().post(URL, {}, format="json", HTTP_X_INSTANCE_SECRET=rahasia).json()
        assert isi["tier"] == "EXPERT"
        # Batasnya ikut dikirim, dan dibaca dari SATU tabel yang sama dengan
        # penegaknya di sisi penyewa.
        assert isi["limits"]["members"] is None

    def test_perusahaan_ditangguhkan_diturunkan_bukan_dimatikan(self):
        """Pelanggan yang tidak bisa masuk tidak akan menyelesaikan tagihannya."""
        _, rahasia = _instance(status=Company.Status.SUSPENDED, tier="PRO")
        jawab = APIClient().post(URL, {}, format="json", HTTP_X_INSTANCE_SECRET=rahasia)
        assert jawab.status_code == 200
        assert jawab.json()["tier"] == "FREE"


@pytest.mark.unit
@pytest.mark.django_db
class TestSisiPenyewa:
    def test_denyut_diam_kalau_pusat_tidak_disetel(self, monkeypatch):
        """Kolam gratis dan instance pasang-sendiri tidak punya pusat, dan itu sah."""
        from plane.bgtasks import control_plane_heartbeat as cph

        monkeypatch.delenv("CONTROL_PLANE_URL", raising=False)
        monkeypatch.delenv("CONTROL_PLANE_SECRET", raising=False)

        assert cph.denyut_bidang_kendali() == "bidang kendali tidak disetel, dilewati"

    def test_pusat_tidak_terjangkau_TIDAK_mengubah_tingkatan(self, monkeypatch):
        """Menurunkan diri sendiri karena jaringan putus mengunci yang sudah membayar."""
        import requests

        from plane.bgtasks import control_plane_heartbeat as cph

        pengguna = User.objects.create(email="t@demo.test", username="t_demo_test")
        ws = Workspace.objects.create(name="t", slug="ws-t", owner=pengguna)
        WorkspaceMember.objects.create(workspace=ws, member=pengguna, role=20)
        WorkspacePlan.objects.create(workspace=ws, tier="PRO")

        monkeypatch.setenv("CONTROL_PLANE_URL", "https://pusat.invalid")
        monkeypatch.setenv("CONTROL_PLANE_SECRET", "x")

        def meledak(*a, **k):
            raise requests.RequestException("putus")

        monkeypatch.setattr(cph.requests, "post", meledak)

        assert cph.denyut_bidang_kendali() == "pusat tidak terjangkau"
        assert WorkspacePlan.objects.get(workspace=ws).tier == "PRO"

    def test_menerapkan_tingkatan_ke_workspace_yang_belum_punya_baris(self):
        from plane.bgtasks.control_plane_heartbeat import terapkan_tingkatan

        pengguna = User.objects.create(email="u@demo.test", username="u_demo_test")
        ws = Workspace.objects.create(name="u", slug="ws-u", owner=pengguna)

        assert terapkan_tingkatan("EXPERT") >= 1
        assert WorkspacePlan.objects.get(workspace=ws).tier == "EXPERT"

    def test_yang_keluar_hanya_tiga_angka_dan_versi(self):
        """Tidak ada nama orang, judul pekerjaan, atau isi berkas yang ikut keluar."""
        from plane.bgtasks.control_plane_heartbeat import kumpulkan_pemakaian

        assert set(kumpulkan_pemakaian()) == {
            "workspaces",
            "members",
            "storage_bytes",
            "version",
        }
