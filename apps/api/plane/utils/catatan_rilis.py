# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: catatan rilis ke kanal Changelog
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Catatan rilis terstruktur, diterbitkan ke kanal Changelog tiap workspace.

Sumbernya `plane/release_notes/<versi>.json`, ikut ter-COPY ke image API
bersama seluruh `plane/`. Satu berkas per versi supaya dua branch yang menulis
catatan untuk versi berbeda tidak bertabrakan:

    {
      "version": "2.3.0",
      "date": "2026-11-10",
      "entries": [
        {"type": "Added", "text": "..."},
        {"type": "Changed", "text": "..."},
        {"type": "Fixed", "text": "..."}
      ]
    }

Yang diterbitkan hanya versi yang <= versi berjalan (`apps/api/package.json`,
KEP-48), jadi catatan yang ditulis lebih awal untuk rilis berikutnya tidak bocor
ke produksi sebelum waktunya.

Idempoten tanpa tabel baru: sebuah versi sudah terbit di workspace X kalau
kanal Changelog X sudah memuat pesan `jenis=changelog` dengan `muatan.versi`
itu. Dua container API yang start bersamaan dijaga advisory lock Postgres.
"""

import json
import logging
from datetime import date, datetime, time
from pathlib import Path

from django.db import connection, transaction
from django.utils import timezone

from plane.db.models import KUNCI_CHANGELOG, JenisPesan, PesanLangsung, Workspace
from plane.utils.kanal_sistem import kirim_pesan_sistem, pastikan_kanal_sistem

logger = logging.getLogger("plane.api")

FOLDER_CATATAN = Path(__file__).resolve().parents[1] / "release_notes"
BERKAS_VERSI = Path(__file__).resolve().parents[2] / "package.json"
JENIS_ENTRI = ("Added", "Changed", "Fixed")
# Kunci advisory lock: angka tetap, cukup unik untuk satu aplikasi.
KUNCI_ADVISORY = 7_022_026_110_3


def urai_versi(teks: str) -> tuple:
    try:
        return tuple(int(b) for b in str(teks).strip().lstrip("pv").split("."))
    except ValueError:
        return ()


def versi_berjalan() -> str:
    try:
        return json.loads(BERKAS_VERSI.read_text(encoding="utf-8")).get("version", "")
    except (OSError, ValueError):
        return ""


def baca_catatan(folder: Path = FOLDER_CATATAN) -> list:
    """Semua catatan yang sah, urut versi naik. Berkas rusak dilewati + dicatat."""
    hasil = []
    for berkas in sorted(folder.glob("*.json")):
        try:
            data = json.loads(berkas.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.warning("changelog: %s bukan JSON yang sah, dilewati", berkas.name)
            continue
        versi = str(data.get("version") or berkas.stem)
        if not urai_versi(versi):
            logger.warning("changelog: versi %r di %s tidak sah, dilewati", versi, berkas.name)
            continue
        entri = [
            {"type": e["type"], "text": str(e["text"]).strip()}
            for e in data.get("entries") or []
            if isinstance(e, dict) and e.get("type") in JENIS_ENTRI and str(e.get("text") or "").strip()
        ]
        if not entri:
            continue
        hasil.append({"versi": versi, "tanggal": str(data.get("date") or ""), "entri": entri})
    hasil.sort(key=lambda c: urai_versi(c["versi"]))
    return hasil


def ringkasan_teks(catatan: dict) -> str:
    """`isi` cadangan: dibaca pencarian dan peramban yang belum mengenal kartu."""
    baris = [f"Paradise {catatan['versi']}" + (f" ({catatan['tanggal']})" if catatan["tanggal"] else "")]
    baris += [f"[{e['type']}] {e['text']}" for e in catatan["entri"]]
    return "\n".join(baris)


def terbitkan(versi_kini: str = None, folder: Path = FOLDER_CATATAN) -> int:
    """Terbitkan setiap catatan yang belum terbit ke setiap workspace.

    Mengembalikan jumlah pesan yang ditulis. Aman dijalankan berulang.
    """
    versi_kini = versi_kini or versi_berjalan()
    batas = urai_versi(versi_kini)
    catatan = [c for c in baca_catatan(folder) if not batas or urai_versi(c["versi"]) <= batas]
    if not catatan:
        return 0

    jumlah = 0
    with transaction.atomic():
        with connection.cursor() as kursor:
            kursor.execute("SELECT pg_advisory_xact_lock(%s)", [KUNCI_ADVISORY])
        for ws_id in Workspace.objects.values_list("id", flat=True):
            kanal = pastikan_kanal_sistem(ws_id)[KUNCI_CHANGELOG]
            sudah = set(
                PesanLangsung.objects.filter(ruang=kanal, jenis=JenisPesan.CHANGELOG).values_list(
                    "muatan__versi", flat=True
                )
            )
            for c in catatan:
                if c["versi"] in sudah:
                    continue
                pesan = kirim_pesan_sistem(kanal, JenisPesan.CHANGELOG, c, ringkasan_teks(c))
                # Rilis lama yang baru diisi belakangan diberi tanggal rilisnya:
                # kanal tetap urut versi dan tidak menyalakan lencana belum-dibaca.
                # Versi berjalan tetap "sekarang" supaya terbaca sebagai kabar baru.
                waktu = waktu_rilis(c["tanggal"])
                if waktu is not None and urai_versi(c["versi"]) < batas:
                    PesanLangsung.objects.filter(pk=pesan.pk).update(created_at=waktu)
                jumlah += 1
    return jumlah


def waktu_rilis(tanggal: str):
    """Tanggal `YYYY-MM-DD` catatan rilis -> pukul 12.00 waktu server, atau None."""
    try:
        hari = date.fromisoformat(tanggal)
    except (TypeError, ValueError):
        return None
    return timezone.make_aware(datetime.combine(hari, time(12, 0)))
