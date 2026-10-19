/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: sampul kartu Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Sampul kartu Wiki: gradien yang diturunkan dari nama foldernya.
 *
 * Kenapa bukan foto yang diunggah: model `Page` tidak punya kolom sampul sama
 * sekali, jadi foto berarti membangun jalur unggah sampul baru DAN menugaskan
 * seseorang mengurus belasan foto itu selamanya. Gradien memberi hasil yang
 * sama-sama enak dilihat dengan nol perawatan, dan karena warnanya diturunkan
 * dari NAMA, folder yang sama selalu berwarna sama di layar siapa pun. Orang
 * mengenali "yang hijau itu Finance" tanpa pernah membaca judulnya.
 *
 * Warnanya sengaja TIDAK memakai token tema. Ini permukaan dekoratif yang
 * memang dimaksudkan menyala di terang maupun gelap, persis seperti referensi
 * yang diminta, dan ikon di atasnya selalu putih sehingga kontrasnya tidak
 * bergantung pada tema. Jangan tiru pola ini untuk chrome aplikasi, di sana
 * token tema tetap wajib.
 */
export const SAMPUL_WIKI: readonly string[] = [
  "linear-gradient(135deg, #2f80ed 0%, #22b8cf 100%)",
  "linear-gradient(135deg, #7c4dff 0%, #a05df5 100%)",
  "linear-gradient(135deg, #12b886 0%, #2fc4a0 100%)",
  "linear-gradient(135deg, #e6437f 0%, #f2708f 100%)",
  "linear-gradient(135deg, #f2711c 0%, #f5a623 100%)",
  "linear-gradient(135deg, #4c6ef5 0%, #7048e8 100%)",
  "linear-gradient(135deg, #0ca678 0%, #66a80f 100%)",
  "linear-gradient(135deg, #d6336c 0%, #f76707 100%)",
];

/**
 * Hash yang stabil lintas sesi dan lintas peramban.
 *
 * `String.prototype.hashCode` tidak ada di JS, dan menghitungnya dari indeks
 * urutan daftar akan membuat warna berpindah-pindah begitu ada folder baru
 * disisipkan. Jadi dihitung dari isi namanya (djb2), yang murah dan tidak
 * pernah berubah selama namanya tidak berubah.
 */
export const gradienUntuk = (kunci: string): string => {
  let hash = 5381;
  for (let i = 0; i < kunci.length; i++) hash = ((hash << 5) + hash + kunci.charCodeAt(i)) | 0;
  return SAMPUL_WIKI[Math.abs(hash) % SAMPUL_WIKI.length];
};
