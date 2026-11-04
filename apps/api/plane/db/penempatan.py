# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: penempatan orang di struktur organisasi
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu-satunya penulis baris penempatan `JabatanOrganisasi` (KEP-76).

Model orang di struktur organisasi, sesudah KEP-76:

- **Satu jenjang per orang** (Staf / Supervisor / Manager / Direktur), disimpan
  sama di setiap barisnya.
- **Daftar penempatan**: departemen (jenjang apa pun, boleh banyak) dan divisi
  (hanya manager ke atas, boleh banyak). Satu baris per tempat.
- Menambah tempat = MENAMBAH baris, tidak pernah memindahkan. Memindahkan adalah
  dua langkah yang terlihat: tambah yang baru, cabut yang lama.
- Turun di bawah Manager: baris divisi dicabut otomatis (pemanggil diberi tahu),
  baris departemen tetap. Tidak ada lagi galat "rapikan dulu".
- Mencabut tempat hanya mengubah jenjang kalau orangnya jadi TANPA TEMPAT sama
  sekali: supervisor/manager yang kehilangan tempat terakhirnya jatuh ke Staf
  (KEP-86). Selama masih memegang satu departemen atau divisi mana pun, jenjangnya
  tetap. Direktur tidak pernah jatuh. Orang tanpa jenjang = Staf.

Dulu ada empat jalur tulis yang masing-masing menyunting baris PERTAMA orang itu
(`.first()`), jadi menempatkan seseorang di departemen baru diam-diam memindahkan
penempatan lamanya. Semua jalur sekarang lewat `setel_penempatan`.

Pemanggil wajib membungkusnya dengan `transaction.atomic()` + `tunda_sinkron()` lalu
memanggil `sinkronkan_satu` sesudahnya (akses project ikut).
"""

# Module imports
from plane.db.models import (
    JabatanOrganisasi,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
)

TANPA_TEMPAT = (None, None)

# `sumber` untuk baris yang ditulis karena orangnya JATUH ke staf (jenjang dicabut,
# atau supervisor/manager kehilangan tempat terakhirnya).
SUMBER_JATUH_KE_STAF = "bawaan-staf"


def tingkat_sesudah_cabut(tingkat, dep_lama, div_lama, deps, divs):
    """Jenjang sesudah sebagian penempatan dicabut (KEP-86, 4 Nov 2026).

    Supervisor dan manager yang dicabut dari tempat TERAKHIRNYA (tidak tersisa satu
    departemen atau divisi pun) jatuh ke Staf: tanpa tempat, tidak ada yang mereka
    awasi atau pimpin. Masih punya tempat lain mana pun = jenjang tetap. Direktur
    tidak butuh tempat dan tidak pernah jatuh. Hanya PENCABUTAN yang memicu ini:
    menyetel jenjang Manager sebelum diberi divisi tetap boleh.
    """
    dicabut = bool(set(dep_lama) - set(deps)) or bool(set(div_lama) - set(divs))
    pimpinan = TINGKAT_SUPERVISOR <= tingkat < TINGKAT_DIREKTUR
    if pimpinan and dicabut and not deps and not divs:
        return TINGKAT_MEMBER
    return tingkat


def penempatan_sekarang(workspace_id, user_id):
    """(tingkat|None, {departemen_id}, {divisi_id}) dari baris aktif, id sebagai str."""
    baris = list(
        JabatanOrganisasi.objects.filter(workspace_id=workspace_id, member_id=user_id).values_list(
            "tingkat", "departemen_id", "divisi_id"
        )
    )
    tingkat = max((t for t, _, _ in baris), default=None)
    deps = {str(d) for _, d, _ in baris if d}
    divs = {str(v) for _, _, v in baris if v}
    return tingkat, deps, divs


def setel_penempatan(workspace, user, tingkat, departemen_ids, divisi_ids, sumber="manual", catatan=None):
    """Jadikan baris aktif orang ini TEPAT (tingkat, departemen_ids, divisi_ids).

    Tidak ada lagi "jenjang belum diisi" (4 Nov 2026): orang selalu setidaknya Staf.

    - `tingkat=None` = cabut jenjang dan seluruh penempatan; orangnya kembali jadi
      Staf tanpa tempat (satu baris tanpa tempat, bukan nol baris).
    - Supervisor/manager yang dicabut dari tempat terakhirnya jatuh ke Staf
      (`tingkat_sesudah_cabut`). Pemanggil membaca jenjang akhir dari barisnya.
    - Divisi di bawah Manager dibuang di sini juga (penjaga terakhir).

    Mengembalikan himpunan divisi yang dibuang karena jenjangnya di bawah Manager,
    supaya pemanggil bisa melaporkannya.
    """
    aktif = list(JabatanOrganisasi.objects.filter(workspace=workspace, member=user))
    if tingkat is None:
        tingkat, departemen_ids, divisi_ids = TINGKAT_MEMBER, (), ()
        sumber = SUMBER_JATUH_KE_STAF

    deps = {str(d) for d in departemen_ids}
    divs = {str(v) for v in divisi_ids}
    dep_lama = {str(b.departemen_id) for b in aktif if b.departemen_id}
    div_lama = {str(b.divisi_id) for b in aktif if b.divisi_id}
    tingkat_akhir = tingkat_sesudah_cabut(tingkat, dep_lama, div_lama, deps, divs)
    if tingkat_akhir != tingkat:
        tingkat = tingkat_akhir
        sumber = SUMBER_JATUH_KE_STAF
    dibuang = set()
    if tingkat < TINGKAT_MANAGER and divs:
        dibuang, divs = divs, set()

    ingin = {(d, None) for d in deps} | {(None, v) for v in divs}
    if not ingin:
        # Jenjang tanpa tempat (direktur, atau orang yang belum ditempatkan).
        ingin = {TANPA_TEMPAT}

    def kunci(b):
        return (str(b.departemen_id) if b.departemen_id else None, str(b.divisi_id) if b.divisi_id else None)

    sudah = {}
    for b in aktif:
        k = kunci(b)
        if k in ingin and k not in sudah:
            sudah[k] = b
        else:
            b.delete()

    for k, b in sudah.items():
        kolom = []
        if b.tingkat != tingkat:
            b.tingkat = tingkat
            kolom.append("tingkat")
        if catatan is not None and b.catatan != catatan:
            b.catatan = catatan
            kolom.append("catatan")
        if kolom:
            b.save(update_fields=[*kolom, "updated_at"])

    for dep_id, div_id in ingin - set(sudah):
        # `all_objects` + hidupkan kembali, BUKAN create polos: pasangan yang pernah
        # dicabut masih ada sebagai baris ber-deleted_at (jebakan A21).
        lama = (
            JabatanOrganisasi.all_objects.filter(
                workspace=workspace, member=user, departemen_id=dep_id, divisi_id=div_id
            )
            .order_by("-updated_at")
            .first()
        )
        if lama is None:
            JabatanOrganisasi.objects.create(
                workspace=workspace,
                member=user,
                tingkat=tingkat,
                departemen_id=dep_id,
                divisi_id=div_id,
                sumber=sumber,
                catatan=catatan or "",
            )
        else:
            lama.deleted_at = None
            lama.tingkat = tingkat
            lama.sumber = sumber
            if catatan is not None:
                lama.catatan = catatan
            lama.save(update_fields=["deleted_at", "tingkat", "sumber", "catatan", "updated_at"])
    return dibuang
