/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Markdown pengumuman ke penyunting kaya dan kembali
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Menyunting pengumuman = Markdown tersimpan dimuat ke penyunting kaya, lalu
 * disimpan lagi sebagai Markdown. Tidak semua Markdown selamat lewat jalan itu
 * (pengumuman bisa ditulis dari Obrolan, apa saja), jadi pemanggil membandingkan
 * keluaran penyunting dengan sumbernya (`setaraMarkdown`) dan memakai kotak teks
 * Markdown kalau berbeda. Tes: `tests/pengumuman-roundtrip.test.ts`.
 */

import type { Element, ElementContent, Root as HastRoot } from "hast";
import { toHtml } from "hast-util-to-html";
import type { Nodes } from "mdast";
import remarkParse from "remark-parse";
import remarkRehype from "remark-rehype";
import { unified } from "unified";
import { PLUGIN_DIALEK, remarkBarisBaru, uraiMarkdown, pecahBaris } from "./pesan";

const elemen = (anak: ElementContent | undefined, tag: string): anak is Element =>
  anak?.type === "element" && anak.tagName === tag;

/** Butir centang GFM jadi bentuk yang dikenal skema tiptap (`taskList` / `taskItem`). */
const jadiButirCentang = (daftar: Element) => {
  daftar.properties = { "data-type": "taskList" };
  daftar.children = daftar.children.filter((c) => elemen(c, "li"));
  for (const butir of daftar.children as Element[]) {
    // Daftar longgar membungkus kotak centangnya di dalam <p>.
    const wadah = butir.children.find((c) => elemen(c, "p")) as Element | undefined;
    const pemilik = wadah ?? butir;
    const kotak = pemilik.children.find((c) => elemen(c, "input")) as Element | undefined;
    pemilik.children = pemilik.children.filter((c) => c !== kotak);
    const [pertama] = pemilik.children;
    if (pertama?.type === "text") pertama.value = pertama.value.replace(/^ /, "");
    const blok = butir.children.filter((c) => elemen(c, "ul") || elemen(c, "ol") || elemen(c, "p"));
    const isiLangsung = butir.children.filter((c) => !blok.includes(c as Element));
    butir.children = wadah ? blok : [{ type: "element", tagName: "p", properties: {}, children: isiLangsung }, ...blok];
    butir.properties = { "data-type": "taskItem", "data-checked": kotak?.properties.checked ? "true" : "false" };
  }
};

const rapikan = (induk: HastRoot | Element, dalamPre: boolean) => {
  // Hanya jeda baris milik pemformat; spasi di antara dua potongan tebal adalah isi.
  if (!dalamPre) induk.children = induk.children.filter((c) => !(c.type === "text" && /^\s*\n\s*$/.test(c.value)));
  for (const anak of induk.children) {
    if (anak.type !== "element") continue;
    // Baris baru penutup blok kode milik pemformat, bukan isi.
    if (dalamPre && anak.tagName === "code") {
      const akhir = anak.children[anak.children.length - 1];
      if (akhir?.type === "text") akhir.value = akhir.value.replace(/\n$/, "");
    }
    const centang = [anak.properties.className].flat().includes("contains-task-list");
    rapikan(anak, dalamPre || anak.tagName === "pre");
    if (centang) jadiButirCentang(anak);
  }
};

const keHast = unified()
  .use(remarkParse)
  .use(PLUGIN_DIALEK)
  .use(remarkBarisBaru)
  // Hanya <br>: baris baru bawaan sesudahnya terbaca penyunting sebagai spasi.
  .use(remarkRehype, {
    handlers: { break: () => ({ type: "element", tagName: "br", properties: {}, children: [] }) },
  })
  .freeze();

/**
 * HTML untuk `initialValue` penyunting.
 *
 * Satu baris penuh: tiptap-markdown mengurai isi string sebagai Markdown, dan baris
 * kosong di tengah HTML (mis. di dalam blok kode) akan memutusnya.
 */
export const htmlPenyunting = (markdown: string): string => {
  const pohon = keHast.runSync(keHast.parse(markdown)) as HastRoot;
  rapikan(pohon, false);
  return toHtml(pohon).replace(/\n/g, "&#10;") || "<p></p>";
};

// --- kesetaraan ---------------------------------------------------------------

type TSimpul = Record<string, unknown> & { type: string; value?: string; url?: string; children?: TSimpul[] };

/** Satu potongan teks dan format yang berlaku padanya. */
type TPotongan = [teks: string, format: string];

const FORMAT: Record<string, (simpul: TSimpul) => string> = {
  strong: () => "tebal",
  emphasis: () => "miring",
  delete: () => "coret",
  link: (simpul) => `tautan:${simpul.url}`,
};

/**
 * Isi sebaris sebagai deret potongan. Susunan sarangnya tidak penting
 * (`**[a](u)**` tampil sama dengan `[**a**](u)`), dan spasi tidak berformat.
 */
const potongan = (simpul: TSimpul, format: string[]): TPotongan[] => {
  // `toSorted` tidak ada di target TS repo ini; larik dari spread aman diurut di tempat.
  // oxlint-disable-next-line unicorn/no-array-sort
  const label = () => [...format].sort().join(" ");
  if (simpul.type === "text")
    return (simpul.value ?? "")
      .split(/(\s+)/)
      .filter(Boolean)
      .map((bagian) => (bagian.trim() ? [bagian, label()] : [" ", ""]));
  if (simpul.type === "break") return [["\n", ""]];
  if (simpul.type === "inlineCode") return [[simpul.value ?? "", `${label()} kode`]];
  if (simpul.type === "image") return [[String(simpul.alt ?? ""), `${label()} gambar:${simpul.url}`]];
  const tambahan = FORMAT[simpul.type]?.(simpul);
  return (simpul.children ?? []).flatMap((anak) => potongan(anak, tambahan ? [...format, tambahan] : format));
};

const sebaris = (anak: TSimpul[]): TPotongan[] => {
  const hasil: TPotongan[] = [];
  for (const [teks, format] of anak.flatMap((a) => potongan(a, []))) {
    const akhir = hasil[hasil.length - 1];
    // Spasi ganda, dan spasi di sekitar baris baru, tidak tampak.
    if (teks === " " && (!akhir || akhir[0] === "\n" || akhir[0].endsWith(" "))) continue;
    if (teks === "\n" && akhir) akhir[0] = akhir[0].trimEnd();
    const sebelum = hasil[hasil.length - 1];
    if (sebelum && teks !== "\n" && sebelum[0] !== "\n" && sebelum[1] === format) sebelum[0] += teks;
    else hasil.push([teks, format]);
  }
  const akhir = hasil[hasil.length - 1];
  if (akhir) akhir[0] = akhir[0].trimEnd();
  return hasil.filter(([teks]) => teks);
};

const BERISI_SEBARIS = new Set(["paragraph", "heading", "tableCell"]);

/** Bentuk yang dibandingkan: apa yang tampil, tanpa posisi dan gaya tulis. */
const bentuk = (simpul: TSimpul): unknown => {
  const { position: _posisi, spread: _renggang, data: _data, children, ...sisa } = simpul;
  if (!children) return sisa;
  if (BERISI_SEBARIS.has(simpul.type)) return { ...sisa, isi: sebaris(children) };
  return {
    ...sisa,
    children: children
      .filter((anak) => !(anak.type === "paragraph" && sebaris(anak.children ?? []).length === 0))
      .map(bentuk),
  };
};

const sidik = (markdown: string) => {
  const pohon = uraiMarkdown(markdown.trim()) as Nodes;
  pecahBaris(pohon);
  return JSON.stringify(bentuk(pohon as unknown as TSimpul));
};

/** True kalau dua sumber Markdown tampil sama (isi, format, tautan, baris baru). */
export const setaraMarkdown = (a: string, b: string): boolean => sidik(a) === sidik(b);
