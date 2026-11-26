/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Markdown pengumuman pulang-pergi lewat penyunting
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Jalan yang sama dengan menyunting di halaman Pengumuman: Markdown tersimpan ->
 * `htmlPenyunting` -> skema penyunting (daftar ekstensi yang dipakai server Live,
 * diurai tanpa peramban) -> `getHTML` -> `convertHTMLToMarkdown`.
 */

import { generateHTML, generateJSON } from "@tiptap/html";
import { describe, expect, it } from "vite-plus/test";
import { CoreEditorExtensionsWithoutProps } from "@plane/editor/lib";
import { convertHTMLToMarkdown } from "@plane/utils";
import type { TCustomComponentsMetaData } from "@plane/utils";
import { teksTanpaMarkdown } from "@/lib/markdown/pesan";
import { htmlPenyunting, setaraMarkdown } from "@/lib/markdown/penyunting";

const ORANG = "6b1f0c2e-1111-4222-8333-944444444444";
const PROFIL = `https://x.id/ws/profile/${ORANG}`;
const META: TCustomComponentsMetaData = {
  file_assets: [],
  user_mentions: [{ id: ORANG, display_name: "Budi Santoso", url: PROFIL }],
  reference_mentions: [{ id: "k1", label: "umum", url: "https://x.id/ws/chat/?ruang=k1" }],
};

/** Penyunting pengumuman mematikan gambar sebaris (`disabledExtensions`). */
const EKSTENSI = CoreEditorExtensionsWithoutProps.filter(
  (e) => !["image", "imageComponent"].includes(e.name)
  // pnpm memberi `@tiptap/html` salinan tipe @tiptap/core sendiri; objeknya sama.
) as unknown as Parameters<typeof generateHTML>[1];

/** Yang dilakukan penyunting pada isi awalnya, lalu `getMarkDown()`. */
const lewatPenyunting = (html: string) => {
  const dok = generateJSON(html, EKSTENSI, { preserveWhitespace: true });
  return convertHTMLToMarkdown({
    description_html: generateHTML(dok, EKSTENSI),
    metaData: META,
  }).trim();
};

const SELAMAT: Record<string, string> = {
  "pengumuman produksi":
    "Dengan ini kami menyampaikan **selamat bergabung kepada Bapak X sebagai Plant Manager**.\n\nTerhitung mulai **Selasa, 1 Desember 2026**, beliau bertugas.",
  "teks lama polos dua baris": "Besok libur.\nKantor tutup <jam 12> & buka lusa.",
  "format sebaris": "**tebal** *miring* ~~coret~~ `kode` ***dua sekaligus***",
  "miring berisi tebal dan tautan": "*mohon **segera** baca [panduan](https://x.id/p) ini*",
  "daftar butir": "Bawa:\n\n- KTP\n- NPWP",
  "daftar bernomor": "1. satu\n2. dua",
  "daftar bersarang": "- induk\n  - anak\n- lain",
  "daftar centang": "- [ ] belum\n- [x] sudah",
  "tautan dan alamat telanjang": "Lihat [jadwal](https://x.id/a_b) atau https://x.id/c_d_e.",
  "sebutan orang": `Selamat [@Budi Santoso](${PROFIL}) dan tim`,
  "sebutan di dalam tebal dan daftar": `- **[@Budi Santoso](${PROFIL})** hadir`,
  "kanal dan @all": "@all cek [#umum](https://x.id/ws/chat/?ruang=k1)",
  "baris paksa": "satu\\\ndua",
  "judul dan kutipan": "## Agenda\n\n> kata dia\n> lagi",
  "blok kode berbaris kosong": "```\nsatu\n\n  dua **apa adanya**\n```",
  "garis pemisah": "atas\n\n---\n\nbawah",
  tabel: "| a | b |\n| - | - |\n| 1 | **2** |",
  "sebutan rusak lama": "Halo [@]() semua",
};

describe("pulang-pergi lewat penyunting", () => {
  it.each(Object.entries(SELAMAT))("%s", (_nama, markdown) => {
    const html = htmlPenyunting(markdown);
    // Satu baris, supaya tiptap-markdown tidak mengurainya sebagai Markdown.
    expect(html).not.toContain("\n");
    expect(html).toMatch(/^<(p|ul|ol|h[1-6]|blockquote|pre|table|hr)\b/);

    const hasil = lewatPenyunting(html);
    expect(setaraMarkdown(markdown, hasil), hasil).toBe(true);
    expect(teksTanpaMarkdown(hasil).replace(/\s+/g, " ")).toBe(teksTanpaMarkdown(markdown).replace(/\s+/g, " "));
    // Putaran kedua tidak mengubah apa pun lagi.
    expect(setaraMarkdown(hasil, lewatPenyunting(htmlPenyunting(hasil)))).toBe(true);
  });
});

/** Yang tidak selamat HARUS terdeteksi, supaya halaman memakai kotak teks Markdown. */
const TIDAK_SELAMAT: Record<string, string> = {
  "tanda bintang yang sengaja di-escape": "tulis \\*apa adanya\\*",
  gambar: "![denah](https://x.id/d.png)",
};

describe("yang tidak selamat terdeteksi", () => {
  it.each(Object.entries(TIDAK_SELAMAT))("%s", (_nama, markdown) => {
    expect(setaraMarkdown(markdown, lewatPenyunting(htmlPenyunting(markdown)))).toBe(false);
  });
});

describe("setaraMarkdown", () => {
  it("menerima gaya tulis yang berbeda", () => {
    expect(setaraMarkdown("- a\n- b", "* a\n\n* b")).toBe(true);
    expect(setaraMarkdown("a\nb", "a\\\nb")).toBe(true);
    expect(setaraMarkdown("_a_ x", "*a*  x")).toBe(true);
    expect(setaraMarkdown("**[a](https://a.id)** *b c*", "[**a**](https://a.id) *b* *c*")).toBe(true);
  });
  it("menolak isi, format, tautan, atau baris yang berubah", () => {
    expect(setaraMarkdown("**a**", "a")).toBe(false);
    expect(setaraMarkdown("[a](https://a.id)", "[a](https://b.id)")).toBe(false);
    expect(setaraMarkdown("a\nb", "a b")).toBe(false);
    expect(setaraMarkdown("- a\n- b", "- a")).toBe(false);
    expect(setaraMarkdown("- [x] a", "- [ ] a")).toBe(false);
    expect(setaraMarkdown("**a** b", "**a b**")).toBe(false);
    expect(setaraMarkdown("a\n\n---\n\nb", "a\n\nb")).toBe(false);
  });
});

const sebut = (jenis: string, id: string) =>
  `<mention-component id="m1" entity_identifier="${id}" entity_name="${jenis}"></mention-component>`;
const keMarkdown = (html: string) => lewatPenyunting(html).replace(/[ \t]+/g, " ");

describe("yang baru diketik di penyunting", () => {
  it("sebutan orang, @all, dan kanal tidak jadi tautan rusak", () => {
    const hasil = keMarkdown(
      `<p>${sebut("user_mention", ORANG)} ${sebut("everyone_mention", "all")} ${sebut("channel_mention", "k1")}</p>`
    );
    expect(hasil).toBe(`[@Budi Santoso](${PROFIL}) @all [#umum](https://x.id/ws/chat/?ruang=k1)`);
    expect(hasil).not.toContain("[@]()");
  });

  it("miring dan garis bawah tidak membuang isi di dalamnya", () => {
    const hasil = keMarkdown(
      '<p><em>baca <a href="https://x.id/p">panduan</a> <strong>segera</strong></em> <u>dan <strong>catat</strong></u></p>'
    );
    expect(teksTanpaMarkdown(hasil)).toBe("baca panduan segera dan catat");
    expect(hasil).toContain("(https://x.id/p)");
    expect(hasil).toContain("**catat**");
  });
});
