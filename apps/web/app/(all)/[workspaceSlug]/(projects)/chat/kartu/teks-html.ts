/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: HTML editor di kartu obrolan jadi teks
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Kartu lama menyimpan komentar dan deskripsi sebagai HTML editor mentah
 * (`<p class="editor-paragraph-block">Pagi mas <mention-component ...>`), dan
 * sebagian terpotong di tengah tag. Server kini mengirim teks
 * (`plane/utils/teks_html.py`); ini untuk kartu yang sudah tersimpan.
 *
 * Murni dan berbasis string: hasilnya selalu teks yang dirender React sebagai
 * teks, tidak pernah HTML. Nilai tanpa tag dikembalikan apa adanya, jadi teks
 * biasa seperti "a < b" tidak tersentuh.
 */

/** Label satu sebutan: `jenis` = `entity_name`, `id` = `entity_identifier`. */
export type TLabelSebutan = (jenis: string, id: string) => string;

const POLA_TAG = /<(\/?)([a-zA-Z][\w-]*)\b([^>]*)>/g;
// Tag terakhir yang terpotong `_cuplikan` lama sebelum sempat ditutup.
const TAG_TERPOTONG = /<\/?[a-zA-Z][^>]*$/;
const TAG_BLOK = new Set(["p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "tr"]);
const ENTITAS: Record<string, string> = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };

const dekode = (s: string): string =>
  s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (asli, kode: string) => {
    if (kode[0] === "#") {
      const angka = kode[1] === "x" || kode[1] === "X" ? parseInt(kode.slice(2), 16) : parseInt(kode.slice(1), 10);
      return Number.isFinite(angka) && angka > 0 && angka <= 0x10ffff ? String.fromCodePoint(angka) : asli;
    }
    return ENTITAS[kode.toLowerCase()] ?? asli;
  });

const atribut = (isi: string, nama: string): string => {
  const cocok = new RegExp(`${nama}\\s*=\\s*(?:"([^"]*)"|'([^']*)')`, "i").exec(isi);
  return dekode(cocok?.[1] ?? cocok?.[2] ?? "");
};

export const adaHtml = (nilai: string): boolean => new RegExp(POLA_TAG.source).test(nilai);

export const teksDariHtml = (nilai: string, labelSebutan: TLabelSebutan): string => {
  if (!adaHtml(nilai)) return nilai;
  const terpotong = TAG_TERPOTONG.test(nilai);
  const html = nilai.replace(TAG_TERPOTONG, "");
  let hasil = "";
  let akhir = 0;
  for (const cocok of html.matchAll(POLA_TAG)) {
    const [utuh, tutup, nama, isi] = cocok;
    hasil += dekode(html.slice(akhir, cocok.index));
    akhir = cocok.index + utuh.length;
    const tag = nama.toLowerCase();
    if (tag === "mention-component" && !tutup) {
      hasil += labelSebutan(atribut(isi, "entity_name") || "user_mention", atribut(isi, "entity_identifier"));
    } else if (tag === "br" || (tutup && TAG_BLOK.has(tag))) {
      hasil += "\n";
    }
  }
  hasil += dekode(html.slice(akhir));
  const baris = hasil
    .split("\n")
    .map((b) => b.split(/\s+/).filter(Boolean).join(" "))
    .filter(Boolean)
    .join("\n");
  return terpotong && !baris.endsWith("…") ? `${baris}…` : baris;
};
