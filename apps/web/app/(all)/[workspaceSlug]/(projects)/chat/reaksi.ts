/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** Bentuk reaksi yang dipakai di sini. Sama dengan `TReaksi` di chat.service,
 * ditulis ulang supaya berkas ini bisa diperiksa tanpa alias `@/`. */
export type TReaksiRingkas = { emoji: string; orang: string[] };

/**
 * Jendela (ms) tempat aktivasi kedua dengan kunci yang sama dianggap gema dari
 * gestur yang sama, bukan niat baru.
 *
 * Sebabnya di Base UI 1.0.0-beta.3: di Windows, event `contextmenu` datang
 * SESUDAH tombol kanan dilepas, jadi pendengar `mouseup` sekali-pakai yang
 * dipasang pemicu menu konteks baru tertangkap pada klik KIRI berikutnya, yaitu
 * klik pada item menu. Item lalu menjalankan `click()` buatan di `onMouseUp`,
 * disusul klik asli peramban: satu klik, dua kali `onClick`. Untuk reaksi itu
 * berarti tambah lalu batal (tampak "tidak bisa menambah reaksi"), atau dua
 * permintaan yang balapan di server (tampak "reaksi ganda"). Kedua klik itu
 * berjarak beberapa milidetik; manusia tidak membuka menu lagi lalu memilih
 * item yang sama secepat ini.
 */
export const JENDELA_GEMA_KLIK_MS = 400;

/**
 * Penyaring aktivasi ganda. Mengembalikan fungsi yang menjawab `true` kalau
 * aktivasi dengan `kunci` ini boleh dijalankan, `false` kalau ia gema dari
 * aktivasi yang sama `jendelaMs` sebelumnya.
 *
 * Dicatat per kunci, jadi memilih 👍 lalu ❤️ beruntun tetap dua aksi.
 */
export const buatPenyaringGanda = (jendelaMs = JENDELA_GEMA_KLIK_MS) => {
  const terakhir = new Map<string, number>();
  return (kunci: string, sekarang = Date.now()): boolean => {
    const sebelumnya = terakhir.get(kunci);
    if (sebelumnya !== undefined && sekarang - sebelumnya < jendelaMs) return false;
    terakhir.set(kunci, sekarang);
    return true;
  };
};

/**
 * Daftar reaksi sesudah `sayaId` menekan `emoji`: tambah kalau belum, buang
 * kalau sudah. Cermin `ChatReaksiEndpoint.post` di server, dipakai untuk
 * memperbarui riwayat lama yang tidak ikut ditarik ulang SWR. Tidak mengubah
 * masukan.
 */
export const alihkanReaksi = (reaksi: TReaksiRingkas[], emoji: string, sayaId: string): TReaksiRingkas[] => {
  const ada = reaksi.find((r) => r.emoji === emoji);
  if (!ada) return [...reaksi, { emoji, orang: [sayaId] }];
  if (!ada.orang.includes(sayaId))
    return reaksi.map((r) => (r.emoji === emoji ? { ...r, orang: [...r.orang, sayaId] } : r));
  const sisa = ada.orang.filter((id) => id !== sayaId);
  return sisa.length === 0
    ? reaksi.filter((r) => r.emoji !== emoji)
    : reaksi.map((r) => (r.emoji === emoji ? { ...r, orang: sisa } : r));
};
