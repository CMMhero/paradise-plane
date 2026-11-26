/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Markdown pesan obrolan dan pengumuman
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readFileSync } from "node:fs";
import { toHtml } from "hast-util-to-html";
import remarkParse from "remark-parse";
import remarkRehype from "remark-rehype";
import { unified } from "unified";
import { describe, expect, it } from "vite-plus/test";
import { remarkRujukan } from "@/app/(all)/[workspaceSlug]/(projects)/chat/rujukan-markdown";
import type { TSumberRujukan } from "@/app/(all)/[workspaceSlug]/(projects)/chat/sebut";
import { alamatDariMarkdown } from "@/components/pratinjau-tautan/alamat";
import {
  PLUGIN_DIALEK,
  bolehDiklik,
  idProfil,
  remarkBarisBaru,
  tautanDalamMarkdown,
  teksTanpaMarkdown,
} from "@/lib/markdown/pesan";

/** Berkas yang sama dibaca `test_markdown_pesan.py`: satu aturan, dua bahasa. */
const KASUS: { nama: string; markdown: string; polos: string }[] = JSON.parse(
  readFileSync(new URL("../../api/plane/tests/data/markdown_polos.json", import.meta.url), "utf8")
);

const ORANG = "6b1f0c2e-1111-4222-8333-944444444444";
const SUMBER: TSumberRujukan = {
  orang: [{ id: ORANG, nama: "Budi Santoso" }],
  kanal: [{ id: "k1", nama: "umum" }],
  tugas: [{ id: "t1", nomor: "GDG-12" }],
  semua: true,
};

/** Rangkaian plugin yang sama dengan `IsiMarkdown`, sampai HTML. */
const render = (markdown: string, sumber: TSumberRujukan = SUMBER) => {
  const proses = unified()
    .use(remarkParse)
    .use(PLUGIN_DIALEK)
    .use(remarkRujukan, sumber)
    .use(remarkBarisBaru)
    .use(remarkRehype);
  return toHtml(proses.runSync(proses.parse(markdown)) as Parameters<typeof toHtml>[0]);
};

const pil = (jenis: string, id: string, isi: string) => `<span data-rujukan="${jenis}" data-id="${id}">${isi}</span>`;

describe("teksTanpaMarkdown", () => {
  it.each(KASUS)("$nama", ({ markdown, polos }) => {
    expect(teksTanpaMarkdown(markdown)).toBe(polos);
  });
  it("kosong untuk null", () => {
    expect(teksTanpaMarkdown(null)).toBe("");
  });
});

describe("sebutan dan rujukan di dalam Markdown", () => {
  it("jalan di dalam tebal, miring, daftar, dan kutipan", () => {
    const html = render("**@Budi Santoso** dan _#umum_\n\n* @all cek #GDG-12\n\n> @Budi Santoso");
    expect(html).toContain(`<strong>${pil("sebut", ORANG, "@Budi Santoso")}</strong>`);
    expect(html).toContain(`<em>${pil("kanal", "k1", "#umum")}</em>`);
    expect(html).toContain(`<li>${pil("semua", "", "@all")} cek ${pil("tugas", "t1", "#GDG-12")}</li>`);
    expect(html.match(/data-rujukan="sebut"/g)).toHaveLength(2);
  });

  it("tidak jalan di dalam kode, dan alamat di sana tidak jadi tautan", () => {
    const html = render("`@Budi Santoso #umum http://a.id`\n\n```\n@all http://b.id\n```");
    expect(html).not.toContain("data-rujukan");
    expect(html).not.toContain("<a ");
  });

  it("yang tidak tercatat di muatan tetap teks", () => {
    expect(render("@Budi Santoso #umum @all", {})).toBe("<p>@Budi Santoso #umum @all</p>");
  });

  it("tautan profil, kanal, dan work item jadi pil", () => {
    const html = render(
      `[@Siti](https://x.id/ws/profile/${ORANG}) [#umum](https://x.id/ws/chat/?ruang=k1) [#GDG-12](https://x.id/ws/browse/GDG-12/)`,
      { ...SUMBER, orang: [] }
    );
    expect(html).toContain(pil("sebut", ORANG, "@Siti"));
    expect(html).toContain(pil("kanal", "k1", "#umum"));
    expect(html).toContain(pil("tugas", "t1", "#GDG-12"));
    expect(html).not.toContain("<a ");
  });

  it("tautan biasa dan alamat telanjang tetap tautan, teks di dalamnya tidak disorot", () => {
    const html = render("lihat https://a.id/x. dan (lihat:http://b.id) dan [#umum](https://c.id)");
    expect(html).toContain('<a href="https://a.id/x">https://a.id/x</a>.');
    expect(html).toContain('<a href="http://b.id">http://b.id</a>)');
    expect(html).toContain('<a href="https://c.id">#umum</a>');
    expect(html).not.toContain("data-rujukan");
  });

  it("baris baru tetap baris baru, di paragraf maupun butir daftar", () => {
    expect(render("a\nb")).toBe("<p>a<br>\nb</p>");
    expect(render("* a\n  b")).toContain("<li>a<br>\nb</li>");
  });

  it("HTML yang diketik tetap tampil sebagai teks", () => {
    expect(render("<img src=x onerror=alert(1)>")).toBe("<p>&#x3C;img src=x onerror=alert(1)></p>");
    expect(render("<script>\nalert(1)\n</script>")).not.toContain("<script>");
  });
});

describe("tautan", () => {
  it("hanya http, https, dan mailto yang boleh diklik", () => {
    for (const aman of ["http://a.id", "HTTPS://a.id", "mailto:a@a.id"]) expect(bolehDiklik(aman)).toBe(true);
    for (const jahat of ["javascript:alert(1)", "data:text/html,x", "file:///etc/passwd", "/relatif", "", undefined])
      expect(bolehDiklik(jahat)).toBe(false);
  });

  it("id profil dibaca dari tautan sebutan", () => {
    expect(idProfil(`https://x.id/ws/profile/${ORANG}`)).toBe(ORANG);
    expect(idProfil(`https://x.id/ws/profile/${ORANG}/`)).toBe(ORANG);
    expect(idProfil("https://x.id/profile/saya")).toBeUndefined();
  });

  it("alamat di dalam kode tidak ikut", () => {
    expect(tautanDalamMarkdown("**https://a.id** `https://b.id` [c](https://c.id)")).toEqual([
      "https://a.id",
      "https://c.id",
    ]);
  });

  it("kartu pratinjau melewati sebutan, kode, dan mailto", () => {
    const isi = `[@Siti](https://x.id/ws/profile/${ORANG}) a@b.id \`https://kode.id\` https://luar.id/a`;
    expect(alamatDariMarkdown(isi)).toEqual(["https://luar.id/a"]);
  });
});
