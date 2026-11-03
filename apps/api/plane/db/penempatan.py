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

Dulu ada empat jalur tulis yang masing-masing menyunting baris PERTAMA orang itu
(`.first()`), jadi menempatkan seseorang di departemen baru diam-diam memindahkan
penempatan lamanya. Semua jalur sekarang lewat `setel_penempatan`.

Pemanggil wajib membungkusnya dengan `transaction.atomic()` + `tunda_sinkron()` lalu
memanggil `sinkronkan_satu` sesudahnya (akses project ikut).
"""

# Module imports
from plane.db.models import JabatanOrganisasi, TINGKAT_MANAGER

TANPA_TEMPAT = (None, None)


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

    `tingkat=None` = cabut jenjang dan seluruh penempatan. Divisi di bawah Manager
    dibuang di sini juga (penjaga terakhir). Mengembalikan himpunan divisi yang
    dibuang karena aturan itu, supaya pemanggil bisa melaporkannya.
    """
    aktif = list(JabatanOrganisasi.objects.filter(workspace=workspace, member=user))
    if tingkat is None:
        for b in aktif:
            b.delete()  # soft delete: riwayat siapa mencabut tetap ada
        return set()

    deps = {str(d) for d in departemen_ids}
    divs = {str(v) for v in divisi_ids}
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
