/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: perender Markdown pengumuman dan obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vite-plus/test";
import { IsiMarkdown } from "@/components/pengumuman/isi-markdown";

// Pemicu profil menarik store MobX; yang diuji di sini hanya apa yang dibungkusnya.
vi.mock("@/components/member-profile", () => ({
  MemberProfileTrigger: ({ userId, children }: { userId: string; children: ReactNode }) => (
    <button data-profil={userId}>{children}</button>
  ),
}));

const ORANG = "6b1f0c2e-1111-4222-8333-944444444444";

describe("IsiMarkdown", () => {
  it("merender format, tabel, dan nomor awal daftar", () => {
    const html = renderToStaticMarkup(<IsiMarkdown teks={"**a** ~~b~~\n\n3. c\n\n| d |\n| - |\n| e |"} />);
    expect(html).toContain("<strong>a</strong>");
    expect(html).toContain("<del>b</del>");
    expect(html).toContain('<ol start="3"');
    expect(html).toMatch(/<td[^>]*>e<\/td>/);
  });

  it("HTML yang diketik tampil sebagai teks, gambar tidak dimuat", () => {
    const html = renderToStaticMarkup(
      <IsiMarkdown teks={"<img src=x onerror=alert(1)> ![denah](https://x.id/d.png)"} />
    );
    expect(html).toContain("&lt;img src=x onerror=alert(1)&gt;");
    expect(html).not.toContain("<img");
    expect(html).toContain('href="https://x.id/d.png"');
  });

  it("skema selain http, https, dan mailto tidak pernah jadi href", () => {
    const html = renderToStaticMarkup(
      <IsiMarkdown teks={"[a](javascript:alert(1)) [b](data:text/html,x) [c](/relatif) <vbscript:x>"} />
    );
    expect(html).not.toContain("href=");
    expect(html).not.toContain("<a");
  });

  it("sebutan penyunting membuka profil", () => {
    const html = renderToStaticMarkup(<IsiMarkdown teks={`Halo [@Budi](https://x.id/ws/profile/${ORANG})`} />);
    expect(html).toContain(`<button data-profil="${ORANG}">`);
    expect(html).toContain("@Budi");
    expect(html).not.toContain("<a ");
  });

  it.each(["kartu", "gelembung", "terang"] as const)("pil dari muatan digambar pemanggil (%s)", (nada) => {
    const html = renderToStaticMarkup(
      <IsiMarkdown
        teks={"* **@Budi** di `@Budi`"}
        nada={nada}
        sumber={{ orang: [{ id: ORANG, nama: "Budi" }] }}
        renderPil={(pil) => <mark data-jenis={pil.jenis}>{pil.isi}</mark>}
      />
    );
    expect(html.match(/<mark/g)).toHaveLength(1);
    expect(html).toContain('<strong><mark data-jenis="sebut">@Budi</mark></strong>');
    expect(html).toMatch(/<code[^>]*>@Budi<\/code>/);
  });

  it("gelembung saya memakai latar gelap tembus untuk kode, bukan warna layer", () => {
    const html = renderToStaticMarkup(<IsiMarkdown teks={"`x`"} nada="terang" />);
    expect(html).toContain("bg-black/20");
    expect(html).not.toContain("bg-layer");
  });
});
