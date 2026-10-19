# Kustomisasi Paradise Task Tracker: pesan langsung antar-karyawan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Yang diuji hanya bagian yang bisa diam-diam salah.

Bukan "apakah pesan tersimpan", itu satu baris ORM. Yang diuji: kueri DISTINCT ON
yang meringkas percakapan, dan pemeriksaan penerima di sisi server. Dua-duanya
gagal tanpa suara kalau rusak: yang pertama menampilkan daftar yang tampak wajar
tapi salah orang, yang kedua baru terlihat setelah ada yang mencobanya.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from plane.db.models import Langganan, Ruang, FileAsset, PesanLangsung, ReaksiPesan, User, Workspace, WorkspaceMember


def _ruang_dm(workspace, a, b):
    """Ruang DM antara dua orang, dibuat kalau belum ada.

    Sengaja meniru `_ruang_dm` di views, bukan memanggilnya: kalau nanti keduanya
    berbeda, ujinya harus MERAH, bukan diam-diam ikut berubah bersama kodenya.
    """
    kunci = Ruang.buat_kunci_dm(a.id, b.id)
    ruang, dibuat = Ruang.objects.get_or_create(
        kunci_dm=kunci, defaults={"workspace": workspace, "tipe": Ruang.Tipe.DM}
    )
    if dibuat:
        Langganan.objects.bulk_create(
            [Langganan(ruang=ruang, user=a), Langganan(ruang=ruang, user=b)]
        )
    return ruang


def _pesan(workspace, dari, ke, isi, menit_lalu):
    """Buat pesan dengan waktu yang pasti berbeda.

    `created_at` memakai auto_now_add, jadi tiga pesan yang dibuat dalam satu
    tarikan napas bisa berbagi mikrodetik yang sama dan urutannya jadi undian.
    Ditimpa lewat update supaya urutan yang diuji memang urutan yang dimaksud.
    """
    ruang = _ruang_dm(workspace, dari, ke)
    pesan = PesanLangsung.objects.create(
        workspace=workspace, ruang=ruang, pengirim=dari, penerima=ke, isi=isi
    )
    waktu = timezone.now() - timedelta(minutes=menit_lalu)
    PesanLangsung.objects.filter(pk=pesan.pk).update(created_at=waktu)
    # Ruang ikut digeser, karena daftar percakapan diurutkan dari medan ini dan
    # penanda baca dibandingkan terhadapnya.
    if ruang.pesan_terakhir_pada is None or waktu > ruang.pesan_terakhir_pada:
        Ruang.objects.filter(pk=ruang.pk).update(pesan_terakhir_pada=waktu)
    return pesan


def _orang(nama):
    # `username` unik dan TIDAK boleh dikosongkan: dua User tanpa username
    # menabrak users_username_key, dan galatnya menunjuk ke baris kedua,
    # bukan ke sebabnya.
    return User.objects.create(
        id=uuid4(), username=nama, email=f"{nama}@paradise.test", display_name=nama, is_active=True
    )


@pytest.fixture
def kantor(db):
    """Satu workspace berisi tiga orang.

    Memakai ORM langsung, bukan plane.tests.factories: factory_boy adalah
    dependensi pengembangan dan tidak ada di image runtime, jadi uji ini akan
    gagal impor di container padahal isinya tidak salah apa-apa.
    """
    pemilik = _orang("aku")
    workspace = Workspace.objects.create(id=uuid4(), name="Kantor", slug="kantor-uji", owner=pemilik)
    budi = _orang("budi")
    citra = _orang("citra")
    for satu in (pemilik, budi, citra):
        WorkspaceMember.objects.create(workspace=workspace, member=satu, role=20)
    return workspace, pemilik, budi, citra


@pytest.mark.unit
class TestChat:
    @pytest.mark.django_db
    def test_percakapan_satu_baris_per_lawan_bicara(self, kantor):
        workspace, aku, budi, citra = kantor
        _pesan(workspace, budi, aku, "halo", menit_lalu=10)
        _pesan(workspace, aku, budi, "hai", menit_lalu=5)
        _pesan(workspace, budi, aku, "apa kabar", menit_lalu=1)
        _pesan(workspace, citra, aku, "titip berkas ya", menit_lalu=30)

        client = APIClient()
        client.force_authenticate(user=aku)
        res = client.get(f"/api/workspaces/{workspace.slug}/chat/")

        assert res.status_code == 200
        # Empat pesan, dua lawan bicara. Kalau DISTINCT ON hilang, ini jadi 4.
        assert len(res.data) == 2
        # Budi lebih dulu karena pesannya paling baru, meski Citra lebih dulu masuk.
        budi_baris, citra_baris = res.data
        assert budi_baris["lawan_bicara"] == str(budi.id)
        assert budi_baris["isi"] == "apa kabar"
        assert budi_baris["dari_saya"] is False
        assert budi_baris["belum_dibaca"] == 2
        assert citra_baris["lawan_bicara"] == str(citra.id)
        assert citra_baris["belum_dibaca"] == 1

    @pytest.mark.django_db
    def test_membuka_percakapan_menandai_terbaca(self, kantor):
        workspace, aku, budi, _ = kantor
        _pesan(workspace, budi, aku, "halo", menit_lalu=2)

        client = APIClient()
        client.force_authenticate(user=aku)
        assert client.get(f"/api/workspaces/{workspace.slug}/chat/{budi.id}/").status_code == 200

        assert PesanLangsung.objects.filter(penerima=aku, dibaca_pada__isnull=True).count() == 0
        # Yang ditandai hanya pesan MASUK. Pesan keluar milik lawan bicara.
        assert PesanLangsung.objects.filter(pengirim=aku, dibaca_pada__isnull=False).count() == 0

    @pytest.mark.django_db
    def test_penanda_baru_dihitung_sebelum_ditandai_terbaca(self, kantor):
        """UI memakai `baru` untuk menarik garis "pesan belum dibaca".

        Kalau penandanya dihitung SESUDAH UPDATE terbaca jalan, semuanya sudah
        terbaca dan garis itu tidak akan pernah muncul untuk siapa pun. Gagalnya
        senyap: responsnya tetap 200 dan pesannya tetap lengkap.
        """
        workspace, aku, budi, _ = kantor
        _pesan(workspace, aku, budi, "punyaku", menit_lalu=3)
        _pesan(workspace, budi, aku, "punya budi", menit_lalu=2)

        client = APIClient()
        client.force_authenticate(user=aku)
        res = client.get(f"/api/workspaces/{workspace.slug}/chat/{budi.id}/")

        assert [p["baru"] for p in res.data] == [False, True]
        # Muatan kedua: sudah terbaca, jadi tidak ada lagi yang ditandai baru.
        res2 = client.get(f"/api/workspaces/{workspace.slug}/chat/{budi.id}/")
        assert [p["baru"] for p in res2.data] == [False, False]

    @pytest.mark.django_db
    def test_jumlah_belum_dibaca_hanya_menghitung_pesan_masuk(self, kantor):
        workspace, aku, budi, citra = kantor
        _pesan(workspace, budi, aku, "satu", menit_lalu=3)
        _pesan(workspace, citra, aku, "dua", menit_lalu=2)
        # Pesan KELUAR tidak boleh ikut terhitung. Kalau filternya salah arah,
        # lencana sidebar akan menghitung pesan yang kita kirim sendiri.
        _pesan(workspace, aku, budi, "tiga", menit_lalu=1)

        client = APIClient()
        client.force_authenticate(user=aku)
        res = client.get(f"/api/workspaces/{workspace.slug}/chat/belum-dibaca/")

        assert res.status_code == 200
        assert res.data["jumlah"] == 2

        # Membuka percakapan dengan Budi menurunkan hitungannya, bukan menolkan.
        client.get(f"/api/workspaces/{workspace.slug}/chat/{budi.id}/")
        assert client.get(f"/api/workspaces/{workspace.slug}/chat/belum-dibaca/").data["jumlah"] == 1

    @pytest.mark.django_db
    def test_tidak_bisa_mengirim_ke_orang_di_luar_workspace(self, kantor):
        workspace, aku, _, _ = kantor
        orang_luar = _orang("dewi")

        client = APIClient()
        client.force_authenticate(user=aku)
        res = client.post(f"/api/workspaces/{workspace.slug}/chat/{orang_luar.id}/", {"isi": "hai"})

        assert res.status_code == 404
        assert PesanLangsung.objects.count() == 0

    @pytest.mark.django_db
    def test_lampiran_hanya_boleh_dibuka_pihak_yang_berhak(self, kantor):
        """Penjaga lampiran, diuji lewat fungsinya langsung.

        Fungsi ini dipanggil DUA endpoint: milik Obrolan dan endpoint unduhan
        bawaan yang melayani setiap anggota workspace. Kalau ia salah, id
        lampiran yang bocor sekali bisa dibuka siapa pun yang punya akun.
        """
        from plane.app.views.chat import boleh_lihat_lampiran

        workspace, aku, budi, citra = kantor
        pesan = _pesan(workspace, budi, citra, "ini fotonya", menit_lalu=1)
        aset = FileAsset.objects.create(
            attributes={"name": "foto.jpg", "type": "image/jpeg"},
            asset="x/foto.jpg",
            size=10,
            workspace=workspace,
            created_by=budi,
            entity_type=FileAsset.EntityTypeContext.CHAT_ATTACHMENT,
            entity_identifier=str(pesan.id),
            is_uploaded=True,
        )

        assert boleh_lihat_lampiran(budi, aset, workspace.slug) is True, "pengirim boleh"
        assert boleh_lihat_lampiran(citra, aset, workspace.slug) is True, "penerima boleh"
        # Pemilik workspace TIDAK boleh: kewenangan membaca obrolan orang lain
        # ditarik 13 Agt 2026, dan lampiran adalah isi obrolan juga.
        assert boleh_lihat_lampiran(aku, aset, workspace.slug) is False, "pemilik workspace TIDAK boleh"

        orang_lain = _orang("dewi")
        WorkspaceMember.objects.create(workspace=workspace, member=orang_lain, role=15)
        assert boleh_lihat_lampiran(orang_lain, aset, workspace.slug) is False, (
            "anggota lain TIDAK boleh, walau punya akun dan tahu id-nya"
        )

    @pytest.mark.django_db
    def test_lampiran_orang_lain_tidak_bisa_ditempel_ke_pesan_sendiri(self, kantor):
        workspace, aku, budi, citra = kantor
        # Berkas milik Citra, belum menempel ke pesan mana pun.
        aset = FileAsset.objects.create(
            attributes={"name": "rahasia.pdf", "type": "application/pdf"},
            asset="x/rahasia.pdf",
            size=10,
            workspace=workspace,
            created_by=citra,
            entity_type=FileAsset.EntityTypeContext.CHAT_ATTACHMENT,
            is_uploaded=True,
        )

        client = APIClient()
        client.force_authenticate(user=budi)
        res = client.post(
            f"/api/workspaces/{workspace.slug}/chat/{aku.id}/",
            {"isi": "lihat ini", "lampiran": [str(aset.id)]},
            format="json",
        )

        # Pesannya tetap terkirim, tapi berkas orang lain TIDAK ikut menempel.
        assert res.status_code == 201
        assert res.data["lampiran"] == []
        aset.refresh_from_db()
        assert aset.entity_identifier is None

    @pytest.mark.django_db
    def test_hanya_pengirim_yang_bisa_menyunting_dan_menghapus(self, kantor):
        """Pemilik workspace pun tidak boleh mengubah tulisan orang.

        Mengawasi itu membaca. Menyunting kalimat orang lain adalah hal yang
        sama sekali berbeda dan tidak pernah diminta, jadi jalannya memang
        tidak disediakan.
        """
        workspace, aku, budi, _ = kantor
        pesan = _pesan(workspace, budi, aku, "aslinya begini", menit_lalu=1)

        client = APIClient()
        client.force_authenticate(user=aku)  # penerima, sekaligus pemilik workspace
        ubah = client.patch(
            f"/api/workspaces/{workspace.slug}/chat/pesan/{pesan.id}/", {"isi": "diubah"}, format="json"
        )
        hapus = client.delete(f"/api/workspaces/{workspace.slug}/chat/pesan/{pesan.id}/")

        assert ubah.status_code == 404
        assert hapus.status_code == 404
        pesan.refresh_from_db()
        assert pesan.isi == "aslinya begini"

        # Pengirimnya sendiri boleh.
        client.force_authenticate(user=budi)
        ubah2 = client.patch(
            f"/api/workspaces/{workspace.slug}/chat/pesan/{pesan.id}/", {"isi": "sudah dibetulkan"}, format="json"
        )
        assert ubah2.status_code == 200
        assert ubah2.data["disunting"] is True
        assert client.delete(f"/api/workspaces/{workspace.slug}/chat/pesan/{pesan.id}/").status_code == 204
        assert PesanLangsung.objects.filter(id=pesan.id).count() == 0, "hilang dari daftar"
        assert PesanLangsung.all_objects.filter(id=pesan.id).count() == 1, "barisnya tetap ada untuk audit"

    @pytest.mark.django_db
    def test_reaksi_klik_kedua_membatalkan(self, kantor):
        workspace, aku, budi, citra = kantor
        pesan = _pesan(workspace, budi, aku, "halo", menit_lalu=1)

        client = APIClient()
        client.force_authenticate(user=aku)
        url = f"/api/workspaces/{workspace.slug}/chat/pesan/{pesan.id}/reaksi/"

        assert client.post(url, {"emoji": "👍"}, format="json").data["aktif"] is True
        assert ReaksiPesan.objects.count() == 1
        assert client.post(url, {"emoji": "👍"}, format="json").data["aktif"] is False
        assert ReaksiPesan.objects.count() == 0

        # Orang di luar percakapan tidak bisa ikut bereaksi.
        client.force_authenticate(user=citra)
        assert client.post(url, {"emoji": "👍"}, format="json").status_code == 404

    @pytest.mark.django_db
    def test_penggulungan_riwayat_memakai_sebelum(self, kantor):
        workspace, aku, budi, _ = kantor
        for i in range(5):
            _pesan(workspace, budi, aku, f"pesan {i}", menit_lalu=10 - i)

        client = APIClient()
        client.force_authenticate(user=aku)
        semua = client.get(f"/api/workspaces/{workspace.slug}/chat/{budi.id}/")
        assert [p["isi"] for p in semua.data] == ["pesan 0", "pesan 1", "pesan 2", "pesan 3", "pesan 4"]

        batas = semua.data[2]["created_at"].isoformat()
        lama = client.get(f"/api/workspaces/{workspace.slug}/chat/{budi.id}/", {"sebelum": batas})
        assert [p["isi"] for p in lama.data] == ["pesan 0", "pesan 1"], "hanya yang lebih tua dari batas"

        # Nilai ngawur dijawab dengan keterangan, bukan 400 mentah.
        ngawur = client.get(f"/api/workspaces/{workspace.slug}/chat/{budi.id}/", {"sebelum": "kemarin"})
        assert ngawur.status_code == 400
        assert "ISO" in ngawur.data["error"]

    @pytest.mark.django_db
    def test_kutipan_hanya_dari_percakapan_yang_sama(self, kantor):
        workspace, aku, budi, citra = kantor
        # Pesan milik percakapan LAIN (Budi dengan Citra).
        asing = _pesan(workspace, budi, citra, "rahasia mereka", menit_lalu=5)

        client = APIClient()
        client.force_authenticate(user=aku)
        res = client.post(
            f"/api/workspaces/{workspace.slug}/chat/{budi.id}/",
            {"isi": "coba kutip", "balasan_ke": str(asing.id)},
            format="json",
        )

        assert res.status_code == 201
        # Terkirim, tapi kutipannya DIBUANG: cuplikan percakapan orang lain
        # tidak boleh ikut terbawa.
        assert res.data["balasan_ke"] is None

    @pytest.mark.django_db
    def test_pencarian_tidak_menembus_obrolan_orang_lain(self, kantor):
        """Ini penjaga pencarian.

        Kalau saringannya lepas, satu kata kunci cukup untuk membaca cuplikan
        obrolan seluruh kantor, dan tidak ada gejala apa pun di layar.
        """
        workspace, aku, budi, citra = kantor
        _pesan(workspace, budi, aku, "invoice bulan ini sudah dibayar", menit_lalu=5)
        _pesan(workspace, budi, citra, "invoice rahasia mereka berdua", menit_lalu=4)

        client = APIClient()
        client.force_authenticate(user=aku)
        res = client.get(f"/api/workspaces/{workspace.slug}/chat/cari/", {"q": "invoice"})

        assert res.status_code == 200
        assert [h["isi"] for h in res.data] == ["invoice bulan ini sudah dibayar"]
        assert res.data[0]["lawan_bicara"] == str(budi.id)

        # Kata kunci terlalu pendek ditolak dengan keterangan.
        pendek = client.get(f"/api/workspaces/{workspace.slug}/chat/cari/", {"q": "in"})
        assert pendek.status_code == 400

    @pytest.mark.django_db
    def test_pesan_kosong_ditolak(self, kantor):
        workspace, aku, budi, _ = kantor

        client = APIClient()
        client.force_authenticate(user=aku)
        res = client.post(f"/api/workspaces/{workspace.slug}/chat/{budi.id}/", {"isi": "   "})

        assert res.status_code == 400
        assert PesanLangsung.objects.count() == 0
