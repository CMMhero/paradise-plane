# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: email tiap pengumuman perusahaan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tiap pesan baru di kanal Announcements dikirim ke email semua anggota.

Penerima = anggota aktif workspace (sama dengan yang diikutkan ke kanal), tanpa
penulisnya sendiri, disaring saklar email `pengumuman` (bawaan hidup). Sengaja
TIDAK disaring `ENABLE_CHAT_EMAIL` maupun `ENABLE_EMAIL_ACTIVE_ONLY`: pengumuman
memang dimaksudkan sampai ke semua orang, termasuk yang jarang membuka aplikasi.
Dua aturan God Mode mengubahnya: ANNOUNCEMENT_EMAIL (bawaan hidup; mati = tidak ada
email pengumuman) dan ANNOUNCEMENT_EMAIL_ACTIVE_ONLY (bawaan mati; hidup = hanya yang
membuka aplikasi dalam EMAIL_ACTIVE_DAYS terakhir).

Sekali kirim per pesan. Menyunting atau menghapus pengumuman tidak mengirim ulang.
"""

import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

from celery import shared_task
from django.utils import timezone

from plane.db.models import KUNCI_PENGUMUMAN, FileAsset, PesanLangsung, User
from plane.license.utils.instance_value import email_aktif, get_email_configuration
from plane.utils.email_merek import (
    avatar_untuk,
    bahasa_penerima,
    base_url,
    baris_orang,
    buat_pesan,
    bungkus,
    judul_html,
    koneksi_smtp,
    kotak,
    tombol,
    url_preferensi,
)
from plane.utils import aturan
from plane.utils.aturan.area_notifikasi import ANNOUNCEMENT_EMAIL, ANNOUNCEMENT_EMAIL_ACTIVE_ONLY
from plane.utils.exception_logger import log_exception
from plane.utils.kanal_sistem import anggota_layak
from plane.utils.penerima_aktif import aktif_sejak
from plane.utils.preferensi_email import penyaring
from plane.utils.saklar_instance import EMAIL_ACTIVE_DAYS, setelan_angka
from plane.utils.rujukan_obrolan import samarkan

logger = logging.getLogger("plane.worker")

TEKS = {
    "id": {
        "subjek": "[Pengumuman] {nama}: {cuplikan}",
        "judul": "Pengumuman baru",
        "lampiran": "{n} lampiran, buka di aplikasi untuk melihatnya.",
        "tombol": "Buka Announcements",
        "buka_teks": "Buka: {url}",
        "alasan": "Anda menerima email ini karena email pengumuman Anda menyala.",
    },
    "en": {
        "subjek": "[Announcement] {nama}: {cuplikan}",
        "judul": "New announcement",
        "lampiran": "{n} attachments, open the app to see them.",
        "tombol": "Open Announcements",
        "buka_teks": "Open: {url}",
        "alasan": "You received this email because announcement emails are turned on for you.",
    },
}
PANJANG_SUBJEK = 60


def _zona(user):
    try:
        return ZoneInfo(getattr(user, "user_timezone", None) or "UTC")
    except Exception:  # noqa: BLE001
        return ZoneInfo("UTC")


def _nama(user) -> str:
    return user.display_name or user.first_name or user.email


def _cuplikan(teks) -> str:
    satu_baris = " ".join((teks or "").split())
    return satu_baris if len(satu_baris) <= PANJANG_SUBJEK else satu_baris[: PANJANG_SUBJEK - 1] + "…"


def susun_email_pengumuman(penerima, pesan, isi, jumlah_lampiran, bahasa="id", gambar=None):
    """(subjek, teks, html). `isi` = teks pengumuman yang sudah disamarkan."""
    s = TEKS.get(bahasa, TEKS["id"])
    nama = _nama(pesan.pengirim)
    subjek = s["subjek"].format(nama=nama, cuplikan=_cuplikan(isi) or s["judul"])
    url = base_url()
    tautan = f"{url}/{pesan.workspace.slug}/chat?ruang={pesan.ruang_id}" if url else ""
    waktu = timezone.localtime(pesan.created_at, _zona(penerima)).strftime("%d/%m/%Y %H:%M")
    catatan_lampiran = s["lampiran"].format(n=jumlah_lampiran) if jumlah_lampiran else ""

    av, _ = avatar_untuk(pesan.pengirim, gambar=gambar)
    badan = "\n".join(b for b in (isi, catatan_lampiran) if b)
    html_isi = judul_html(s["judul"]) + baris_orang(av, waktu) + kotak(badan) + tombol(s["tombol"], tautan)
    html = bungkus(
        html_isi,
        bahasa=bahasa,
        judul=subjek,
        pratajuk=_cuplikan(isi),
        alasan=s["alasan"],
        url_preferensi=url_preferensi(pesan.workspace.slug),
        email_penerima=penerima.email,
    )
    teks = [s["judul"], "", f"{nama} · {waktu}", "", badan, ""]
    if tautan:
        teks.append(s["buka_teks"].format(url=tautan))
    return subjek, "\n".join(teks).strip() + "\n", html


@shared_task
def kirim_email_pengumuman(pesan_id):
    pesan = (
        PesanLangsung.objects.filter(id=pesan_id, ruang__kunci_sistem=KUNCI_PENGUMUMAN, pengirim__isnull=False)
        .select_related("pengirim", "workspace")
        .first()
    )
    if pesan is None:
        return {"terkirim": 0, "gagal": 0}
    if not aturan.get_bool(ANNOUNCEMENT_EMAIL):
        logger.info("pengumuman-email: dimatikan di God Mode, pesan %s tidak dikirim lewat email", pesan_id)
        return {"terkirim": 0, "gagal": 0}
    if not email_aktif(get_email_configuration()[0]):
        logger.info("pengumuman-email: SMTP belum diatur, pesan %s tidak dikirim lewat email", pesan_id)
        return {"terkirim": 0, "gagal": 0}

    calon = anggota_layak(pesan.workspace_id) - {pesan.pengirim_id}
    penerima = User.objects.filter(id__in=penyaring(calon, "pengumuman")).exclude(email="").order_by("email")
    if aturan.get_bool(ANNOUNCEMENT_EMAIL_ACTIVE_ONLY):
        batas = timezone.now() - timedelta(days=setelan_angka(EMAIL_ACTIVE_DAYS))
        penerima = [orang for orang in penerima if aktif_sejak(orang, batas)]
    # KEP-91: email bisa diteruskan ke siapa saja, jadi nama kanal privat yang
    # dirujuk selalu disamarkan, untuk penerima mana pun.
    isi, _ = samarkan(pesan.isi, pesan.muatan or {}, None)
    jumlah_lampiran = FileAsset.objects.filter(
        entity_type=FileAsset.EntityTypeContext.CHAT_ATTACHMENT, entity_identifier=str(pesan.id), is_uploaded=True
    ).count()

    koneksi, dari = koneksi_smtp()
    terkirim = gagal = 0
    koneksi.open()
    try:
        for orang in penerima:
            try:
                gambar = []
                subjek, teks, html = susun_email_pengumuman(
                    orang, pesan, isi, jumlah_lampiran, bahasa_penerima(orang), gambar
                )
                buat_pesan(
                    ke=orang.email, subjek=subjek, html=html, teks=teks, koneksi=koneksi, dari=dari, gambar=gambar
                ).send(fail_silently=False)
                terkirim += 1
            except Exception as e:  # noqa: BLE001
                # Satu alamat rusak tidak boleh menahan pengumuman untuk orang lain.
                gagal += 1
                log_exception(e)
    finally:
        koneksi.close()
    logger.info("pengumuman-email: pesan %s, %s terkirim, %s gagal", pesan_id, terkirim, gagal)
    return {"terkirim": terkirim, "gagal": gagal}
