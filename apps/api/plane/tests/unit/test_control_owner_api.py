# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""API yang akan dipanggil Owner Panel, dan perintah penyiapan pelanggan.

Yang paling perlu dijaga di sini: endpoint ini menampilkan daftar SELURUH
pelanggan beserta pemakaiannya, jadi kebocoran izinnya bukan kebocoran satu
perusahaan melainkan seluruh portofolio sekaligus.
"""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from rest_framework.test import APIClient

from plane.control.models import Company, Subscription, TenantInstance, UsageSnapshot
from plane.db.models import User
from plane.license.models import Instance, InstanceAdmin

DAFTAR = "/control/companies/"


@pytest.fixture
def admin_instance(db):
    """Admin instance = pemilik produk di deployment bidang kendali."""
    user = User.objects.create(email="owner@nomax.test", username="owner_nomax_test")
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id="uji-1",
        current_version="1",
        last_checked_at=timezone.now(),
    )
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    return user


def _perusahaan(slug="acme", tier="PRO", status=Company.Status.ACTIVE):
    c = Company.objects.create(
        name=slug.upper(), slug=slug, contact_email=f"a@{slug}.test", status=status
    )
    Subscription.objects.create(company=c, tier=tier, started_at=timezone.now() - timedelta(days=5))
    inst = TenantInstance.objects.create(
        company=c, subdomain=slug, secret_hash=TenantInstance.sidik("x" + slug)
    )
    return c, inst


@pytest.mark.unit
@pytest.mark.django_db
class TestIzin:
    def test_anonim_ditolak(self):
        """Daftar ini adalah seluruh portofolio pelanggan. Bocornya bukan satu."""
        assert APIClient().get(DAFTAR).status_code in (401, 403)

    def test_pengguna_biasa_ditolak(self):
        biasa = User.objects.create(email="biasa@demo.test", username="biasa_demo_test")
        klien = APIClient()
        klien.force_authenticate(user=biasa)
        assert klien.get(DAFTAR).status_code == 403

    def test_admin_instance_boleh(self, admin_instance):
        klien = APIClient()
        klien.force_authenticate(user=admin_instance)
        assert klien.get(DAFTAR).status_code == 200


@pytest.mark.unit
@pytest.mark.django_db
class TestDaftar:
    def test_satu_permintaan_sudah_membawa_tingkatan_dan_pemakaian(self, admin_instance):
        """Kalau tidak, sepuluh pelanggan berarti tiga puluh permintaan."""
        _, inst = _perusahaan("acme", tier="EXPERT")
        UsageSnapshot.objects.create(
            instance=inst, taken_at=timezone.now(), workspaces=2, members=9, storage_bytes=1234
        )

        klien = APIClient()
        klien.force_authenticate(user=admin_instance)
        isi = klien.get(DAFTAR).json()["companies"]

        satu = next(c for c in isi if c["slug"] == "acme")
        assert satu["tier"] == "EXPERT"
        assert satu["instances"][0]["subdomain"] == "acme"
        assert satu["instances"][0]["usage"]["members"] == 9

    def test_tanpa_langganan_terbaca_gratis(self, admin_instance):
        Company.objects.create(name="Sepi", slug="sepi", contact_email="s@sepi.test")

        klien = APIClient()
        klien.force_authenticate(user=admin_instance)
        isi = klien.get(DAFTAR).json()["companies"]

        assert next(c for c in isi if c["slug"] == "sepi")["tier"] == "FREE"

    def test_yang_ditampilkan_pemakaian_TERBARU(self, admin_instance):
        _, inst = _perusahaan("baru")
        UsageSnapshot.objects.create(
            instance=inst,
            taken_at=timezone.now() - timedelta(days=3),
            members=1,
        )
        UsageSnapshot.objects.create(instance=inst, taken_at=timezone.now(), members=42)

        klien = APIClient()
        klien.force_authenticate(user=admin_instance)
        isi = klien.get(DAFTAR).json()["companies"]

        assert next(c for c in isi if c["slug"] == "baru")["instances"][0]["usage"]["members"] == 42


@pytest.mark.unit
@pytest.mark.django_db
class TestUbahLangganan:
    def test_naik_kelas_MENGAKHIRI_yang_lama_bukan_menimpanya(self, admin_instance):
        """Penagihan pasti menanyakan sejak kapan mereka Pro. Kolom yang ditimpa
        tidak bisa menjawabnya."""
        c, _ = _perusahaan("naik", tier="PRO")
        klien = APIClient()
        klien.force_authenticate(user=admin_instance)

        jawab = klien.patch(f"/control/companies/{c.slug}/", {"tier": "EXPERT"}, format="json")

        assert jawab.status_code == 200
        assert Subscription.objects.filter(company=c).count() == 2
        assert Subscription.objects.get(company=c, ended_at__isnull=True).tier == "EXPERT"
        assert Subscription.objects.filter(company=c, ended_at__isnull=False).count() == 1

    def test_menyetel_tingkatan_yang_sama_tidak_bikin_baris_kembar(self, admin_instance):
        c, _ = _perusahaan("sama", tier="PRO")
        klien = APIClient()
        klien.force_authenticate(user=admin_instance)

        klien.patch(f"/control/companies/{c.slug}/", {"tier": "PRO"}, format="json")

        assert Subscription.objects.filter(company=c).count() == 1

    def test_menangguhkan_menurunkan_denyut_ke_gratis(self, admin_instance):
        """Menyambungkan dua hal: status di panel, dan apa yang diterima instance."""
        c, inst = _perusahaan("tunggak", tier="EXPERT")
        klien = APIClient()
        klien.force_authenticate(user=admin_instance)
        klien.patch(
            f"/control/companies/{c.slug}/", {"status": "SUSPENDED"}, format="json"
        )

        denyut = APIClient().post(
            "/control/heartbeat/", {}, format="json", HTTP_X_INSTANCE_SECRET="xtunggak"
        )
        assert denyut.json()["tier"] == "FREE"
        assert denyut.json()["company_status"] == "SUSPENDED"

    def test_status_ngawur_ditolak(self, admin_instance):
        c, _ = _perusahaan("ngawur")
        klien = APIClient()
        klien.force_authenticate(user=admin_instance)

        jawab = klien.patch(
            f"/control/companies/{c.slug}/", {"status": "BUKAN-STATUS"}, format="json"
        )
        assert jawab.status_code == 400


@pytest.mark.unit
@pytest.mark.django_db
class TestProvisioning:
    def test_membuat_catatan_dan_menulis_berkas_rahasianya(self, tmp_path, settings):
        settings.ENABLE_CONTROL_PLANE = True
        keluar = tmp_path / "acme.env"

        call_command(
            "provision_tenant",
            "PT Acme",
            subdomain="acme",
            email="admin@acme.test",
            tier="PRO",
            control_url="https://panel.test",
            out=str(keluar),
        )

        c = Company.objects.get(slug="acme")
        assert Subscription.objects.get(company=c, ended_at__isnull=True).tier == "PRO"
        inst = TenantInstance.objects.get(company=c)

        isi = keluar.read_text(encoding="utf-8")
        assert "CONTROL_PLANE_SECRET=" in isi
        assert "ENABLE_CONTROL_PLANE=0" in isi, "instance pelanggan tidak pernah jadi pusat"
        assert "POSTGRES_PASSWORD=" in isi

        # Rahasianya ada di berkas, dan di database HANYA sidiknya.
        rahasia = isi.split('CONTROL_PLANE_SECRET="')[1].split('"')[0]
        assert TenantInstance.sidik(rahasia) == inst.secret_hash
        assert rahasia not in inst.secret_hash

    def test_rahasia_yang_ditulis_benar_benar_bisa_dipakai_berdenyut(self, tmp_path, settings):
        """Uji yang menghubungkan provisioning ke denyut. Tanpa ini, berkasnya bisa
        saja berisi rahasia yang tidak pernah cocok dengan sidik mana pun."""
        settings.ENABLE_CONTROL_PLANE = True
        keluar = tmp_path / "hidup.env"
        call_command(
            "provision_tenant",
            "Hidup",
            subdomain="hidup",
            email="a@hidup.test",
            tier="EXPERT",
            out=str(keluar),
        )
        rahasia = keluar.read_text(encoding="utf-8").split('CONTROL_PLANE_SECRET="')[1].split('"')[0]

        jawab = APIClient().post(
            "/control/heartbeat/", {"members": 3}, format="json", HTTP_X_INSTANCE_SECRET=rahasia
        )

        assert jawab.status_code == 200
        assert jawab.json()["tier"] == "EXPERT"

    def test_menolak_menimpa_berkas_rahasia_yang_sudah_ada(self, tmp_path, settings):
        """Menimpanya berarti melenyapkan rahasia yang mungkin masih dipakai instance hidup."""
        settings.ENABLE_CONTROL_PLANE = True
        keluar = tmp_path / "ada.env"
        keluar.write_text("sudah ada", encoding="utf-8")

        with pytest.raises(CommandError, match="sudah ada"):
            call_command(
                "provision_tenant", "Ada", subdomain="ada", email="a@ada.test", out=str(keluar)
            )

    def test_menolak_subdomain_yang_sudah_dipakai(self, tmp_path, settings):
        settings.ENABLE_CONTROL_PLANE = True
        _perusahaan("dipakai")

        with pytest.raises(CommandError, match="sudah dipakai"):
            call_command(
                "provision_tenant",
                "Dobel",
                subdomain="dipakai",
                email="a@d.test",
                out=str(tmp_path / "dobel.env"),
            )

    def test_menolak_jalan_di_instance_pelanggan(self, tmp_path, settings):
        """Perintah ini menulis ke tabel yang tidak ada di instance pelanggan."""
        settings.ENABLE_CONTROL_PLANE = False

        with pytest.raises(CommandError, match="ENABLE_CONTROL_PLANE"):
            call_command(
                "provision_tenant",
                "Salah",
                subdomain="salah",
                email="a@s.test",
                out=str(tmp_path / "salah.env"),
            )

    def test_menolak_menulis_rahasia_ke_dalam_pohon_kerja_git(self, tmp_path, settings):
        """`.gitignore` adalah janji yang bisa dilanggar satu `git add -f`.

        Riwayat repo ini sudah pernah dicermin ke tempat lain, jadi rahasia yang
        sekali masuk riwayat tidak bisa ditarik kembali. Penjaga yang berjalan
        mengalahkan penjaga yang tertulis.
        """
        settings.ENABLE_CONTROL_PLANE = True
        repo = tmp_path / "repo"
        (repo / ".git").mkdir(parents=True)
        dalam = repo / "apps" / "rahasia.env"

        with pytest.raises(CommandError, match="pohon kerja git"):
            call_command(
                "provision_tenant",
                "Bahaya",
                subdomain="bahaya",
                email="a@b.test",
                out=str(dalam),
            )

    def test_di_luar_repo_tetap_boleh(self, tmp_path, settings):
        settings.ENABLE_CONTROL_PLANE = True
        call_command(
            "provision_tenant",
            "Aman",
            subdomain="aman",
            email="a@a.test",
            out=str(tmp_path / "luar" / "aman.env"),
        )
        assert (tmp_path / "luar" / "aman.env").exists()
