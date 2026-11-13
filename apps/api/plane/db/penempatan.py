# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: penempatan orang di struktur organisasi
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu-satunya penulis baris penempatan `JabatanOrganisasi` (KEP-76).

Model orang di struktur organisasi, sesudah KEP-76:

- **Satu jenjang per orang** (Staf / Supervisor / Manager / Direktur) = baris
  tertingginya. Sejak KEP-93 baris departemen membawa PERAN orang itu di
  departemen tersebut: manager boleh jadi Staf/Supervisor di departemen divisi
  LAIN, tidak pernah "manager departemen".
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
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SEKRETARIS,
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
    dan sekretaris (KEP-101) tidak butuh tempat dan tidak pernah jatuh. Hanya PENCABUTAN yang memicu ini:
    menyetel jenjang Manager sebelum diberi divisi tetap boleh.
    """
    dicabut = bool(set(dep_lama) - set(deps)) or bool(set(div_lama) - set(divs))
    pimpinan = TINGKAT_SUPERVISOR <= tingkat < TINGKAT_SEKRETARIS
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


def departemen_dalam_divisi(departemen_ids, divisi_ids):
    """Id departemen (str) di `departemen_ids` yang berada di salah satu `divisi_ids`.

    KEP-93: manager memimpin divisinya, jadi ia tidak pernah DUDUK di departemen
    divisi itu. Tidak ada "manager departemen"; baris semacam itu hanya menurunkan
    dia diam-diam ke jenjang departemen.
    """
    from plane.db.models import Departemen  # noqa: PLC0415

    if not departemen_ids or not divisi_ids:
        return set()
    return {
        str(d)
        for d in Departemen.objects.filter(id__in=list(departemen_ids), divisi_id__in=list(divisi_ids)).values_list(
            "id", flat=True
        )
    }


def peran_departemen_sekarang(workspace_id, user_id):
    """{departemen_id (str): tingkat baris itu}, peran orang ini per departemen (KEP-93)."""
    return {
        str(d): t
        for t, d in JabatanOrganisasi.objects.filter(
            workspace_id=workspace_id, member_id=user_id, departemen__isnull=False
        ).values_list("tingkat", "departemen_id")
    }


# Peran yang boleh dipegang di satu departemen (KEP-93): tidak ada "manager departemen".
PERAN_DEPARTEMEN_SAH = (TINGKAT_MEMBER, TINGKAT_SUPERVISOR)


def setel_penempatan(
    workspace,
    user,
    tingkat,
    departemen_ids,
    divisi_ids,
    sumber="manual",
    catatan=None,
    peran_departemen=None,
    seragam=False,
):
    """Jadikan baris aktif orang ini TEPAT (tingkat, departemen_ids, divisi_ids).

    Tidak ada lagi "jenjang belum diisi" (4 Nov 2026): orang selalu setidaknya Staf.

    - `tingkat=None` = cabut jenjang dan seluruh penempatan; orangnya kembali jadi
      Staf tanpa tempat (satu baris tanpa tempat, bukan nol baris).
    - Supervisor/manager yang dicabut dari tempat terakhirnya jatuh ke Staf
      (`tingkat_sesudah_cabut`). Pemanggil membaca jenjang akhir dari barisnya.
    - Divisi di bawah Manager dibuang di sini juga (penjaga terakhir).

    Peran per tempat (KEP-93, 5 Nov 2026): `tingkat` adalah jenjang ORANGNYA,
    baris departemen membawa peran orang itu DI departemen tersebut:

    - Peran di satu departemen selalu Staf atau Supervisor, tidak pernah Manager:
      `peran_departemen` kalau dikirim, lalu peran lama, lalu min(jenjang, Supervisor)
      untuk departemen baru. Orang bisa Supervisor di X sekaligus Staf di Y.
    - `seragam=True` (jenjang dipilih eksplisit, mis. halaman Members): di bawah
      Manager semua departemen ikut jenjang itu, seperti sebelum KEP-93.
    - Di bawah Manager jenjang orangnya DITURUNKAN dari perannya: peran tertinggi.
    - Manager ke atas: baris divisi = jenjangnya. Departemen di dalam divisi yang
      ia pimpin dibuang. Manager tanpa divisi menyimpan jenjangnya di satu baris
      tanpa tempat.

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
    peran_lama = {str(b.departemen_id): b.tingkat for b in aktif if b.departemen_id}
    tingkat_akhir = tingkat_sesudah_cabut(tingkat, dep_lama, div_lama, deps, divs)
    if tingkat_akhir != tingkat:
        tingkat = tingkat_akhir
        sumber = SUMBER_JATUH_KE_STAF
    dibuang = set()
    if tingkat < TINGKAT_MANAGER and divs:
        dibuang, divs = divs, set()
    if tingkat >= TINGKAT_MANAGER:
        deps -= departemen_dalam_divisi(deps, divs)

    diminta = {str(k): v for k, v in (peran_departemen or {}).items()}

    def peran(dep_id):
        if dep_id in diminta:
            return min(diminta[dep_id], TINGKAT_SUPERVISOR)
        if seragam and tingkat < TINGKAT_MANAGER:
            return tingkat
        return min(peran_lama.get(dep_id, tingkat), TINGKAT_SUPERVISOR)

    peran_dep = {d: peran(d) for d in deps}
    if tingkat < TINGKAT_MANAGER and peran_dep:
        tingkat = max(peran_dep.values())
    ingin = {(d, None): t for d, t in peran_dep.items()} | {(None, v): tingkat for v in divs}
    if not ingin or max(ingin.values()) < tingkat:
        # Jenjang yang tidak terwakili satu tempat pun: direktur, orang belum
        # ditempatkan, atau manager yang belum (atau tidak lagi) memimpin divisi.
        ingin[TANPA_TEMPAT] = tingkat

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
        if b.tingkat != ingin[k]:
            b.tingkat = ingin[k]
            kolom.append("tingkat")
        if catatan is not None and b.catatan != catatan:
            b.catatan = catatan
            kolom.append("catatan")
        if kolom:
            b.save(update_fields=[*kolom, "updated_at"])

    for (dep_id, div_id), t in ingin.items():
        if (dep_id, div_id) in sudah:
            continue
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
                tingkat=t,
                departemen_id=dep_id,
                divisi_id=div_id,
                sumber=sumber,
                catatan=catatan or "",
            )
        else:
            lama.deleted_at = None
            lama.tingkat = t
            lama.sumber = sumber
            if catatan is not None:
                lama.catatan = catatan
            lama.save(update_fields=["deleted_at", "tingkat", "sumber", "catatan", "updated_at"])
    return dibuang
