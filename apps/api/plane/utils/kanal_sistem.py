# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kanal sistem obrolan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kanal sistem: Announcements, Changelog, dan ruang kabar "Paradise" per orang.

Satu tempat untuk tiga aturan yang harus sama di setiap jalur:

* Kanal sistem ada di setiap workspace dan diikuti SEMUA anggota aktif. Dibuat
  dan diikutkan dari tiga jalur: migrasi 0159 (anggota lama), signal anggota
  workspace baru, dan pemeriksaan malas saat daftar percakapan dibuka. Yang
  terakhir itu jaring untuk jalur `bulk_create` (terima undangan) yang tidak
  memancarkan signal.
* Siapa yang boleh menulis: Changelog hanya sistem, Announcements hanya Super
  Admin dan admin workspace, ruang kabar hanya sistem.
* Pesan sistem ditulis lewat `kirim_pesan_sistem`, yang juga menggeser
  `pesan_terakhir_pada` dan menyiarkan ke soket, sama seperti jalur kirim biasa.

Semua fungsi yang dipanggil dari jalur lain (signal, tugas Celery) menelan
galatnya sendiri: kanal sistem tidak boleh menggagalkan pendaftaran anggota.
"""

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from plane.db.models import (
    AWALAN_KABAR,
    KUNCI_CHANGELOG,
    KUNCI_PENGUMUMAN,
    Langganan,
    PesanLangsung,
    Ruang,
    WorkspaceMember,
)
from plane.db.models.akun_terhapus import DOMAIN_AKUN_TERHAPUS
from plane.utils.obrolan_siaran import siarkan

logger = logging.getLogger("plane.api")

ROLE_ADMIN = 20

# Nama tampilan. God Mode dan teks sistem berbahasa Inggris; peramban boleh
# menerjemahkannya lewat `kunci_sistem`.
KANAL_SISTEM = (
    (KUNCI_PENGUMUMAN, "Announcements", "Company announcements from admins."),
    (KUNCI_CHANGELOG, "Changelogs", "What changed in each Paradise release."),
)
NAMA_KABAR = "Paradise"


def kunci_kabar(user_id) -> str:
    return f"{AWALAN_KABAR}{user_id}"


def adalah_kabar(ruang) -> bool:
    return bool(ruang.kunci_sistem and ruang.kunci_sistem.startswith(AWALAN_KABAR))


def _ambil_atau_buat(workspace_id, kunci, nama, topik, tipe):
    """Ruang sistem `kunci` di workspace ini, dibuat kalau belum ada.

    Dua proses yang membuat bersamaan menabrak constraint unik; yang kalah
    mengambil baris pemenang, bukan meledak.
    """
    ruang = Ruang.objects.filter(workspace_id=workspace_id, kunci_sistem=kunci).first()
    if ruang is not None:
        return ruang, False
    try:
        with transaction.atomic():
            return (
                Ruang.objects.create(
                    workspace_id=workspace_id,
                    tipe=tipe,
                    nama=nama,
                    topik=topik,
                    sistem=True,
                    kunci_sistem=kunci,
                ),
                True,
            )
    except IntegrityError:
        return Ruang.objects.get(workspace_id=workspace_id, kunci_sistem=kunci), False


def pastikan_kanal_sistem(workspace_id) -> dict:
    """{kunci: Ruang} untuk Announcements dan Changelog workspace ini."""
    ada = {
        r.kunci_sistem: r
        for r in Ruang.objects.filter(workspace_id=workspace_id, kunci_sistem__in=[k for k, _, _ in KANAL_SISTEM])
    }
    for kunci, nama, topik in KANAL_SISTEM:
        if kunci not in ada:
            ada[kunci], _ = _ambil_atau_buat(workspace_id, kunci, nama, topik, Ruang.Tipe.KANAL)
    return ada


def anggota_layak(workspace_id, user_ids=None) -> set:
    """Anggota aktif workspace yang boleh diikutkan: bukan bot, bukan akun
    nonaktif, bukan akun terhapus (KEP-50, email `@deleted.local`)."""
    kueri = WorkspaceMember.objects.filter(
        workspace_id=workspace_id,
        is_active=True,
        member__is_active=True,
        member__is_bot=False,
    ).exclude(member__email__endswith=f"@{DOMAIN_AKUN_TERHAPUS}")
    if user_ids is not None:
        kueri = kueri.filter(member_id__in=list(user_ids))
    return set(kueri.values_list("member_id", flat=True))


def ikutkan_ke_kanal_sistem(workspace_id, user_ids=None) -> int:
    """Langgankan orang ke kanal sistem. `user_ids=None` = semua anggota layak.

    Mengembalikan jumlah langganan baru. Langganan yang sudah ada tidak
    disentuh, jadi penanda baca orang tidak pernah direset.
    """
    kanal = pastikan_kanal_sistem(workspace_id)
    orang = anggota_layak(workspace_id, user_ids)
    if not orang:
        return 0
    ruang_ids = [r.id for r in kanal.values()]
    sudah = set(Langganan.objects.filter(ruang_id__in=ruang_ids, user_id__in=orang).values_list("ruang_id", "user_id"))
    # Orang yang baru masuk tidak perlu menerima riwayat sebagai "belum dibaca":
    # puluhan catatan rilis lama yang menyala merah di hari pertama hanya
    # mengajari orang mengabaikan lencananya.
    sekarang = timezone.now()
    baru = [
        Langganan(ruang_id=rid, user_id=uid, dibaca_sampai=sekarang)
        for rid in ruang_ids
        for uid in orang
        if (rid, uid) not in sudah
    ]
    Langganan.objects.bulk_create(baru, batch_size=500, ignore_conflicts=True)
    return len(baru)


def ikutkan_aman(workspace_id, user_ids=None) -> None:
    try:
        ikutkan_ke_kanal_sistem(workspace_id, user_ids)
    except Exception:  # noqa: BLE001
        logger.exception("kanal-sistem: gagal mengikutkan %s ke workspace %s", user_ids, workspace_id)


def ikutkan_jika_belum(workspace_id, user_id) -> None:
    """Jaring malas untuk daftar percakapan: satu kueri kalau semuanya beres."""
    try:
        jumlah = Langganan.objects.filter(
            user_id=user_id,
            ruang__workspace_id=workspace_id,
            ruang__kunci_sistem__in=[KUNCI_PENGUMUMAN, KUNCI_CHANGELOG],
        ).count()
        if jumlah < len(KANAL_SISTEM):
            ikutkan_ke_kanal_sistem(workspace_id, [user_id])
    except Exception:  # noqa: BLE001
        logger.exception("kanal-sistem: pemeriksaan malas gagal untuk %s", user_id)


def ruang_kabar(workspace_id, user_id):
    """Ruang kabar "Paradise" milik satu orang, dibuat kalau belum ada.

    Tipe privat dengan satu pelanggan: hanya pemiliknya yang melihatnya, dan
    semua jalur baca yang sudah ada (daftar kanal, isi ruang, pencarian)
    melayaninya tanpa cabang kode baru.
    """
    ruang, dibuat = _ambil_atau_buat(workspace_id, kunci_kabar(user_id), NAMA_KABAR, "", Ruang.Tipe.PRIVAT)
    if dibuat or not Langganan.objects.filter(ruang=ruang, user_id=user_id).exists():
        Langganan.objects.get_or_create(ruang=ruang, user_id=user_id)
    return ruang


def adalah_admin_workspace(user, workspace_id) -> bool:
    from plane.db.superadmin import is_super_admin  # noqa: PLC0415

    if is_super_admin(user):
        return True
    return WorkspaceMember.objects.filter(
        workspace_id=workspace_id, member_id=user.id, is_active=True, role=ROLE_ADMIN
    ).exists()


def boleh_kirim(ruang, user, admin=None) -> bool:
    """Boleh `user` menulis di ruang ini. `admin` boleh diisi pemanggil yang
    sudah menghitungnya, supaya daftar kanal tidak menghitungnya per baris."""
    if not ruang.sistem:
        return True
    if ruang.kunci_sistem == KUNCI_PENGUMUMAN:
        return adalah_admin_workspace(user, ruang.workspace_id) if admin is None else admin
    # Kanal divisi/departemen: obrolan biasa antar anggotanya. Yang dikunci cuma
    # keanggotaannya (ikut God Mode), bukan hak menulisnya.
    kunci = ruang.kunci_sistem or ""
    if kunci.startswith(("divisi:", "departemen:")):
        return True
    # Changelog dan ruang kabar: hanya sistem.
    return False


def boleh_tinggalkan(ruang) -> bool:
    """Kanal sistem tidak bisa ditinggalkan, diganti nama, atau dihapus."""
    return not ruang.sistem


def kirim_pesan_sistem(ruang, jenis, muatan, isi, pengirim_id=None, penerima_id=None):
    """Tulis satu pesan kartu ke ruang, geser urutan, siarkan ke soket."""
    pesan = PesanLangsung.objects.create(
        workspace_id=ruang.workspace_id,
        ruang=ruang,
        pengirim_id=pengirim_id,
        penerima_id=penerima_id,
        isi=isi or "",
        jenis=jenis,
        muatan=muatan or {},
    )
    Ruang.objects.filter(id=ruang.id).update(pesan_terakhir_pada=pesan.created_at)
    siarkan(ruang.id, "pesan", pengirim_id)
    return pesan
