# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan area G, keputusan KEP lain yang terkunci di kode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Area G inventaris: keputusan KEP lain yang terkunci di kode.

Tetap di kode (bukan aturan), dengan alasannya:

- G2 tugas terlambat tidak pernah digeser tenggatnya (KEP-67): itu bukti
  keterlambatan; menggesernya menghapus jejak.
- G4 satu project per departemen (KEP-32): invarian struktur data.
- G7 rentang kustom KPI 366 hari, riwayat persetujuan 200 baris, daftar laporan
  500 baris: batas teknis agar jawaban tidak membengkak, bukan kebijakan.
- Proyeksi permintaan lintas divisi (KEP-02): batas kebocoran data; peminta tidak
  pernah menjadi anggota departemen tujuan.
- Judul permintaan 255 karakter: mengikuti kolom `Issue.name`.
- Departemen sendiri bukan tujuan permintaan: jalur UI-nya dibangun di atas itu
  (di departemen sendiri orang membuat work item langsung).
"""

from plane.utils.aturan.jenis import INT, LEVEL, RENDAH, SEDANG, Rule

# Dulu `BATAS_CATATAN = 2000` di app/views/issue/cross_division.py, dan 2000 yang
# sama tertulis di textarea apps/web (tugas-lintas-divisi/page.tsx).
CROSS_DIVISION_NOTE_MAX = "CROSS_DIVISION_NOTE_MAX"

# Dulu tidak ada pemeriksaan jenjang: siapa pun anggota divisi asal boleh mengirim
# (jenjang kosong dihitung staf, KEP-83).
CROSS_DIVISION_MIN_LEVEL = "CROSS_DIVISION_MIN_LEVEL"

ATURAN = (
    Rule(
        key=CROSS_DIVISION_NOTE_MAX,
        kind=INT,
        default=2000,
        min=200,
        max=10000,
        group="assignment",
        label="Cross-department request note length",
        help=(
            "The longest note, in characters, that someone can attach to a request sent to another department. "
            "Lowering it does not shorten notes that were already sent."
        ),
        risk=RENDAH,
        web=True,
        kep="KEP-02",
    ),
    Rule(
        key=CROSS_DIVISION_MIN_LEVEL,
        kind=LEVEL,
        default=10,
        choices=(10, 12, 20, 30),
        group="assignment",
        label="Lowest level that can send a cross-department request",
        help=(
            "People below this level cannot send requests to other departments. People without a level count as "
            "Member. Workspace admins and Super Admins can always send. Requests already sent stay as they are."
        ),
        risk=SEDANG,
        kep="KEP-02",
    ),
)
