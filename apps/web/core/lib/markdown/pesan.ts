/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Markdown pesan obrolan dan pengumuman
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Dialek Markdown `PesanLangsung.isi`: satu tempat untuk perender, pratinjau
 * tautan, penyunting, dan teks polos. Pasangannya di server:
 * `plane/utils/markdown_pesan.py`; kesamaan teks polos keduanya dijaga
 * `plane/tests/data/markdown_polos.json`.
 *
 * Tanpa impor beralias, supaya `notifikasi/teks.ts` tetap bisa dijalankan tsx.
 */

import type { Nodes, Parents, Root, RootContent } from "mdast";
import remarkGfm from "remark-gfm";
import remarkParse from "remark-parse";
import { unified } from "unified";
import type { Plugin, PluggableList } from "unified";

/**
 * Konstruksi CommonMark yang dimatikan karena membuat teks yang diketik orang hilang
 * atau berubah arti: HTML mentah dan entitas (`<jam 12>`, `&amp;` tetap teks), baris
 * menjorok jadi blok kode, `---` di bawah kalimat jadi judul, serta definisi tautan
 * dan catatan kaki (`[PENTING]: segera` tidak ditampilkan sama sekali).
 */
const KONSTRUKSI_MATI = [
  "htmlFlow",
  "htmlText",
  "characterReference",
  "codeIndented",
  "setextUnderline",
  "definition",
  "gfmFootnoteDefinition",
  "gfmFootnoteCall",
];

const remarkDialek: Plugin = function () {
  const data = this.data() as { micromarkExtensions?: unknown[] };
  (data.micromarkExtensions ??= []).push({ disable: { null: KONSTRUKSI_MATI } });
};

/** `~satu~` tetap teks: di kantor tilde berarti "kira-kira". */
export const PLUGIN_DIALEK: PluggableList = [[remarkGfm, { singleTilde: false }], remarkDialek];

/** Teks berbaris banyak jadi teks dan `break` bergantian. */
const barisan = (teks: string): RootContent[] => {
  const hasil: RootContent[] = [];
  for (const [i, baris] of teks.split("\n").entries()) {
    if (i > 0) hasil.push({ type: "break" });
    if (baris) hasil.push({ type: "text", value: baris });
  }
  return hasil;
};

/** Satu baris baru di sumber = satu baris baru di layar, seperti pesan teks biasa. */
export const pecahBaris = (simpul: Nodes): void => {
  if (!("children" in simpul)) return;
  const induk = simpul as Parents;
  induk.children = (induk.children as RootContent[]).flatMap((anak) => {
    if (anak.type === "text") return barisan(anak.value);
    pecahBaris(anak);
    return [anak];
  }) as Parents["children"];
};

export const remarkBarisBaru: Plugin<[], Root> = () => pecahBaris;

const pengurai = unified().use(remarkParse).use(PLUGIN_DIALEK).freeze();

// Kode dan alamat dibiarkan apa adanya; di luar keduanya `*` di antara angka bukan penanda miring.
const APA_ADANYA = /(```[\s\S]*?(?:```|$)|~~~[\s\S]*?(?:~~~|$)|`[^`\n]*`|https?:\/\/[^\s<>]+)/;

/** `10*20*30` itu ukuran, bukan miring. Pasangannya di server: `_lindungi_kali`. */
export const lindungiKali = (teks: string): string =>
  teks
    .split(APA_ADANYA)
    .map((bagian, i) => (i % 2 ? bagian : bagian.replace(/(?<=\d)\*(?=\d)/g, "\\*")))
    .join("");

export const uraiMarkdown = (teks: string): Root => {
  const sumber = lindungiKali(teks);
  return pengurai.runSync(pengurai.parse(sumber), sumber) as Root;
};

// --- teks polos ---------------------------------------------------------------

const sebaris = (simpul: Nodes): string => {
  if (simpul.type === "break") return "\n";
  if (simpul.type === "image") return simpul.alt ?? "";
  if ("value" in simpul) return simpul.value;
  return "children" in simpul ? (simpul.children as Nodes[]).map(sebaris).join("") : "";
};

const gabung = (bagian: string[], pemisah: string) => bagian.filter(Boolean).join(pemisah);

const blok = (simpul: Nodes): string => {
  switch (simpul.type) {
    case "list":
      return simpul.children
        .map((butir, i) => {
          const awalan = simpul.ordered ? `${(simpul.start ?? 1) + i}. ` : "• ";
          const centang = typeof butir.checked === "boolean" ? (butir.checked ? "☑ " : "☐ ") : "";
          return awalan + centang + gabung(butir.children.map(blok), "\n").replace(/\n/g, "\n  ");
        })
        .join("\n");
    case "paragraph":
    case "heading":
      return sebaris(simpul).trim();
    case "code":
      return simpul.value;
    case "thematicBreak":
      return "---";
    case "table":
      return simpul.children.map((tr) => tr.children.map((sel) => sebaris(sel).trim()).join(" | ")).join("\n");
    default:
      return "children" in simpul ? gabung((simpul.children as Nodes[]).map(blok), "\n\n") : sebaris(simpul);
  }
};

/** Teks tanpa sintaks Markdown, baris dipertahankan. Untuk cuplikan, kutipan, dan pemberitahuan. */
export const teksTanpaMarkdown = (isi: string | null | undefined): string => {
  const sumber = (isi ?? "").trim();
  // Tidak pernah mengosongkan pesan yang ada isinya (mis. hanya "#").
  return sumber ? blok(uraiMarkdown(sumber)).trim() || sumber : "";
};

// --- tautan -------------------------------------------------------------------

/** Satu-satunya skema yang boleh jadi sesuatu yang bisa diklik (lihat `chat/tautan.ts`). */
export const bolehDiklik = (alamat: string | null | undefined): boolean => /^(https?:\/\/|mailto:)/i.test(alamat ?? "");

/** Id orang dari tautan profil (`.../<slug>/profile/<uuid>`), bentuk sebutan yang disimpan penyunting. */
export const idProfil = (alamat: string | null | undefined): string | undefined =>
  /\/profile\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\/?$/i.exec(alamat ?? "")?.[1];

/** Alamat semua tautan di teks, urut kemunculan. Yang di dalam kode tidak ikut. */
export const tautanDalamMarkdown = (isi: string): string[] => {
  const hasil: string[] = [];
  const jelajah = (simpul: Nodes) => {
    if (simpul.type === "link") hasil.push(simpul.url);
    else if ("children" in simpul) (simpul.children as Nodes[]).forEach(jelajah);
  };
  jelajah(uraiMarkdown(isi));
  return hasil;
};
