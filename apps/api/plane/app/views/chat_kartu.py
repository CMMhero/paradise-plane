# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: log panggilan di linimasa obrolan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Log panggilan suara/video sebagai kartu di percakapan.

`POST chat/ruang/<ruang_id>/panggilan-log/` dengan `peristiwa`:

* `mulai` (penelepon, atau pemulai panggilan kanal): satu kartu baru berstatus
  `berlangsung`. Log `berlangsung` lama di ruang yang sama ditutup lebih dulu,
  jadi peramban yang tertutup paksa tidak meninggalkan kartu yang "berlangsung"
  selamanya.
* `tersambung` (siapa pun di ruang itu): mencatat waktu sambung pertama.
* `selesai` (siapa pun, yang pertama menang): `selesai` + durasi kalau pernah
  tersambung, `tak_terjawab` kalau tidak.

Server, bukan peramban, yang memutuskan selesai vs tak terjawab dan menghitung
durasinya dari cap waktu yang ia catat sendiri. Peramban cuma melaporkan
peristiwa, jadi kedua pihak boleh melapor tanpa harus sepakat soal id log:
yang dipakai selalu log `berlangsung` terbaru di ruang itu.

Hak = hak baca ruang (Langganan), sama dengan token panggilan.
"""

from datetime import datetime

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import WorkspaceEntityPermission
from plane.db.models import JenisPesan, Langganan, PesanLangsung, Ruang
from plane.utils.obrolan_siaran import siarkan

from .base import BaseAPIView

BERLANGSUNG = "berlangsung"
SELESAI = "selesai"
TAK_TERJAWAB = "tak_terjawab"
PERISTIWA = ("mulai", "tersambung", "selesai")


def ringkasan_panggilan(muatan) -> str:
    """`isi` cadangan untuk pencarian dan peramban lama. Bahasa Inggris."""
    jenis = "Video call" if muatan.get("video") else "Voice call"
    if muatan.get("status") == TAK_TERJAWAB:
        return f"Missed {jenis.lower()}"
    if muatan.get("status") == SELESAI and muatan.get("durasi") is not None:
        menit, detik = divmod(int(muatan["durasi"]), 60)
        return f"{jenis} ({menit}:{detik:02d})"
    return jenis


def tutup_log(pesan, sekarang) -> None:
    """Tutup satu log berlangsung. Idempoten: log yang sudah tutup dibiarkan."""
    muatan = dict(pesan.muatan or {})
    if muatan.get("status") != BERLANGSUNG:
        return
    sambung = muatan.get("tersambung_pada")
    if sambung:
        mulai = datetime.fromisoformat(sambung)
        muatan["status"] = SELESAI
        muatan["durasi"] = max(0, int((sekarang - mulai).total_seconds()))
    else:
        muatan["status"] = TAK_TERJAWAB
        muatan["durasi"] = None
    muatan["selesai_pada"] = sekarang.isoformat()
    pesan.muatan = muatan
    pesan.isi = ringkasan_panggilan(muatan)
    pesan.save(update_fields=["muatan", "isi", "updated_at"])


def _lawan_dm(ruang, saya_id):
    if ruang.tipe != Ruang.Tipe.DM or not ruang.kunci_dm:
        return None
    dua = ruang.kunci_dm.split(":")
    lawan = next((x for x in dua if x != str(saya_id)), None)
    return lawan


class ChatPanggilanLogEndpoint(BaseAPIView):
    permission_classes = [WorkspaceEntityPermission]

    def post(self, request, slug, ruang_id):
        ruang = Ruang.objects.filter(id=ruang_id, workspace__slug=slug).first()
        if ruang is None or not Langganan.objects.filter(ruang=ruang, user=request.user).exists():
            return Response({"error": "Ruang tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        peristiwa = request.data.get("peristiwa")
        if peristiwa not in PERISTIWA:
            return Response(
                {"error": "peristiwa harus 'mulai', 'tersambung', atau 'selesai'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sekarang = timezone.now()
        berlangsung = PesanLangsung.objects.filter(
            ruang=ruang, jenis=JenisPesan.PANGGILAN, muatan__status=BERLANGSUNG
        ).order_by("-created_at")

        if peristiwa == "mulai":
            for lama in berlangsung:
                tutup_log(lama, sekarang)
            muatan = {
                "status": BERLANGSUNG,
                "video": bool(request.data.get("video")),
                "konferensi": ruang.tipe != Ruang.Tipe.DM,
                "oleh": str(request.user.id),
                "mulai": sekarang.isoformat(),
                # Panggilan kanal dihitung tersambung sejak dimulai: tidak ada
                # satu orang yang "menjawab", durasinya = keikutsertaan pemulai.
                "tersambung_pada": sekarang.isoformat() if ruang.tipe != Ruang.Tipe.DM else None,
                "durasi": None,
            }
            lawan = _lawan_dm(ruang, request.user.id)
            pesan = PesanLangsung.objects.create(
                workspace_id=ruang.workspace_id,
                ruang=ruang,
                pengirim=request.user,
                penerima_id=lawan,
                isi=ringkasan_panggilan(muatan),
                jenis=JenisPesan.PANGGILAN,
                muatan=muatan,
            )
            Ruang.objects.filter(id=ruang.id).update(pesan_terakhir_pada=pesan.created_at)
            siarkan(ruang.id, "pesan", request.user.id)
            return Response({"id": str(pesan.id), "muatan": muatan}, status=status.HTTP_201_CREATED)

        pesan = berlangsung.first()
        if pesan is None:
            # Sudah ditutup pihak lain: bukan galat, laporan kedua memang biasa.
            return Response({"id": None}, status=status.HTTP_200_OK)

        if peristiwa == "tersambung":
            if not (pesan.muatan or {}).get("tersambung_pada"):
                pesan.muatan = {**(pesan.muatan or {}), "tersambung_pada": sekarang.isoformat()}
                pesan.save(update_fields=["muatan", "updated_at"])
        else:
            tutup_log(pesan, sekarang)
            siarkan(ruang.id, "sunting", request.user.id)
        return Response({"id": str(pesan.id), "muatan": pesan.muatan}, status=status.HTTP_200_OK)
