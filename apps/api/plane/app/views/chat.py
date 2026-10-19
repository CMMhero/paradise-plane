# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pesan langsung antar-karyawan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Obrolan dua orang di dalam satu workspace.

Tidak ada WebSocket di sini, dan itu disengaja untuk versi pertama. Peramban
menarik ulang percakapan yang sedang dibuka tiap beberapa detik. Untuk 79
karyawan beban itu tidak terasa, dan yang dihemat besar: tanpa ini kita perlu
menyambungkan `apps/live` ke sesi Django, memutuskan apa yang terjadi saat
sambungan putus, dan menguji dua jalur pengiriman yang bisa saling menyalip.

ponytail: tarik-ulang berkala, batasnya sekitar 200 orang mengobrol bersamaan.
Kalau tercapai, jalur naiknya sudah ada dan jangan ganti dengan Django Channels:
`apps/live` sudah memakai express-ws + Redis, jadi tambahkan satu rute di sana
yang menyiarkan pesan baru, dan endpoint ini tetap jadi satu-satunya penulis.
"""

# Python imports
import logging

# Django imports
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

# Third Party imports
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.response import Response

from plane.settings.storage import S3Storage
from plane.utils.chat_ruang import ruang_dm
from plane.utils.ice import daftar_ice
from plane.utils.livekit import konfigurasi_ada, nama_ruang, token_panggilan, url_livekit
from plane.utils.obrolan_siaran import siarkan

# Module imports
from plane.app.permissions import WorkspaceEntityPermission
from plane.db.models import (
    BATAS_ISI,
    FileAsset,
    Langganan,
    PesanLangsung,
    ReaksiPesan,
    Ruang,
    Workspace,
    WorkspaceMember,
)

from .base import BaseAPIView

# "plane.api", BUKAN "plane". Konfigurasi logging produksi memakai
# disable_existing_loggers dan TIDAK punya entri untuk "plane" polos, jadi
# catatan yang dikirim ke sana tidak sampai ke mana-mana. Untuk jejak audit,
# itu kegagalan yang paling buruk bentuknya: terlihat ada di kode, tidak ada
# di kenyataan, dan baru ketahuan saat dibutuhkan.
logger = logging.getLogger("plane.api")

# Berapa pesan terakhir yang dikirim ke peramban saat percakapan dibuka.
# ponytail: tanpa penggulungan ke belakang. Pesan ke-101 masih ada di database
# dan tidak hilang, cuma belum bisa dilihat dari UI. Tambahkan parameter
# `sebelum=<created_at>` di sini kalau ada yang benar-benar memintanya.
JUMLAH_PESAN = 100

# Batas hasil pencarian. Tanpa batas, satu kata umum seperti "ya" menarik
# seluruh riwayat ke dalam satu respons.
JUMLAH_HASIL_CARI = 50

# Berapa lampiran boleh menempel pada satu pesan.
BATAS_LAMPIRAN = 5


def _peta_lampiran(pesan_ids, slug):
    """Lampiran seluruh pesan dalam SATU kueri, dikelompokkan per pesan.

    Tanpa ini, merender 100 pesan berarti 100 kueri lampiran. Kuncinya
    `entity_identifier`, yang sudah ter-indeks bersama `entity_type`.
    """
    peta = {}
    aset = FileAsset.objects.filter(
        entity_type=FileAsset.EntityTypeContext.CHAT_ATTACHMENT,
        entity_identifier__in=[str(i) for i in pesan_ids],
        is_uploaded=True,
    )
    for a in aset:
        peta.setdefault(a.entity_identifier, []).append(
            {
                "id": str(a.id),
                "nama": a.attributes.get("name", ""),
                "tipe": a.attributes.get("type", ""),
                "ukuran": a.size,
                # URL berpenjaga milik Obrolan, BUKAN /assets/v2/static/ yang
                # AllowAny. Yang statis itu memang hanya melayani avatar dan
                # logo, dan memang seharusnya begitu.
                "url": f"/api/workspaces/{slug}/chat/lampiran/{a.id}/",
            }
        )
    return peta


def _peta_reaksi(pesan_ids):
    """Reaksi seluruh pesan dalam satu kueri, dikelompokkan per pesan lalu per
    emoji, berikut siapa saja yang memberikannya."""
    peta = {}
    for r in ReaksiPesan.objects.filter(pesan_id__in=pesan_ids).values("pesan_id", "emoji", "user_id"):
        baris = peta.setdefault(str(r["pesan_id"]), {})
        baris.setdefault(r["emoji"], []).append(str(r["user_id"]))
    return {
        pid: [{"emoji": e, "orang": orang} for e, orang in emoji.items()]
        for pid, emoji in peta.items()
    }


def _peta_kutipan(pesan_list):
    """Cuplikan pesan yang dibalas, satu kueri untuk semuanya."""
    induk_ids = {p.balasan_ke_id for p in pesan_list if p.balasan_ke_id}
    if not induk_ids:
        return {}
    induk = PesanLangsung.objects.filter(id__in=induk_ids).values("id", "isi", "pengirim_id")
    return {
        str(i["id"]): {
            "id": str(i["id"]),
            "pengirim": str(i["pengirim_id"]),
            # Dipotong di server: yang dibutuhkan UI cuma cuplikan, dan
            # mengirim pesan panjang dua kali membengkakkan tiap muatan.
            "isi": (i["isi"] or "")[:120],
        }
        for i in induk
    }


# Panjang maksimum nama kanal. Bukan batas teknis, tapi batas supaya daftar
# percakapan di sidebar tetap terbaca tanpa terpotong di tengah kata.
BATAS_NAMA_RUANG = 80


def _ruang_dm(request, slug, lawan_id):
    """Ruang DM antara peminta dan lawan bicaranya, kalau lawannya memang ada.

    Yang dikerjakan di sini cuma penjagaan pintunya: lawan bicara harus anggota
    aktif workspace ini. Pembuatan ruangnya sendiri ada di `utils/chat_ruang.py`,
    dipakai bersama tugas Celery yang mengirim penugasan sebagai DM, supaya
    aturan "kedua pihak langsung berlangganan" cuma ditulis satu kali.
    """
    anggota = WorkspaceMember.objects.filter(
        workspace__slug=slug, member_id=lawan_id, is_active=True
    ).select_related("workspace").first()
    if anggota is None:
        return None

    return ruang_dm(anggota.workspace_id, request.user.id, lawan_id)


def _langganan(user_id, ruang):
    """Langganan orang ini di ruang ini, atau None kalau bukan anggota.

    Ini SATU-SATUNYA penjaga akses isi ruang. Kanal publik pun tidak dibaca
    tanpa berlangganan lebih dulu, supaya tidak ada dua jalur izin yang harus
    dijaga sinkron.
    """
    return Langganan.objects.filter(ruang=ruang, user_id=user_id).first()


def _tandai_terbaca(langganan, sampai):
    """Geser penanda baca MAJU saja.

    Mundur akan terjadi kalau orang membuka riwayat lama, dan itu membuat pesan
    yang sudah dibaca muncul lagi sebagai belum dibaca.
    """
    if sampai and (langganan.dibaca_sampai is None or sampai > langganan.dibaca_sampai):
        langganan.dibaca_sampai = sampai
        langganan.save(update_fields=["dibaca_sampai", "updated_at"])


def _jumlah_belum_dibaca(langganan):
    """Pesan di ruang ini yang lebih baru dari penanda baca dan bukan kiriman sendiri."""
    kueri = PesanLangsung.objects.filter(ruang_id=langganan.ruang_id).exclude(pengirim_id=langganan.user_id)
    if langganan.dibaca_sampai is not None:
        kueri = kueri.filter(created_at__gt=langganan.dibaca_sampai)
    return kueri.count()


def _bentuk(pesan, slug, saya_id=None, lampiran=None, reaksi=None, dikutip=None):
    return {
        "id": str(pesan.id),
        "pengirim": str(pesan.pengirim_id),
        "isi": pesan.isi,
        "created_at": pesan.created_at,
        "lampiran": lampiran or [],
        "disunting": pesan.disunting_pada is not None,
        # Hanya berarti untuk pesan KELUAR: pengirim ingin tahu sudah dibaca
        # atau belum. Untuk pesan masuk nilainya tidak dipakai UI.
        "sudah_dibaca": pesan.dibaca_pada is not None,
        "balasan_ke": dikutip,
        "reaksi": reaksi or [],
        # Dipakai UI untuk menarik garis "pesan belum dibaca" di posisi yang
        # tepat. WAJIB dihitung SEBELUM percakapan ditandai terbaca: sesudah
        # UPDATE jalan, semuanya sudah terbaca dan garisnya tidak akan pernah
        # muncul untuk siapa pun.
        "baru": pesan.dibaca_pada is None and pesan.pengirim_id != saya_id,
    }


def _peta_belum_dibaca(daftar_langganan):
    """Jumlah belum dibaca per ruang, dalam SATU kueri.

    Seluruh langganan yang masuk harus milik SATU orang, dan pemanggilnya memang
    selalu begitu. Versi naifnya satu COUNT per ruang, padahal daftar percakapan
    dan lencana sidebar ditarik dari hampir setiap halaman: untuk orang yang ikut
    dua puluh kanal, itu dua puluh kali bolak-balik ke database tiap penggambaran.
    """
    if not daftar_langganan:
        return {}

    saya_id = daftar_langganan[0].user_id
    kondisi = Q()
    for langganan in daftar_langganan:
        satu = Q(ruang_id=langganan.ruang_id)
        if langganan.dibaca_sampai is not None:
            satu &= Q(created_at__gt=langganan.dibaca_sampai)
        kondisi |= satu

    baris = (
        PesanLangsung.objects.filter(kondisi)
        .exclude(pengirim_id=saya_id)
        .values_list("ruang_id")
        .annotate(jumlah=Count("id"))
    )
    return {ruang_id: jumlah for ruang_id, jumlah in baris}


def _lawan_bicara(ruang, saya_id):
    """Id lawan bicara sebuah DM, dibaca dari kunci_dm. None untuk kanal."""
    if ruang.tipe != Ruang.Tipe.DM or not ruang.kunci_dm:
        return None
    dua = ruang.kunci_dm.split(":")
    return next((x for x in dua if x != str(saya_id)), dua[0])


def _bentuk_ruang(ruang, saya_id, belum_dibaca=0, ikut=True):
    return {
        "id": str(ruang.id),
        "tipe": ruang.tipe,
        "nama": ruang.nama,
        "topik": ruang.topik,
        # Tetap dikirim untuk DM supaya peramban yang sudah beredar tidak perlu
        # tahu apa pun tentang ruang untuk bisa membuka percakapan lama.
        "lawan_bicara": _lawan_bicara(ruang, saya_id),
        "pesan_terakhir_pada": ruang.pesan_terakhir_pada,
        "belum_dibaca": belum_dibaca,
        "ikut": ikut,
    }


class ChatConversationsEndpoint(BaseAPIView):
    """Semua ruang yang saya ikuti: DM maupun kanal, urut pesan terakhir.

    Versi lama menjalankan DUA kueri DISTINCT ON, satu per arah pesan, lalu
    menggabungkannya di Python, karena tidak ada tabel yang menyimpan "siapa
    berbicara dengan siapa". Sekarang Langganan menyimpannya, jadi seluruh
    akrobat itu hilang dan kanal ikut terlayani tanpa cabang kode kedua.
    """

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        daftar = list(
            Langganan.objects.filter(ruang__workspace__slug=slug, user=request.user)
            .select_related("ruang")
            .order_by("-ruang__pesan_terakhir_pada")
        )
        if not daftar:
            return Response([], status=status.HTTP_200_OK)

        belum = _peta_belum_dibaca(daftar)

        # Pesan terakhir tiap ruang, satu kueri untuk semuanya.
        terakhir = {}
        for pesan in (
            PesanLangsung.objects.filter(ruang_id__in=[l.ruang_id for l in daftar])
            .order_by("ruang_id", "-created_at")
            .distinct("ruang_id")
        ):
            terakhir[pesan.ruang_id] = pesan

        hasil = []
        for langganan in daftar:
            ruang = langganan.ruang
            # Ruang yang belum berisi pesan apa pun tetap ditampilkan kalau itu
            # kanal: orang perlu melihat kanal yang baru saja dibuatnya. DM
            # kosong disembunyikan, karena ia lahir hanya dari orang yang
            # membuka profil lalu menutupnya lagi tanpa menulis apa pun.
            pesan = terakhir.get(ruang.id)
            if pesan is None and ruang.tipe == Ruang.Tipe.DM:
                continue

            baris = _bentuk_ruang(ruang, request.user.id, belum.get(ruang.id, 0))
            baris["isi"] = pesan.isi if pesan else ""
            baris["dari_saya"] = bool(pesan and pesan.pengirim_id == request.user.id)
            baris["created_at"] = pesan.created_at if pesan else ruang.created_at
            hasil.append(baris)

        return Response(hasil, status=status.HTTP_200_OK)


class ChatCariEndpoint(BaseAPIView):
    """Cari isi pesan di SELURUH percakapan milik sendiri.

    Hanya pesan yang kita kirim atau terima. Tidak ada jalan untuk mencari di
    obrolan orang lain, dan itu bukan kelalaian melainkan batas yang sama dengan
    seluruh fitur ini.
    """

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        kunci = (request.query_params.get("q") or "").strip()
        # Dua huruf terlalu pendek: hasilnya hampir seluruh isi kotak masuk, dan
        # itu bukan pencarian, cuma pemborosan.
        if len(kunci) < 3:
            return Response(
                {"error": "Kata kunci minimal 3 huruf."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Saringannya kini "ruang yang saya ikuti", bukan "pesan yang saya kirim
        # atau terima". Dua alasan: pesan kanal tidak punya penerima tunggal jadi
        # saringan lama membuatnya tidak pernah ketemu, dan berlangganan adalah
        # satu-satunya penanda hak baca yang dipakai endpoint lain. Menyatukan
        # keduanya berarti tidak ada dua definisi "boleh lihat" yang bisa
        # melenceng satu sama lain.
        ruang_saya = Langganan.objects.filter(
            ruang__workspace__slug=slug, user=request.user
        ).values_list("ruang_id", flat=True)

        hasil = (
            PesanLangsung.objects.filter(ruang_id__in=ruang_saya)
            .filter(isi__icontains=kunci)
            .order_by("-created_at")[:JUMLAH_HASIL_CARI]
        )
        return Response(
            [
                {
                    "id": str(p.id),
                    "isi": p.isi,
                    "created_at": p.created_at,
                    "dari_saya": p.pengirim_id == request.user.id,
                    # Ruang tempat pesan ini berada, supaya UI bisa langsung
                    # membukanya tanpa menebak dari arah pesan.
                    "ruang": str(p.ruang_id),
                    # Tetap dikirim untuk DM demi peramban yang sudah beredar.
                    # Kosong untuk kanal, karena tidak ada lawan tunggal.
                    "lawan_bicara": (
                        str(p.penerima_id if p.pengirim_id == request.user.id else p.pengirim_id)
                        if p.penerima_id
                        else None
                    ),
                }
                for p in hasil
            ],
            status=status.HTTP_200_OK,
        )


class ChatUnreadEndpoint(BaseAPIView):
    """Jumlah pesan belum dibaca di seluruh workspace, untuk lencana sidebar.

    Endpoint terpisah dari daftar percakapan, dan itu bukan duplikasi: lencana
    ini hidup di sidebar, jadi ikut ditarik dari SETIAP halaman. Memakai
    endpoint percakapan untuk itu berarti membawa isi pesan terakhir setiap
    lawan bicara ke tiap halaman cuma untuk menampilkan satu angka.

    Satu COUNT yang seluruhnya dilayani indeks `dm_penerima_dibaca_idx`.
    """

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        daftar = list(Langganan.objects.filter(ruang__workspace__slug=slug, user=request.user))
        jumlah = sum(_peta_belum_dibaca(daftar).values())
        return Response({"jumlah": jumlah}, status=status.HTTP_200_OK)


class ChatPesanEndpoint(BaseAPIView):
    """Sunting, hapus, dan reaksi pada SATU pesan."""

    permission_classes = [WorkspaceEntityPermission]

    def _pesan_saya(self, request, slug, pesan_id):
        """Pesan yang boleh DIUBAH: hanya milik pengirimnya sendiri.

        Pemilik workspace sengaja TIDAK diberi jalan masuk ke sini. Mengawasi
        adalah membaca; mengubah tulisan orang lain adalah hal yang sama sekali
        berbeda, dan tidak pernah diminta.
        """
        return PesanLangsung.objects.filter(id=pesan_id, workspace__slug=slug, pengirim=request.user).first()

    def patch(self, request, slug, pesan_id):
        pesan = self._pesan_saya(request, slug, pesan_id)
        if pesan is None:
            return Response({"error": "Bukan pesan Anda."}, status=status.HTTP_404_NOT_FOUND)

        isi = (request.data.get("isi") or "").strip()
        if not isi:
            return Response({"error": "Pesan kosong."}, status=status.HTTP_400_BAD_REQUEST)
        if len(isi) > BATAS_ISI:
            return Response(
                {"error": f"Pesan terlalu panjang, maksimum {BATAS_ISI} karakter."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pesan.isi = isi
        pesan.disunting_pada = timezone.now()
        pesan.save(update_fields=["isi", "disunting_pada", "updated_at"])
        siarkan(pesan.ruang_id, "sunting", request.user.id)
        peta = _peta_lampiran([pesan.id], slug)
        return Response(
            _bentuk(pesan, slug, request.user.id, peta.get(str(pesan.id))),
            status=status.HTTP_200_OK,
        )

    def delete(self, request, slug, pesan_id):
        pesan = self._pesan_saya(request, slug, pesan_id)
        if pesan is None:
            return Response({"error": "Bukan pesan Anda."}, status=status.HTTP_404_NOT_FOUND)
        # Soft delete: barisnya tetap ada untuk audit, tapi hilang dari semua
        # daftar karena manager bawaan menyaring deleted_at.
        ruang_id = pesan.ruang_id
        pesan.delete()
        siarkan(ruang_id, "hapus", request.user.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatReaksiEndpoint(BaseAPIView):
    """Tambah atau buang satu reaksi emoji pada pesan di percakapan sendiri."""

    permission_classes = [WorkspaceEntityPermission]

    def post(self, request, slug, pesan_id):
        emoji = (request.data.get("emoji") or "").strip()
        if not emoji or len(emoji) > 32:
            return Response({"error": "Emoji tidak sah."}, status=status.HTTP_400_BAD_REQUEST)

        # Boleh bereaksi hanya pada percakapan yang kita ikuti, bukan pada
        # sembarang id pesan yang ditebak.
        pesan = PesanLangsung.objects.filter(id=pesan_id, workspace__slug=slug).filter(
            Q(pengirim=request.user) | Q(penerima=request.user)
        ).first()
        if pesan is None:
            return Response({"error": "Pesan tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        ada = ReaksiPesan.objects.filter(pesan=pesan, user=request.user, emoji=emoji).first()
        if ada:
            # Klik kedua pada emoji yang sama = membatalkan. Satu endpoint untuk
            # dua arah, karena dari sisi UI ini memang satu tombol.
            ada.delete(soft=False)
            siarkan(pesan.ruang_id, "reaksi", request.user.id)
            return Response({"aktif": False}, status=status.HTTP_200_OK)

        ReaksiPesan.objects.create(pesan=pesan, user=request.user, emoji=emoji)
        siarkan(pesan.ruang_id, "reaksi", request.user.id)
        return Response({"aktif": True}, status=status.HTTP_201_CREATED)


def boleh_lihat_lampiran(user, aset, slug) -> bool:
    """Penjaga tunggal lampiran obrolan.

    Satu fungsi, dipakai endpoint Obrolan MAUPUN endpoint unduhan bawaan, supaya
    tidak ada pintu belakang. Endpoint unduhan workspace bawaan melayani setiap
    anggota untuk aset apa pun; tanpa penjaga ini, id lampiran yang bocor sekali
    bisa dibuka siapa saja yang punya akun.

    Parameter `slug` dipertahankan walau tidak lagi dipakai: pemanggilnya ada di
    berkas upstream (`asset/v2.py`), dan mengubah tanda tangannya menambah
    permukaan konflik tiap kali upstream disinkronkan.
    """
    if aset.entity_type != FileAsset.EntityTypeContext.CHAT_ATTACHMENT:
        return True  # bukan urusan fungsi ini
    if not aset.entity_identifier:
        # Belum menempel ke pesan mana pun: hanya pengunggahnya.
        return aset.created_by_id == user.id
    pesan = PesanLangsung.objects.filter(id=aset.entity_identifier).first()
    if pesan is None:
        return False
    # HANYA pengirim dan penerima. Pemilik workspace sengaja TIDAK ikut:
    # kewenangan membaca obrolan orang lain ditarik 13 Agt 2026 atas permintaan
    # pemiliknya sendiri, dan lampiran adalah isi obrolan juga.
    return user.id in (pesan.pengirim_id, pesan.penerima_id)


class ChatLampiranEndpoint(BaseAPIView):
    """Unduh satu lampiran obrolan, hanya untuk pihak yang berhak."""

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug, asset_id):
        aset = FileAsset.objects.filter(
            id=asset_id,
            workspace__slug=slug,
            entity_type=FileAsset.EntityTypeContext.CHAT_ATTACHMENT,
            is_uploaded=True,
        ).first()
        if aset is None:
            return Response({"error": "Lampiran tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        if not boleh_lihat_lampiran(request.user, aset, slug):
            logger.warning(
                "lampiran-chat: %s DITOLAK membuka lampiran %s",
                request.user.email,
                asset_id,
            )
            return Response({"error": "Bukan lampiran Anda."}, status=status.HTTP_403_FORBIDDEN)

        storage = S3Storage(request=request)
        # `inline` supaya gambar dan video tampil di dalam percakapan, bukan
        # terunduh sebagai berkas tiap kali dilihat.
        signed = storage.generate_presigned_url(
            object_name=aset.asset.name,
            disposition="inline",
            filename=aset.attributes.get("name", "lampiran"),
        )
        return HttpResponseRedirect(signed)


def _urai_sebelum(request):
    """Baca kursor penggulungan. Kembalikan (batas, respons_galat)."""
    sebelum = request.query_params.get("sebelum")
    if not sebelum:
        return None, None
    batas = parse_datetime(sebelum)
    if batas is None:
        # Diurai eksplisit. Kalau nilainya diserahkan langsung ke filter, format
        # yang tidak dikenal keluar sebagai 400 mentah dari Django tanpa
        # keterangan apa pun, dan yang memanggil tidak tahu apa yang salah.
        return None, Response(
            {"error": "Parameter `sebelum` harus waktu ISO 8601."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return batas, None


def _muat_isi_ruang(request, slug, ruang, batas=None):
    """Isi satu ruang, urut waktu, lengkap dengan lampiran, reaksi, dan kutipan.

    Satu fungsi untuk DM maupun kanal. Menyalinnya jadi dua berarti tiap
    perbaikan tampilan pesan harus diingat dua kali, dan yang terlupa baru
    ketahuan dari laporan pengguna.
    """
    antara = PesanLangsung.objects.filter(ruang=ruang)
    if batas is not None:
        antara = antara.filter(created_at__lt=batas)

    # Diambil menurun supaya yang terpotong adalah pesan TERTUA, lalu dibalik
    # supaya peramban menerimanya urut waktu.
    urut = list(reversed(list(antara.order_by("-created_at")[:JUMLAH_PESAN])))
    peta = _peta_lampiran([p.id for p in urut], slug)
    reaksi = _peta_reaksi([p.id for p in urut])
    kutipan = _peta_kutipan(urut)
    return [
        _bentuk(
            p,
            slug,
            request.user.id,
            peta.get(str(p.id)),
            reaksi.get(str(p.id)),
            kutipan.get(str(p.balasan_ke_id)) if p.balasan_ke_id else None,
        )
        for p in urut
    ]


def _kirim_ke_ruang(request, slug, ruang, penerima_id=None):
    """Tulis satu pesan ke ruang. Kembalikan Response, sukses maupun gagal.

    Semua pemeriksaan isi ada di sini dan hanya di sini, supaya kanal tidak bisa
    dipakai sebagai jalan memutar batas yang berlaku di DM.
    """
    isi = (request.data.get("isi") or "").strip()
    lampiran_ids = request.data.get("lampiran") or []

    if not isinstance(lampiran_ids, list) or len(lampiran_ids) > BATAS_LAMPIRAN:
        return Response(
            {"error": "Lampiran maksimum %s berkas." % BATAS_LAMPIRAN},
            status=status.HTTP_400_BAD_REQUEST,
        )
    # Kosong hanya ditolak kalau lampirannya juga kosong. Mengirim gambar tanpa
    # keterangan apa pun itu hal yang wajar dilakukan orang.
    if not isi and not lampiran_ids:
        return Response({"error": "Pesan kosong."}, status=status.HTTP_400_BAD_REQUEST)
    if len(isi) > BATAS_ISI:
        return Response(
            {"error": "Pesan terlalu panjang, maksimum %s karakter." % BATAS_ISI},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Yang boleh dikutip hanya pesan dari ruang INI. Tanpa saringan itu, id pesan
    # ruang lain bisa dikutip dan cuplikannya ikut terbaca oleh yang tidak berhak.
    balasan_ke_id = request.data.get("balasan_ke")
    if balasan_ke_id and not PesanLangsung.objects.filter(id=balasan_ke_id, ruang=ruang).exists():
        balasan_ke_id = None

    pesan = PesanLangsung.objects.create(
        workspace_id=ruang.workspace_id,
        ruang=ruang,
        pengirim=request.user,
        penerima_id=penerima_id,
        isi=isi,
        balasan_ke_id=balasan_ke_id,
    )

    # Denormalisasi yang membuat daftar percakapan bisa diurutkan tanpa subquery.
    Ruang.objects.filter(id=ruang.id).update(pesan_terakhir_pada=pesan.created_at)

    # Beri tahu yang sedang membuka ruang ini. Ditaruh SESUDAH pesan tersimpan:
    # siaran yang mendahului commit membuat peramban menarik ulang lalu tidak
    # menemukan apa-apa, dan pesannya baru muncul pada penarikan berikutnya.
    siarkan(ruang.id, "pesan", request.user.id)

    if lampiran_ids:
        # Yang boleh ditempel HANYA berkas yang diunggah orang ini sendiri, di
        # workspace ini, bertipe lampiran obrolan, dan belum menempel di pesan
        # mana pun. Tanpa keempatnya, id berkas milik orang lain bisa
        # ditempelkan ke pesan sendiri lalu isinya ikut terbaca.
        terpakai = FileAsset.objects.filter(
            id__in=lampiran_ids,
            workspace__slug=slug,
            created_by=request.user,
            entity_type=FileAsset.EntityTypeContext.CHAT_ATTACHMENT,
            entity_identifier__isnull=True,
        ).update(entity_identifier=str(pesan.id))
        if terpakai != len(lampiran_ids):
            logger.warning(
                "lampiran-chat: %s mengirim %s id, hanya %s yang sah",
                request.user.email,
                len(lampiran_ids),
                terpakai,
            )

    peta = _peta_lampiran([pesan.id], slug)
    kutipan = _peta_kutipan([pesan])
    return Response(
        _bentuk(
            pesan,
            slug,
            request.user.id,
            peta.get(str(pesan.id)),
            None,
            kutipan.get(str(pesan.balasan_ke_id)) if pesan.balasan_ke_id else None,
        ),
        status=status.HTTP_201_CREATED,
    )


class ChatThreadEndpoint(BaseAPIView):
    """Percakapan dengan satu orang. Pintu masuk DM ke mesin ruang.

    Endpoint ini sengaja dipertahankan walau isinya sekarang cuma menerjemahkan
    "siapa lawan bicaranya" jadi "ruang mana", lalu menyerahkannya. Peramban dan
    tautan yang sudah beredar memakai bentuk URL ini, dan mengubahnya berarti
    memutus percakapan yang sedang dibuka orang tepat saat deploy berjalan.
    """

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug, user_id):
        batas, galat = _urai_sebelum(request)
        if galat:
            return galat

        ruang = _ruang_dm(request, slug, user_id)
        if ruang is None:
            return Response(
                {"error": "Orang itu bukan anggota aktif workspace ini."},
                status=status.HTTP_404_NOT_FOUND,
            )

        isi = _muat_isi_ruang(request, slug, ruang, batas)

        # Membuka percakapan berarti membacanya. Dua penanda digeser sekaligus
        # dan keduanya perlu: `dibaca_pada` adalah tanda terima yang dilihat
        # pengirim, `dibaca_sampai` adalah yang dipakai lencana dan kanal.
        # WAJIB sesudah `_muat_isi_ruang`, karena medan `baru` dihitung dari
        # keadaan sebelum dibaca. Membalik urutannya membuat garis "pesan belum
        # dibaca" tidak pernah muncul untuk siapa pun.
        PesanLangsung.objects.filter(
            ruang=ruang, pengirim_id=user_id, penerima=request.user, dibaca_pada__isnull=True
        ).update(dibaca_pada=timezone.now())

        langganan = _langganan(request.user.id, ruang)
        if langganan is not None:
            _tandai_terbaca(langganan, ruang.pesan_terakhir_pada)

        return Response(isi, status=status.HTTP_200_OK)

    def post(self, request, slug, user_id):
        if str(user_id) == str(request.user.id):
            return Response(
                {"error": "Tidak bisa mengirim pesan ke diri sendiri."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Penerima WAJIB diperiksa di sini, bukan cuma di UI. Tanpa ini, id siapa
        # pun yang ditebak dari URL bisa dikirimi pesan, termasuk orang dari
        # workspace lain di instance yang sama.
        ruang = _ruang_dm(request, slug, user_id)
        if ruang is None:
            return Response(
                {"error": "Orang itu bukan anggota aktif workspace ini."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return _kirim_ke_ruang(request, slug, ruang, penerima_id=user_id)


class ChatIceEndpoint(BaseAPIView):
    """Server ICE untuk panggilan, berikut kredensial TURN berumur pendek.

    Disajikan dari server, BUKAN ditanam saat build. Kredensial TURN berumur
    pendek dan alamatnya bisa berubah; kalau nilainya ikut dibundel ke berkas
    JavaScript, setiap penggantian menuntut build ulang dan deploy penuh.
    """

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        return Response({"iceServers": daftar_ice(request.user.id)}, status=status.HTTP_200_OK)


class ChatPanggilanTokenEndpoint(BaseAPIView):
    """Token masuk ruang panggilan LiveKit.

    Hak panggil = hak baca. Yang boleh membuka isi ruang boleh meneleponnya, dan
    itu diperiksa lewat Langganan yang sama seperti seluruh fitur ini. Definisi
    kedua berarti dua aturan yang harus dijaga sinkron, dan yang satu pasti
    ketinggalan.
    """

    permission_classes = [WorkspaceEntityPermission]

    def post(self, request, slug, ruang_id):
        ruang = Ruang.objects.filter(id=ruang_id, workspace__slug=slug).first()
        if ruang is None or _langganan(request.user.id, ruang) is None:
            return Response({"error": "Ruang tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        if not konfigurasi_ada() or not url_livekit():
            # Dijawab jelas, bukan token kosong. Kegagalan konfigurasi yang
            # menyamar jadi kegagalan jaringan adalah yang paling lama dicari.
            return Response(
                {"error": "Panggilan belum dikonfigurasi di server ini."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        logger.info("panggilan: %s masuk ruang %s", request.user.email, ruang_id)
        return Response(
            {
                "url": url_livekit(),
                "token": token_panggilan(request.user, ruang_id),
                "ruang": nama_ruang(ruang_id),
            },
            status=status.HTTP_200_OK,
        )


class ChatRuangEndpoint(BaseAPIView):
    """Daftar kanal, dan pembuatan kanal baru."""

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        milik_saya = set(
            Langganan.objects.filter(ruang__workspace__slug=slug, user=request.user).values_list(
                "ruang_id", flat=True
            )
        )
        # Kanal publik selalu terlihat supaya orang bisa menemukan lalu bergabung.
        # Kanal privat hanya terlihat oleh yang sudah di dalamnya; menampilkan
        # namanya saja sudah membocorkan bahwa ada obrolan tertutup soal sesuatu.
        ruang = (
            Ruang.objects.filter(workspace__slug=slug)
            .exclude(tipe=Ruang.Tipe.DM)
            .filter(Q(tipe=Ruang.Tipe.KANAL) | Q(id__in=milik_saya))
            .order_by("nama")
        )
        daftar = list(ruang)
        langganan_saya = list(
            Langganan.objects.filter(user=request.user, ruang_id__in=[r.id for r in daftar])
        )
        belum = _peta_belum_dibaca(langganan_saya)

        return Response(
            [
                _bentuk_ruang(r, request.user.id, belum.get(r.id, 0), ikut=r.id in milik_saya)
                for r in daftar
            ],
            status=status.HTTP_200_OK,
        )

    def post(self, request, slug):
        nama = (request.data.get("nama") or "").strip()
        tipe = request.data.get("tipe") or Ruang.Tipe.KANAL
        topik = (request.data.get("topik") or "").strip()

        if not nama:
            return Response({"error": "Nama kanal wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)
        if len(nama) > BATAS_NAMA_RUANG:
            return Response(
                {"error": "Nama kanal maksimum %s karakter." % BATAS_NAMA_RUANG},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # DM sengaja tidak bisa dibuat lewat sini. Ia lahir sendiri saat orang
        # membuka percakapan, dan membiarkan dua jalur pembuatan berarti ada
        # jalan membuat DM tanpa kunci_dm yang benar.
        if tipe not in (Ruang.Tipe.KANAL, Ruang.Tipe.PRIVAT):
            return Response(
                {"error": "Tipe kanal harus `kanal` atau `privat`."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workspace = Workspace.objects.filter(slug=slug).first()
        if workspace is None:
            return Response({"error": "Workspace tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        # Nama kembar bikin orang salah masuk kanal. Diperiksa case-insensitive
        # karena "Umum" dan "umum" sama saja bagi yang membacanya.
        if (
            Ruang.objects.filter(workspace=workspace, nama__iexact=nama)
            .exclude(tipe=Ruang.Tipe.DM)
            .exists()
        ):
            return Response(
                {"error": "Sudah ada kanal dengan nama itu."}, status=status.HTTP_400_BAD_REQUEST
            )

        ruang = Ruang.objects.create(workspace=workspace, tipe=tipe, nama=nama, topik=topik)
        # Pembuatnya langsung menjadi anggota. Kanal tanpa satu pun anggota tidak
        # akan muncul di daftar percakapan siapa pun, termasuk yang membuatnya.
        Langganan.objects.create(ruang=ruang, user=request.user)

        logger.info("kanal-chat: %s membuat kanal %s (%s)", request.user.email, nama, tipe)
        return Response(_bentuk_ruang(ruang, request.user.id), status=status.HTTP_201_CREATED)


class ChatRuangThreadEndpoint(BaseAPIView):
    """Isi satu ruang dan pengiriman pesan ke dalamnya.

    Berlaku untuk kanal MAUPUN DM. Peramban boleh memakai jalur ini untuk
    keduanya begitu ia tahu id ruangnya; jalur `chat/<user_id>/` tetap ada untuk
    yang belum tahu.
    """

    permission_classes = [WorkspaceEntityPermission]

    def _ruang_saya(self, request, slug, ruang_id):
        """Ruang beserta langganan saya, atau (None, None) kalau tidak berhak.

        Berlangganan adalah SATU-SATUNYA syarat baca, termasuk untuk kanal
        publik. Menambahkan pengecualian "publik boleh dibaca tanpa gabung"
        berarti dua definisi hak baca yang harus dijaga sinkron selamanya.
        """
        ruang = Ruang.objects.filter(id=ruang_id, workspace__slug=slug).first()
        if ruang is None:
            return None, None
        return ruang, _langganan(request.user.id, ruang)

    def get(self, request, slug, ruang_id):
        batas, galat = _urai_sebelum(request)
        if galat:
            return galat

        ruang, langganan = self._ruang_saya(request, slug, ruang_id)
        if ruang is None or langganan is None:
            return Response({"error": "Ruang tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        isi = _muat_isi_ruang(request, slug, ruang, batas)

        # Untuk DM, tanda terima ikut digeser supaya pengirimnya melihat
        # pesannya sudah dibaca, sama seperti lewat jalur `chat/<user_id>/`.
        if ruang.tipe == Ruang.Tipe.DM:
            PesanLangsung.objects.filter(
                ruang=ruang, penerima=request.user, dibaca_pada__isnull=True
            ).update(dibaca_pada=timezone.now())

        _tandai_terbaca(langganan, ruang.pesan_terakhir_pada)
        return Response(isi, status=status.HTTP_200_OK)

    def post(self, request, slug, ruang_id):
        ruang, langganan = self._ruang_saya(request, slug, ruang_id)
        if ruang is None or langganan is None:
            return Response({"error": "Ruang tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        # DM tetap membawa `penerima` supaya tanda terima, email pemberitahuan,
        # dan penjaga lampiran terus bekerja. Kanal tidak punya penerima tunggal.
        penerima_id = _lawan_bicara(ruang, request.user.id) if ruang.tipe == Ruang.Tipe.DM else None
        return _kirim_ke_ruang(request, slug, ruang, penerima_id=penerima_id)


class ChatGabungEndpoint(BaseAPIView):
    """Gabung ke kanal, atau keluar darinya."""

    permission_classes = [WorkspaceEntityPermission]

    def post(self, request, slug, ruang_id):
        ruang = Ruang.objects.filter(id=ruang_id, workspace__slug=slug).first()
        if ruang is None:
            return Response({"error": "Ruang tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        if ruang.tipe != Ruang.Tipe.KANAL:
            # DM tidak bisa dimasuki, dan kanal privat hanya lewat undangan
            # anggotanya. Tanpa batas ini, id kanal privat yang bocor sekali
            # cukup untuk membaca seluruh isinya.
            return Response(
                {"error": "Hanya kanal publik yang bisa dimasuki sendiri."},
                status=status.HTTP_403_FORBIDDEN,
            )

        _, dibuat = Langganan.objects.get_or_create(ruang=ruang, user=request.user)
        return Response(
            {"ikut": True},
            status=status.HTTP_201_CREATED if dibuat else status.HTTP_200_OK,
        )

    def delete(self, request, slug, ruang_id):
        ruang = Ruang.objects.filter(id=ruang_id, workspace__slug=slug).first()
        if ruang is None:
            return Response({"error": "Ruang tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        if ruang.tipe == Ruang.Tipe.DM:
            return Response(
                {"error": "Percakapan berdua tidak bisa ditinggalkan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        langganan = _langganan(request.user.id, ruang)
        if langganan is None:
            return Response({"error": "Anda bukan anggota kanal ini."}, status=status.HTTP_404_NOT_FOUND)

        # Hapus lunak, jadi kalau bergabung lagi nanti barisnya baru dan penanda
        # bacanya mulai bersih. Riwayat kanal sendiri tidak disentuh.
        langganan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatAnggotaEndpoint(BaseAPIView):
    """Siapa saja di dalam kanal, dan menambahkan orang ke dalamnya."""

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug, ruang_id):
        ruang = Ruang.objects.filter(id=ruang_id, workspace__slug=slug).first()
        if ruang is None or _langganan(request.user.id, ruang) is None:
            return Response({"error": "Ruang tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            [
                str(user_id)
                for user_id in Langganan.objects.filter(ruang=ruang).values_list("user_id", flat=True)
            ],
            status=status.HTTP_200_OK,
        )

    def post(self, request, slug, ruang_id):
        ruang = Ruang.objects.filter(id=ruang_id, workspace__slug=slug).first()
        # Yang mengundang wajib sudah di dalam. Inilah satu-satunya jalan masuk
        # ke kanal privat, jadi penjaganya ada di sini.
        if ruang is None or _langganan(request.user.id, ruang) is None:
            return Response({"error": "Ruang tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        if ruang.tipe == Ruang.Tipe.DM:
            return Response(
                {"error": "Percakapan berdua tidak bisa ditambahi orang."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = request.data.get("user")
        if not user_id:
            return Response({"error": "Pilih orang yang mau ditambahkan."}, status=status.HTTP_400_BAD_REQUEST)

        # Diperiksa di server, bukan cuma di UI: tanpa ini id siapa pun yang
        # ditebak bisa dimasukkan ke kanal, termasuk orang dari workspace lain.
        if not WorkspaceMember.objects.filter(
            workspace__slug=slug, member_id=user_id, is_active=True
        ).exists():
            return Response(
                {"error": "Orang itu bukan anggota aktif workspace ini."},
                status=status.HTTP_404_NOT_FOUND,
            )

        _, dibuat = Langganan.objects.get_or_create(ruang=ruang, user_id=user_id)
        return Response(
            {"ditambahkan": dibuat},
            status=status.HTTP_201_CREATED if dibuat else status.HTTP_200_OK,
        )
