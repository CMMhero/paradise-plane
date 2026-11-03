# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kanal obrolan divisi & departemen
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu kanal privat per divisi dan per departemen, anggotanya mengikuti God Mode.

## Siapa di dalam

* Kanal departemen (`departemen:<id>`): orang yang DITEMPATKAN di departemen itu
  (staf, supervisor) + manager divisi induknya.
* Kanal divisi (`divisi:<id>`): semua yang ditempatkan di departemen mana pun di
  divisi itu + manager divisi itu.
* Direktur (tanpa penempatan) tidak diikutkan otomatis: ia menjangkau semua unit,
  dan dua puluh kanal yang menyala sekaligus untuk satu orang hanya mengajarinya
  membisukan semuanya.

Satu-satunya sumber kebenaran adalah `JabatanOrganisasi`, sama dengan jangkauan
project (KEP-29). Tidak ada tombol undang/keluarkan: kanal ini `sistem=True`,
jadi `ChatAnggotaEndpoint` dan `ChatGabungEndpoint` menolak mengubahnya.

## Kapan disinkronkan

Dipanggil dari `plane/db/jangkauan.py`, di ujung `sinkronkan_satu` dan
`sinkronkan_workspace`. Semua jalur yang mengubah penempatan atau struktur sudah
lewat sana (signal jabatan/struktur, endpoint God Mode yang memakai
`tunda_sinkron` lalu sinkron sekali, perintah seed). Menambah signal kedua di sini
berarti dua jalur yang harus dijaga sinkron.

## Keluar dan masuk lagi

Langganan dicabut lewat hapus lunak, persis seperti keluar kanal biasa. Orang yang
masuk lagi mendapat baris baru dengan penanda baca "sekarang": riwayat yang
terjadi selama ia di luar tidak menyala merah di lencananya.

Unit yang dihapus: kanalnya tidak dihapus (riwayatnya tetap milik perusahaan),
seluruh langganannya dicabut sehingga tidak terlihat siapa pun.

Semua fungsi publik menelan galatnya sendiri: kanal obrolan tidak boleh
menggagalkan perubahan penempatan di God Mode.
"""

import logging

from django.utils import timezone

from plane.db.models import Departemen, Divisi, JabatanOrganisasi, Langganan, Ruang
from plane.db.models.hierarki import TINGKAT_MANAGER
from plane.utils.kanal_sistem import _ambil_atau_buat, anggota_layak
from plane.utils.obrolan_siaran import siarkan

logger = logging.getLogger("plane.api")

AWALAN_DIVISI = "divisi:"
AWALAN_DEPARTEMEN = "departemen:"
TOPIK_DIVISI = "Division chat. Members follow the organization chart in God Mode."
TOPIK_DEPARTEMEN = "Department chat. Members follow the organization chart in God Mode."
BATAS_NAMA = 80


def kunci_divisi(divisi_id) -> str:
    return f"{AWALAN_DIVISI}{divisi_id}"


def kunci_departemen(departemen_id) -> str:
    return f"{AWALAN_DEPARTEMEN}{departemen_id}"


def adalah_kanal_organisasi(ruang) -> bool:
    kunci = ruang.kunci_sistem or ""
    return kunci.startswith(AWALAN_DIVISI) or kunci.startswith(AWALAN_DEPARTEMEN)


def _anggota_per_unit(workspace_id) -> tuple:
    """({divisi_id: set(user)}, {departemen_id: set(user)}) dari penempatan aktif."""
    induk = dict(Departemen.objects.filter(workspace_id=workspace_id).values_list("id", "divisi_id"))
    per_divisi, per_dept = {}, {}
    manager = {}
    for user_id, tingkat, dept_id, divisi_id in JabatanOrganisasi.objects.filter(workspace_id=workspace_id).values_list(
        "member_id", "tingkat", "departemen_id", "divisi_id"
    ):
        if dept_id and dept_id in induk:
            per_dept.setdefault(dept_id, set()).add(user_id)
            per_divisi.setdefault(induk[dept_id], set()).add(user_id)
        if divisi_id and tingkat == TINGKAT_MANAGER:
            per_divisi.setdefault(divisi_id, set()).add(user_id)
            manager.setdefault(divisi_id, set()).add(user_id)
    # Manager ikut ke setiap kanal departemen di divisinya.
    for dept_id, divisi_id in induk.items():
        if manager.get(divisi_id):
            per_dept.setdefault(dept_id, set()).update(manager[divisi_id])
    return per_divisi, per_dept


def _pastikan_ruang(workspace_id, kunci, nama, topik):
    """Ruang unit ini; nama ikut diperbarui kalau unitnya diganti nama di God Mode."""
    nama = (nama or "")[:BATAS_NAMA]
    ruang, _ = _ambil_atau_buat(workspace_id, kunci, nama, topik, Ruang.Tipe.PRIVAT)
    if ruang.nama != nama:
        Ruang.objects.filter(id=ruang.id).update(nama=nama)
        ruang.nama = nama
        siarkan(ruang.id, "ruang", None)
    return ruang


def _samakan_anggota(ruang, ingin: set, hanya_user=None) -> int:
    """Langganan ruang = `ingin`. `hanya_user` membatasi perubahan ke satu orang.

    Mengembalikan jumlah perubahan. Siaran "anggota" dikirim sekali per ruang yang
    berubah, supaya panel anggota yang sedang terbuka ikut segar.
    """
    kueri = Langganan.objects.filter(ruang=ruang)
    if hanya_user is not None:
        kueri = kueri.filter(user_id=hanya_user)
    ada = set(kueri.values_list("user_id", flat=True))
    if hanya_user is not None:
        ingin = ingin & {hanya_user}

    sekarang = timezone.now()
    tambah = [Langganan(ruang=ruang, user_id=uid, dibaca_sampai=sekarang) for uid in ingin - ada]
    Langganan.objects.bulk_create(tambah, ignore_conflicts=True)
    buang = ada - ingin
    if buang:
        # Queryset BaseModel menghapus LUNAK (SoftDeletionQuerySet), sama dengan
        # keluar kanal lewat ChatGabungEndpoint.
        Langganan.objects.filter(ruang=ruang, user_id__in=buang).delete()
    berubah = len(tambah) + len(buang)
    if berubah:
        siarkan(ruang.id, "anggota", None)
    return berubah


def _sinkron(workspace_id, hanya_user=None) -> int:
    divisi = list(Divisi.objects.filter(workspace_id=workspace_id).values_list("id", "nama"))
    departemen = list(Departemen.objects.filter(workspace_id=workspace_id).values_list("id", "nama"))
    if (
        not divisi
        and not Ruang.objects.filter(workspace_id=workspace_id, kunci_sistem__startswith=AWALAN_DIVISI).exists()
    ):
        return 0

    per_divisi, per_dept = _anggota_per_unit(workspace_id)
    semua = set().union(*per_divisi.values(), *per_dept.values()) if (per_divisi or per_dept) else set()
    layak = anggota_layak(workspace_id, semua) if semua else set()

    berubah = 0
    hidup = set()
    for div_id, nama in divisi:
        ruang = _pastikan_ruang(workspace_id, kunci_divisi(div_id), nama, TOPIK_DIVISI)
        hidup.add(ruang.id)
        berubah += _samakan_anggota(ruang, per_divisi.get(div_id, set()) & layak, hanya_user)
    for dept_id, nama in departemen:
        ruang = _pastikan_ruang(workspace_id, kunci_departemen(dept_id), nama, TOPIK_DEPARTEMEN)
        hidup.add(ruang.id)
        berubah += _samakan_anggota(ruang, per_dept.get(dept_id, set()) & layak, hanya_user)

    # Unit yang sudah dihapus: kanalnya dikosongkan, riwayatnya disimpan.
    for ruang in Ruang.objects.filter(workspace_id=workspace_id, sistem=True).exclude(id__in=hidup):
        if adalah_kanal_organisasi(ruang):
            berubah += _samakan_anggota(ruang, set(), hanya_user)
    return berubah


def sinkronkan_kanal_organisasi(workspace_id, user_id=None) -> int:
    """Samakan kanal divisi/departemen dengan penempatan. `user_id` = hanya orang itu."""
    try:
        return _sinkron(workspace_id, user_id)
    except Exception:  # noqa: BLE001
        logger.exception("kanal-organisasi: sinkron gagal untuk workspace %s user %s", workspace_id, user_id)
        return 0
