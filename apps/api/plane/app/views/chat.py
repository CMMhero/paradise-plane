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
import uuid
from datetime import timedelta

# Django imports
from django.db import transaction
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
from plane.utils.inbox_chat import catat_pesan_dm, tandai_chat_terbaca
from plane.utils.livekit import konfigurasi_ada, nama_ruang, token_panggilan, url_livekit
from plane.utils.obrolan_siaran import siarkan
from plane.utils.kanal_sistem import adalah_admin_workspace, boleh_kirim, ikutkan_jika_belum
from plane.utils.kartu_obrolan import kartu_disebut_di_obrolan
from plane.utils.rujukan_obrolan import kanal_privat_milik, samarkan, saring_kanal, saring_tugas
from plane.utils.saklar_instance import (
    CHAT_ATTACHMENTS_MAX,
    CHAT_DELETE_WINDOW_HOURS,
    CHAT_EDIT_WINDOW_HOURS,
    CHAT_MESSAGE_MAX_LENGTH,
    setelan_angka,
)
from plane.db.models import KUNCI_PENGUMUMAN

# Module imports
from plane.app.permissions import WorkspaceEntityPermission
from plane.db.models import (
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

# Berapa orang boleh disebut dalam satu pesan. Lebih dari ini sudah pengumuman.
BATAS_SEBUT = 20


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
        orang = baris.setdefault(r["emoji"], [])
        # Baris kembar sisa balapan lama (lihat ChatReaksiEndpoint) tidak boleh
        # menghitung satu orang dua kali.
        if str(r["user_id"]) not in orang:
            orang.append(str(r["user_id"]))
    return {
        pid: [{"emoji": e, "orang": orang} for e, orang in emoji.items()]
        for pid, emoji in peta.items()
    }


def _peta_kutipan(pesan_list, saya_id=None):
    """Cuplikan pesan yang dibalas, satu kueri untuk semuanya.

    KEP-91: cuplikan disamarkan untuk `saya_id` SEBELUM dipotong, supaya nama
    kanal privat tidak lolos lewat kutipan maupun terpotong setengah.
    """
    induk_ids = {p.balasan_ke_id for p in pesan_list if p.balasan_ke_id}
    if not induk_ids:
        return {}
    # all_objects: kutipan ke pesan yang sudah dihapus tetap ada, isinya dikosongkan.
    induk = list(
        PesanLangsung.all_objects.filter(id__in=induk_ids).values("id", "isi", "muatan", "pengirim_id", "deleted_at")
    )
    privat = kanal_privat_milik([saya_id], [i["muatan"] for i in induk]).get(str(saya_id), set())
    return {
        str(i["id"]): {
            "id": str(i["id"]),
            "pengirim": str(i["pengirim_id"]) if i["pengirim_id"] else "",
            # Dipotong di server: yang dibutuhkan UI cuma cuplikan, dan
            # mengirim pesan panjang dua kali membengkakkan tiap muatan.
            "isi": "" if i["deleted_at"] else (samarkan(i["isi"], i["muatan"], saya_id, boleh=privat)[0] or "")[:120],
            "dihapus": i["deleted_at"] is not None,
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


def _bentuk(pesan, slug, saya_id=None, lampiran=None, reaksi=None, dikutip=None, privat=None):
    if pesan.deleted_at is not None:
        # Batu nisan: pesan dihapus tetap menempati tempatnya di percakapan,
        # tapi tanpa isi, lampiran, reaksi, kutipan, atau data kartu. Penyaringan
        # DI SINI (satu-satunya pembentuk muatan pesan) menjamin tak ada jalur
        # yang bocor. `pengirim` dan waktu tetap, supaya susunan gelembung sama.
        return {
            "id": str(pesan.id),
            "pengirim": str(pesan.pengirim_id) if pesan.pengirim_id else None,
            "isi": "",
            "jenis": "teks",
            "muatan": {},
            "created_at": pesan.created_at,
            "lampiran": [],
            "disunting": False,
            "sudah_dibaca": pesan.dibaca_pada is not None,
            "balasan_ke": None,
            "reaksi": [],
            "baru": False,
            "dihapus": True,
            "disematkan": False,
            "disematkan_pada": None,
            "disematkan_oleh": None,
        }
    # KEP-91: rujukan #kanal-privat disamarkan bagi yang bukan anggotanya.
    # `privat` = keanggotaan yang sudah dihitung pemanggil massal, kalau ada.
    isi, muatan = samarkan(pesan.isi, pesan.muatan or {}, saya_id, boleh=privat)
    return {
        "dihapus": False,
        "id": str(pesan.id),
        # Kosong = pesan sistem ("Paradise"): catatan rilis dan kartu kabar.
        "pengirim": str(pesan.pengirim_id) if pesan.pengirim_id else None,
        "isi": isi,
        # Kartu: `jenis` selain "teks" dirender peramban dari `muatan`.
        "jenis": pesan.jenis,
        "muatan": muatan or {},
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
        # Sematan berlaku untuk seluruh ruang (lihat ChatSematanEndpoint).
        "disematkan": pesan.disematkan_pada is not None,
        "disematkan_pada": pesan.disematkan_pada,
        "disematkan_oleh": str(pesan.disematkan_oleh_id) if pesan.disematkan_oleh_id else None,
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


class _HakTulis:
    """`boleh_kirim` per ruang dengan status admin dihitung paling banyak SEKALI
    per permintaan, bukan per baris daftar kanal."""

    def __init__(self, user):
        self.user = user
        self._admin = {}

    def __call__(self, ruang) -> bool:
        if not ruang.sistem:
            return True
        if ruang.workspace_id not in self._admin:
            self._admin[ruang.workspace_id] = adalah_admin_workspace(self.user, ruang.workspace_id)
        return boleh_kirim(ruang, self.user, admin=self._admin[ruang.workspace_id])


def _bentuk_ruang(ruang, saya_id, belum_dibaca=0, ikut=True, boleh_tulis=True):
    return {
        # Kanal sistem: tanpa tombol keluar/ganti nama, berlencana "System".
        # `kunci_sistem` = pengumuman | changelog | kabar:<user_id>.
        "sistem": ruang.sistem,
        "kunci_sistem": ruang.kunci_sistem,
        "boleh_kirim": boleh_tulis,
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
        # Jaring malas kanal sistem: menutup jalur pendaftaran anggota yang tidak
        # memancarkan signal (bulk_create undangan). Satu COUNT kalau sudah beres.
        ws_id = Workspace.objects.filter(slug=slug).values_list("id", flat=True).first()
        if ws_id:
            ikutkan_jika_belum(ws_id, request.user.id)

        daftar = list(
            Langganan.objects.filter(ruang__workspace__slug=slug, user=request.user)
            .select_related("ruang")
            .order_by("-ruang__pesan_terakhir_pada")
        )
        if not daftar:
            return Response([], status=status.HTTP_200_OK)

        belum = _peta_belum_dibaca(daftar)
        hak_tulis = _HakTulis(request.user)

        # Pesan terakhir tiap ruang, satu kueri untuk semuanya.
        terakhir = {}
        for pesan in (
            PesanLangsung.objects.filter(ruang_id__in=[langganan.ruang_id for langganan in daftar])
            .order_by("ruang_id", "-created_at")
            .distinct("ruang_id")
        ):
            terakhir[pesan.ruang_id] = pesan
        privat = kanal_privat_milik([request.user.id], [p.muatan for p in terakhir.values()]).get(
            str(request.user.id), set()
        )

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

            baris = _bentuk_ruang(ruang, request.user.id, belum.get(ruang.id, 0), boleh_tulis=hak_tulis(ruang))
            baris["isi"] = samarkan(pesan.isi, pesan.muatan, request.user.id, boleh=privat)[0] if pesan else ""
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

        hasil = list(
            PesanLangsung.objects.filter(ruang_id__in=ruang_saya)
            .filter(isi__icontains=kunci)
            .order_by("-created_at")[:JUMLAH_HASIL_CARI]
        )
        # KEP-91: isi disamarkan untuk yang mencari, lalu hasil yang cocoknya
        # HANYA di nama kanal privat yang tersamar dibuang. Tanpa saringan kedua,
        # mencari nama kanal privat jadi cara menebak bahwa kanal itu ada.
        privat = kanal_privat_milik([request.user.id], [p.muatan for p in hasil]).get(str(request.user.id), set())
        tersaring = []
        for p in hasil:
            isi = samarkan(p.isi, p.muatan, request.user.id, boleh=privat)[0]
            if kunci.lower() in (isi or "").lower():
                tersaring.append((p, isi))
        return Response(
            [
                {
                    "id": str(p.id),
                    "isi": isi,
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
                for p, isi in tersaring
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
        # Kartu (log panggilan, kartu tugas) bukan tulisan orang: tidak bisa
        # disunting atau dihapus lewat sini.
        return PesanLangsung.objects.filter(
            id=pesan_id, workspace__slug=slug, pengirim=request.user, jenis="teks"
        ).first()

    def patch(self, request, slug, pesan_id):
        pesan = self._pesan_saya(request, slug, pesan_id)
        if pesan is None:
            return Response({"error": "Bukan pesan Anda."}, status=status.HTTP_404_NOT_FOUND)
        # Jendela sunting dari God Mode (KEP-83), 0 = tanpa batas (perilaku lama).
        # Pola sama dengan jendela hapus di bawah.
        batas_jam = setelan_angka(CHAT_EDIT_WINDOW_HOURS)
        if batas_jam and pesan.created_at < timezone.now() - timedelta(hours=batas_jam):
            return Response(
                {"error": f"Pesan yang lebih lama dari {batas_jam} jam tidak bisa disunting."},
                status=status.HTTP_403_FORBIDDEN,
            )

        isi = (request.data.get("isi") or "").strip()
        if not isi:
            return Response({"error": "Pesan kosong."}, status=status.HTTP_400_BAD_REQUEST)
        batas_isi = setelan_angka(CHAT_MESSAGE_MAX_LENGTH)
        if len(isi) > batas_isi:
            return Response(
                {"error": f"Pesan terlalu panjang, maksimum {batas_isi} karakter."},
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
        # Pesan lama sudah dibaca dan ditanggapi orang; menghapusnya merobek
        # percakapan. Batasnya dari God Mode > Features, 0 = tanpa batas.
        batas_jam = setelan_angka(CHAT_DELETE_WINDOW_HOURS)
        if batas_jam and pesan.created_at < timezone.now() - timedelta(hours=batas_jam):
            return Response(
                {"error": f"Pesan yang lebih lama dari {batas_jam} jam tidak bisa dihapus."},
                status=status.HTTP_403_FORBIDDEN,
            )
        # Soft delete: barisnya tetap ada. Daftar pesan satu ruang memuatnya
        # sebagai batu nisan (`dihapus`), sedangkan pencarian, hitungan belum
        # dibaca, dan pratinjau percakapan tetap menyaringnya lewat manager bawaan.
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
        # sembarang id pesan yang ditebak. Penjaganya Langganan, sama dengan hak
        # baca: aturan lama "pengirim/penerima" membuat pesan kanal (tanpa
        # penerima), termasuk Announcements, tidak bisa direaksi siapa pun selain
        # pengirimnya.
        pesan = (
            PesanLangsung.objects.filter(id=pesan_id, workspace__slug=slug)
            .filter(
                Q(pengirim=request.user)
                | Q(penerima=request.user)
                | Q(ruang__langganan__user=request.user, ruang__langganan__deleted_at__isnull=True)
            )
            .distinct()
            .first()
        )
        if pesan is None:
            return Response({"error": "Pesan tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        # Periksa-lalu-tulis harus satu langkah. unique_together di model memuat
        # deleted_at, dan NULL tidak pernah sama dengan NULL di Postgres, jadi
        # basis data TIDAK menolak dua baris aktif yang kembar. Dua permintaan
        # serentak (klik ganda, atau satu klik yang terpicu dua kali) dulu
        # sama-sama melihat "belum ada" lalu sama-sama membuat baris: reaksi
        # ganda. Mengunci baris pesannya membuat toggle per pesan berurutan.
        # Tidak bisa di kueri di atas: Postgres menolak FOR UPDATE bersama DISTINCT.
        with transaction.atomic():
            PesanLangsung.objects.select_for_update().filter(pk=pesan.pk).first()
            milik_saya = ReaksiPesan.objects.filter(pesan=pesan, user=request.user, emoji=emoji)
            if milik_saya.exists():
                # Klik kedua pada emoji yang sama = membatalkan. Satu endpoint untuk
                # dua arah, karena dari sisi UI ini memang satu tombol. Semua baris
                # sekaligus, supaya kembaran sisa balapan lama ikut bersih.
                milik_saya.delete(soft=False)
                aktif = False
            else:
                ReaksiPesan.objects.create(pesan=pesan, user=request.user, emoji=emoji)
                aktif = True

        siarkan(pesan.ruang_id, "reaksi", request.user.id)
        return Response({"aktif": aktif}, status=status.HTTP_201_CREATED if aktif else status.HTTP_200_OK)


# Batas sematan per ruang. Bilah sematan di atas percakapan berguna selama
# isinya bisa dipindai sekilas; lewat dari ini ia jadi daftar kedua yang tidak
# dibaca siapa pun.
BATAS_SEMATAN = 20


def _bentuk_sematan(pesan, saya_id=None):
    """Satu baris bilah sematan: cukup untuk dipindai dan dilompati."""
    return {
        "id": str(pesan.id),
        "pengirim": str(pesan.pengirim_id) if pesan.pengirim_id else None,
        # Dipotong seperti kutipan balasan: bilah cuma menampilkan cuplikan.
        # KEP-91: disamarkan dulu, baru dipotong.
        "isi": (samarkan(pesan.isi, pesan.muatan, saya_id)[0] or "")[:200],
        "jenis": pesan.jenis,
        "created_at": pesan.created_at,
        "disematkan_pada": pesan.disematkan_pada,
        "disematkan_oleh": str(pesan.disematkan_oleh_id) if pesan.disematkan_oleh_id else None,
    }


def _boleh_sematkan(user, ruang) -> bool:
    """Siapa boleh menyematkan dan melepas sematan di sebuah ruang.

    Anggota ruang (berlangganan), sama dengan hak baca dan hak reaksi, DAN orang
    yang boleh menulis di ruang itu (`boleh_kirim`). Syarat kedua yang membuat
    kanal sistem tetap terkunci: Announcements hanya disematkan admin, dan
    Changelog serta ruang kabar tidak bisa diubah siapa pun, sama seperti tidak
    bisa ditulisi. Kanal biasa dan DM: semua anggotanya, seperti WhatsApp grup
    yang tidak dikunci admin.
    """
    return _langganan(user.id, ruang) is not None and boleh_kirim(ruang, user)


class ChatSematanEndpoint(BaseAPIView):
    """Sematkan (POST) atau lepas sematan (DELETE) satu pesan.

    Dua kata kerja, bukan satu tombol bolak-balik seperti reaksi: sematan milik
    seluruh ruang, jadi dua orang yang menekan "Sematkan" bersamaan harus sama-sama
    berakhir dengan pesan tersemat, bukan saling membatalkan.
    """

    permission_classes = [WorkspaceEntityPermission]

    def _pesan(self, request, slug, pesan_id):
        """Pesan hidup beserta izinnya. Kembalikan (pesan, respons_galat)."""
        pesan = (
            PesanLangsung.objects.filter(id=pesan_id, workspace__slug=slug, ruang__isnull=False)
            .select_related("ruang")
            .first()
        )
        # Bukan anggota = 404, bukan 403: id pesan di ruang orang lain tidak
        # boleh membocorkan bahwa pesan itu ada.
        if pesan is None or _langganan(request.user.id, pesan.ruang) is None:
            return None, Response({"error": "Pesan tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        if not _boleh_sematkan(request.user, pesan.ruang):
            return None, Response(
                {"error": "Anda tidak bisa menyematkan pesan di ruang ini."}, status=status.HTTP_403_FORBIDDEN
            )
        return pesan, None

    def post(self, request, slug, pesan_id):
        pesan, galat = self._pesan(request, slug, pesan_id)
        if galat:
            return galat
        if pesan.disematkan_pada is None:
            jumlah = PesanLangsung.objects.filter(ruang_id=pesan.ruang_id, disematkan_pada__isnull=False).count()
            if jumlah >= BATAS_SEMATAN:
                return Response(
                    {"error": f"Maksimum {BATAS_SEMATAN} pesan tersemat. Lepas salah satu dulu."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            pesan.disematkan_pada = timezone.now()
            pesan.disematkan_oleh = request.user
            pesan.save(update_fields=["disematkan_pada", "disematkan_oleh", "updated_at"])
            siarkan(pesan.ruang_id, "sematan", request.user.id)
        return Response(_bentuk_sematan(pesan, request.user.id), status=status.HTTP_200_OK)

    def delete(self, request, slug, pesan_id):
        pesan, galat = self._pesan(request, slug, pesan_id)
        if galat:
            return galat
        if pesan.disematkan_pada is not None:
            pesan.disematkan_pada = None
            pesan.disematkan_oleh = None
            pesan.save(update_fields=["disematkan_pada", "disematkan_oleh", "updated_at"])
            siarkan(pesan.ruang_id, "sematan", request.user.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatRuangSematanEndpoint(BaseAPIView):
    """Pesan tersemat satu ruang, terbaru disematkan lebih dulu.

    Endpoint sendiri, bukan medan di respons isi ruang: isi ruang adalah daftar
    100 pesan terakhir, sedangkan sematan bisa jauh lebih tua dari itu. Pesan yang
    dihapus otomatis hilang dari sini lewat manager bawaan.
    """

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug, ruang_id):
        ruang = Ruang.objects.filter(id=ruang_id, workspace__slug=slug).first()
        if ruang is None or _langganan(request.user.id, ruang) is None:
            return Response({"error": "Ruang tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        tersemat = PesanLangsung.objects.filter(ruang=ruang, disematkan_pada__isnull=False)
        daftar = tersemat.order_by("-disematkan_pada")[:BATAS_SEMATAN]
        return Response(
            {
                "boleh_sematkan": _boleh_sematkan(request.user, ruang),
                "pesan": [_bentuk_sematan(p, request.user.id) for p in daftar],
            },
            status=status.HTTP_200_OK,
        )


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
    # Lampiran = isi ruang, jadi penjaganya sama dengan isi ruang: anggota
    # (`_langganan`). Pesan kanal tidak punya penerima; aturan lama
    # "pengirim/penerima" membuat lampiran kanal hanya bisa dibuka pengirimnya.
    # Pemilik workspace tetap TIDAK ikut kecuali memang anggota ruangnya:
    # kewenangan membaca obrolan orang lain ditarik 13 Agt 2026.
    if pesan.ruang_id is not None:
        return Langganan.objects.filter(ruang_id=pesan.ruang_id, user_id=user.id).exists()
    # Pesan lama sebelum ada ruang: pengirim dan penerima saja.
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
    # all_objects: pesan yang dihapus ikut sebagai batu nisan (lihat _bentuk).
    antara = PesanLangsung.all_objects.filter(ruang=ruang)
    if batas is not None:
        antara = antara.filter(created_at__lt=batas)

    # Diambil menurun supaya yang terpotong adalah pesan TERTUA, lalu dibalik
    # supaya peramban menerimanya urut waktu.
    urut = list(reversed(list(antara.order_by("-created_at")[:JUMLAH_PESAN])))
    hidup = [p.id for p in urut if p.deleted_at is None]
    peta = _peta_lampiran(hidup, slug)
    reaksi = _peta_reaksi(hidup)
    kutipan = _peta_kutipan([p for p in urut if p.deleted_at is None], request.user.id)
    # KEP-91: keanggotaan kanal privat yang dirujuk, satu kueri untuk semua pesan.
    privat = kanal_privat_milik([request.user.id], [p.muatan for p in urut if p.deleted_at is None]).get(
        str(request.user.id), set()
    )
    return [
        _bentuk(
            p,
            slug,
            request.user.id,
            peta.get(str(p.id)),
            reaksi.get(str(p.id)),
            kutipan.get(str(p.balasan_ke_id)) if p.balasan_ke_id else None,
            privat,
        )
        for p in urut
    ]


def _saring_sebutan(mentah, ruang) -> list:
    """Id yang disebut, disaring ke anggota ruang ini, urut seperti permintaan.

    Peramban mengirim id, bukan nama: nama tampilan bisa kembar dan bisa
    berganti. Disaring di server karena hanya anggota ruang yang boleh disebut;
    tanpa itu, sebutan jadi jalan mengirim kartu ke siapa pun di workspace.

    KEP-91: diri sendiri (`@yourself`) kini IKUT, supaya sebutannya tetap
    disorot di gelembung. Yang membuang pengirim adalah pengiriman kartu, bukan
    saringan ini.
    """
    if not isinstance(mentah, list):
        return []
    calon = []
    for nilai in mentah[:BATAS_SEBUT]:
        try:
            u = uuid.UUID(str(nilai))
        except (TypeError, ValueError):
            continue
        if u not in calon:
            calon.append(u)
    if not calon:
        return []
    anggota = set(Langganan.objects.filter(ruang=ruang, user_id__in=calon).values_list("user_id", flat=True))
    return [u for u in calon if u in anggota]


def _rujukan(request, ruang, sebut) -> dict:
    """`muatan` pesan teks baru: sebutan orang, #kanal, #work item, dan @all.

    Kunci yang kosong tidak ditulis, supaya pesan tanpa rujukan tetap `{}` dan
    peramban lama yang membaca `muatan.sebut` tidak berubah perilakunya.
    """
    muatan = {}
    if sebut:
        muatan["sebut"] = [str(u) for u in sebut]
    kanal = saring_kanal(request.user, ruang.workspace_id, request.data.get("kanal"))
    if kanal:
        muatan["kanal"] = kanal
    tugas = saring_tugas(request.user, ruang.workspace_id, request.data.get("tugas"))
    if tugas:
        muatan["tugas"] = tugas
    # @all hanya bermakna di kanal: di DM lawan bicaranya sudah pasti membaca.
    if request.data.get("semua") is True and ruang.tipe != Ruang.Tipe.DM:
        muatan["semua"] = True
    return muatan


def _kirim_ke_ruang(request, slug, ruang, penerima_id=None):
    """Tulis satu pesan ke ruang. Kembalikan Response, sukses maupun gagal.

    Semua pemeriksaan isi ada di sini dan hanya di sini, supaya kanal tidak bisa
    dipakai sebagai jalan memutar batas yang berlaku di DM.
    """
    isi = (request.data.get("isi") or "").strip()
    lampiran_ids = request.data.get("lampiran") or []

    # Batas lampiran dan panjang pesan dari God Mode (KEP-83); bawaannya 5 dan
    # 5000, angka yang dulu tertulis di kode.
    batas_lampiran = setelan_angka(CHAT_ATTACHMENTS_MAX)
    batas_isi = setelan_angka(CHAT_MESSAGE_MAX_LENGTH)
    if not isinstance(lampiran_ids, list) or len(lampiran_ids) > batas_lampiran:
        return Response(
            {"error": "Lampiran maksimum %s berkas." % batas_lampiran},
            status=status.HTTP_400_BAD_REQUEST,
        )
    # Kosong hanya ditolak kalau lampirannya juga kosong. Mengirim gambar tanpa
    # keterangan apa pun itu hal yang wajar dilakukan orang.
    if not isi and not lampiran_ids:
        return Response({"error": "Pesan kosong."}, status=status.HTTP_400_BAD_REQUEST)
    if len(isi) > batas_isi:
        return Response(
            {"error": "Pesan terlalu panjang, maksimum %s karakter." % batas_isi},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Yang boleh dikutip hanya pesan dari ruang INI. Tanpa saringan itu, id pesan
    # ruang lain bisa dikutip dan cuplikannya ikut terbaca oleh yang tidak berhak.
    balasan_ke_id = request.data.get("balasan_ke")
    if balasan_ke_id and not PesanLangsung.objects.filter(id=balasan_ke_id, ruang=ruang).exists():
        balasan_ke_id = None

    # Catatan untuk diri sendiri lahir sudah terbaca. Tanpa ini ia jadi kandidat
    # email pemberitahuan, dan orang dikirimi email berisi tulisannya sendiri.
    ke_diri_sendiri = penerima_id is not None and str(penerima_id) == str(request.user.id)
    sebut = _saring_sebutan(request.data.get("sebut"), ruang)
    muatan = _rujukan(request, ruang, sebut)
    pesan = PesanLangsung.objects.create(
        workspace_id=ruang.workspace_id,
        ruang=ruang,
        pengirim=request.user,
        penerima_id=penerima_id,
        isi=isi,
        balasan_ke_id=balasan_ke_id,
        dibaca_pada=timezone.now() if ke_diri_sendiri else None,
        muatan=muatan,
    )

    # Denormalisasi yang membuat daftar percakapan bisa diurutkan tanpa subquery.
    Ruang.objects.filter(id=ruang.id).update(pesan_terakhir_pada=pesan.created_at)

    # Beri tahu yang sedang membuka ruang ini. Ditaruh SESUDAH pesan tersimpan:
    # siaran yang mendahului commit membuat peramban menarik ulang lalu tidak
    # menemukan apa-apa, dan pesannya baru muncul pada penarikan berikutnya.
    siarkan(ruang.id, "pesan", request.user.id)

    # DM juga ditulis ke inbox penerima (saklar inbox_chat). Sesudah tersimpan, sama alasannya.
    if penerima_id is not None:
        catat_pesan_dm(pesan)

    # Yang disebut di kanal mendapat kartu di ruang "Paradise"-nya, supaya
    # sebutan tetap sampai walau kanalnya dibisukan atau jarang dibuka.
    # KEP-91: @all = seluruh anggota ruang, digabung dengan sebutan bernama
    # tanpa kembar. Pengirim tidak pernah dikirimi kartu, termasuk @yourself.
    if ruang.tipe != Ruang.Tipe.DM:
        tujuan = set(sebut)
        if muatan.get("semua"):
            tujuan |= set(Langganan.objects.filter(ruang=ruang).values_list("user_id", flat=True))
        tujuan.discard(request.user.id)
        if tujuan:
            kartu_disebut_di_obrolan(pesan, ruang, tujuan)

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
        tandai_chat_terbaca(request.user.id, ruang.id)

        return Response(isi, status=status.HTTP_200_OK)

    def post(self, request, slug, user_id):
        # Mengirim ke diri sendiri SENGAJA dibolehkan: itu ruang catatan pribadi,
        # DM berkunci "saya:saya" dengan satu langganan saja.
        #
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
        hak_tulis = _HakTulis(request.user)
        # Jumlah anggota untuk direktori kanal, satu kueri untuk semuanya.
        jumlah = dict(
            Langganan.objects.filter(ruang_id__in=[r.id for r in daftar])
            .values_list("ruang_id")
            .annotate(n=Count("id"))
        )

        return Response(
            [
                {
                    **_bentuk_ruang(
                        r, request.user.id, belum.get(r.id, 0), ikut=r.id in milik_saya, boleh_tulis=hak_tulis(r)
                    ),
                    "jumlah_anggota": jumlah.get(r.id, 0),
                }
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
            # Ruang kabar "Paradise" milik tiap orang tidak terlihat orang lain,
            # jadi namanya tidak boleh menghalangi kanal bernama sama.
            .exclude(kunci_sistem__startswith="kabar:")
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
            tandai_chat_terbaca(request.user.id, ruang.id)

        _tandai_terbaca(langganan, ruang.pesan_terakhir_pada)
        return Response(isi, status=status.HTTP_200_OK)

    def post(self, request, slug, ruang_id):
        ruang, langganan = self._ruang_saya(request, slug, ruang_id)
        if ruang is None or langganan is None:
            return Response({"error": "Ruang tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        # DM tetap membawa `penerima` supaya tanda terima, email pemberitahuan,
        # dan penjaga lampiran terus bekerja. Kanal tidak punya penerima tunggal.
        penerima_id = _lawan_bicara(ruang, request.user.id) if ruang.tipe == Ruang.Tipe.DM else None
        # Kanal sistem: Changelog dan ruang kabar hanya ditulis sistem,
        # Announcements hanya Super Admin dan admin workspace.
        if not boleh_kirim(ruang, request.user):
            pesan_galat = (
                "Hanya admin yang bisa menulis pengumuman."
                if ruang.kunci_sistem == KUNCI_PENGUMUMAN
                else "Kanal ini hanya bisa dibaca."
            )
            return Response({"error": pesan_galat}, status=status.HTTP_403_FORBIDDEN)
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
        if ruang.sistem:
            return Response(
                {"error": "Kanal sistem tidak bisa ditinggalkan."},
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
        if ruang.sistem:
            # Announcements & Changelog sudah diikuti semua anggota; ruang kabar
            # "Paradise" milik satu orang saja.
            return Response(
                {"error": "Anggota kanal sistem diatur otomatis."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Kanal privat: hanya pengelola (pembuat, admin workspace, Super Admin)
        # yang mengundang. Kanal publik bebas, karena siapa pun bisa masuk sendiri.
        from .chat_kelola import boleh_kelola

        if ruang.tipe == Ruang.Tipe.PRIVAT and not boleh_kelola(request.user, ruang, anggota=True):
            return Response(
                {"error": "Hanya pembuat kanal atau admin yang bisa mengundang ke kanal privat."},
                status=status.HTTP_403_FORBIDDEN,
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
        if dibuat:
            siarkan(ruang.id, "anggota", request.user.id)
        return Response(
            {"ditambahkan": dibuat},
            status=status.HTTP_201_CREATED if dibuat else status.HTTP_200_OK,
        )
