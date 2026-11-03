# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pengelolaan kanal obrolan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Pratinjau kanal, ubah nama/topik, keluarkan anggota, hapus kanal.

Berkas terpisah dari `chat.py` supaya aturan "siapa boleh mengelola" tinggal di
satu tempat yang bisa dibaca utuh.

Siapa boleh mengelola (`boleh_kelola`): pembuat kanal, admin workspace, dan Super
Admin, DAN orangnya harus anggota kanal itu. Syarat keanggotaan itu disengaja:
kewenangan membaca obrolan orang lain sudah dicabut (13 Agt 2026), jadi admin
yang bukan anggota kanal privat tidak boleh tahu kanal itu ada, apalagi
mengubahnya. Untuk kanal publik, admin cukup bergabung dulu.

Pratinjau (GET) sengaja TIDAK memuat pesan. Berlangganan tetap satu-satunya
penanda hak baca isi; yang terlihat sebelum bergabung hanya nama, topik, jumlah
anggota, dan pembuatnya.
"""

# Python imports
import logging

# Django imports
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import WorkspaceEntityPermission
from plane.db.models import Langganan, Ruang, WorkspaceMember
from plane.db.superadmin import is_super_admin
from plane.utils.obrolan_siaran import siarkan

from .base import BaseAPIView
from .chat import BATAS_NAMA_RUANG

logger = logging.getLogger("plane.api")

# Batas topik mengikuti kolom `Ruang.topik`.
BATAS_TOPIK = 255
PERAN_ADMIN_WORKSPACE = 20


def _ruang_sistem(ruang) -> bool:
    """Kanal sistem (Pengumuman/Changelog) tidak bisa diubah, ditinggalkan, atau
    dikosongkan lewat sini. Medan `is_system` ditambahkan migrasi 0159; dibaca
    lewat getattr supaya berkas ini tetap jalan sebelum migrasi itu ada."""
    return bool(getattr(ruang, "is_system", False))


def _admin_workspace(user, ruang) -> bool:
    return WorkspaceMember.objects.filter(
        workspace_id=ruang.workspace_id,
        member_id=user.id,
        role=PERAN_ADMIN_WORKSPACE,
        is_active=True,
    ).exists()


def boleh_kelola(user, ruang, anggota: bool) -> bool:
    """Satu definisi untuk endpoint dan UI (dikirim sebagai `boleh_kelola`)."""
    if ruang.tipe == Ruang.Tipe.DM or not anggota:
        return False
    if ruang.created_by_id == user.id:
        return True
    return _admin_workspace(user, ruang) or is_super_admin(user)


def _kanal(slug, ruang_id):
    return (
        Ruang.objects.filter(id=ruang_id, workspace__slug=slug)
        .exclude(tipe=Ruang.Tipe.DM)
        .first()
    )


def _bentuk_detail(ruang, user, anggota: bool):
    return {
        "id": str(ruang.id),
        "tipe": ruang.tipe,
        "nama": ruang.nama,
        "topik": ruang.topik,
        "pembuat": str(ruang.created_by_id) if ruang.created_by_id else None,
        "created_at": ruang.created_at,
        "jumlah_anggota": Langganan.objects.filter(ruang=ruang).count(),
        "ikut": anggota,
        "sistem": _ruang_sistem(ruang),
        "boleh_kelola": boleh_kelola(user, ruang, anggota) and not _ruang_sistem(ruang),
    }


class ChatKelolaRuangEndpoint(BaseAPIView):
    """Detail/pratinjau satu kanal, ubah nama & topik, dan hapus kanal."""

    permission_classes = [WorkspaceEntityPermission]

    def _muat(self, request, slug, ruang_id):
        """(ruang, anggota) atau (None, False) kalau tidak boleh tahu kanal ini ada."""
        ruang = _kanal(slug, ruang_id)
        if ruang is None:
            return None, False
        anggota = Langganan.objects.filter(ruang=ruang, user=request.user).exists()
        # Kanal privat tidak terlihat dari luar, sama seperti di daftar kanal.
        if ruang.tipe == Ruang.Tipe.PRIVAT and not anggota:
            return None, False
        return ruang, anggota

    def get(self, request, slug, ruang_id):
        ruang, anggota = self._muat(request, slug, ruang_id)
        if ruang is None:
            return Response({"error": "Kanal tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_bentuk_detail(ruang, request.user, anggota), status=status.HTTP_200_OK)

    def patch(self, request, slug, ruang_id):
        ruang, anggota = self._muat(request, slug, ruang_id)
        if ruang is None:
            return Response({"error": "Kanal tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        if _ruang_sistem(ruang) or not boleh_kelola(request.user, ruang, anggota):
            return Response(
                {"error": "Hanya pembuat kanal atau admin yang bisa mengubahnya."},
                status=status.HTTP_403_FORBIDDEN,
            )

        ubah = []
        if "nama" in request.data:
            nama = (request.data.get("nama") or "").strip()
            if not nama:
                return Response({"error": "Nama kanal wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)
            if len(nama) > BATAS_NAMA_RUANG:
                return Response(
                    {"error": "Nama kanal maksimum %s karakter." % BATAS_NAMA_RUANG},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            kembar = (
                Ruang.objects.filter(workspace_id=ruang.workspace_id, nama__iexact=nama)
                .exclude(tipe=Ruang.Tipe.DM)
                .exclude(id=ruang.id)
                .exclude(kunci_sistem__startswith="kabar:")
                .exists()
            )
            if kembar:
                return Response({"error": "Sudah ada kanal dengan nama itu."}, status=status.HTTP_400_BAD_REQUEST)
            ruang.nama = nama
            ubah.append("nama")
        if "topik" in request.data:
            topik = (request.data.get("topik") or "").strip()
            if len(topik) > BATAS_TOPIK:
                return Response(
                    {"error": "Topik maksimum %s karakter." % BATAS_TOPIK},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ruang.topik = topik
            ubah.append("topik")

        if ubah:
            ruang.save(update_fields=[*ubah, "updated_at"])
            siarkan(ruang.id, "ruang", request.user.id)
            logger.info("kanal-chat: %s mengubah %s kanal %s", request.user.email, ",".join(ubah), ruang.id)
        return Response(_bentuk_detail(ruang, request.user, anggota), status=status.HTTP_200_OK)

    def delete(self, request, slug, ruang_id):
        ruang, anggota = self._muat(request, slug, ruang_id)
        if ruang is None:
            return Response({"error": "Kanal tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        if _ruang_sistem(ruang) or not boleh_kelola(request.user, ruang, anggota):
            return Response(
                {"error": "Hanya pembuat kanal atau admin yang bisa menghapusnya."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Hapus lunak lewat queryset, bukan `ruang.delete()`: yang terakhir
        # mengantrekan task Celery untuk relasinya, dan sampai task itu jalan
        # Langganan masih menunjuk ruang ini sehingga kanalnya tetap muncul di
        # daftar percakapan semua anggota. Pesan dibiarkan utuh untuk audit.
        sekarang = timezone.now()
        Langganan.objects.filter(ruang=ruang).update(deleted_at=sekarang)
        Ruang.objects.filter(id=ruang.id).update(deleted_at=sekarang)
        siarkan(ruang.id, "ruang", request.user.id)
        logger.info("kanal-chat: %s menghapus kanal %s (%s)", request.user.email, ruang.nama, ruang.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatKeluarkanAnggotaEndpoint(BaseAPIView):
    """Keluarkan satu anggota dari kanal."""

    permission_classes = [WorkspaceEntityPermission]

    def delete(self, request, slug, ruang_id, user_id):
        ruang = _kanal(slug, ruang_id)
        anggota = ruang is not None and Langganan.objects.filter(ruang=ruang, user=request.user).exists()
        if ruang is None or (ruang.tipe == Ruang.Tipe.PRIVAT and not anggota):
            return Response({"error": "Kanal tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        if _ruang_sistem(ruang) or not boleh_kelola(request.user, ruang, anggota):
            return Response(
                {"error": "Hanya pembuat kanal atau admin yang bisa mengeluarkan anggota."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if str(user_id) == str(request.user.id):
            return Response(
                {"error": "Untuk keluar sendiri, pakai Keluar dari kanal."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        langganan = Langganan.objects.filter(ruang=ruang, user_id=user_id).first()
        if langganan is None:
            return Response({"error": "Orang itu bukan anggota kanal ini."}, status=status.HTTP_404_NOT_FOUND)

        # Hapus lunak lewat queryset, sama alasannya dengan hapus kanal: tidak
        # ada task Celery, dan bergabung lagi nanti membuat baris baru.
        Langganan.objects.filter(id=langganan.id).update(deleted_at=timezone.now())
        siarkan(ruang.id, "anggota", request.user.id)
        logger.info("kanal-chat: %s mengeluarkan %s dari kanal %s", request.user.email, user_id, ruang.id)
        return Response(status=status.HTTP_204_NO_CONTENT)
