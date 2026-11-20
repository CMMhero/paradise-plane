/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Pemeriksaan teksDariHtml. Jalankan DARI packages/i18n:
 *
 *   cd packages/i18n
 *   pnpm exec tsx "../../apps/web/app/(all)/[workspaceSlug]/(projects)/chat/kartu/teks-html.check.ts"
 */

import assert from "node:assert/strict";
import { bacaKartuTugas } from "./muatan";
import { teksDariHtml } from "./teks-html";

const NAMA: Record<string, string> = { "u-1": "Budi Santoso" };
const label = (jenis: string, id: string) =>
  jenis === "everyone_mention" ? "@all" : jenis === "user_mention" ? `@${NAMA[id] ?? "?"}` : `#${id}`;

// Contoh dari user: paragraf editor dengan sebutan.
assert.equal(
  teksDariHtml(
    '<p class="editor-paragraph-block" data-id="b42b">Pagi mas <mention-component id="m1" entity_name="user_mention" entity_identifier="u-1"></mention-component></p>',
    label
  ),
  "Pagi mas @Budi Santoso"
);
// Paragraf jadi baris, entitas didekode, tag lain dibuang.
assert.equal(
  teksDariHtml("<p>Cek &amp; balas&nbsp;ya</p><p></p><ul><li><strong>satu</strong></li><li>dua</li></ul>", label),
  "Cek & balas ya\nsatu\ndua"
);
assert.equal(teksDariHtml("<p>a<br>b &lt;c&gt; &#39;d&#x27;</p>", label), "a\nb <c> 'd'");
assert.equal(
  teksDariHtml('<p><mention-component entity_name="everyone_mention" entity_identifier="all"/> rapat</p>', label),
  "@all rapat"
);
// Cuplikan lama yang terpotong di tengah tag: sisa tag dibuang, ditandai elipsis.
assert.equal(
  teksDariHtml('<p class="editor-paragraph-block">Pagi mas <mention-component id="m1" entity_name="user_men…', label),
  "Pagi mas…"
);
// Teks biasa tidak disentuh.
assert.equal(teksDariHtml("a < b > c", label), "a < b > c");
assert.equal(teksDariHtml("Done", label), "Done");
// Tidak ada tag yang lolos sebagai teks.
assert.ok(!teksDariHtml('<img src=x onerror="alert(1)"><p>hai</p>', label).includes("<"));

// Kartu lama ber-HTML terbaca sebagai teks, termasuk daftar perubahan.
const kartu = bacaKartuTugas(
  {
    aksi: "komentar",
    detail: {
      komentar:
        '<p>Halo <mention-component entity_name="user_mention" entity_identifier="u-1"></mention-component></p>',
      perubahan: [{ field: "description", lama: "<p>lama</p>", baru: "<p>baru</p><p>dua</p>" }],
    },
  },
  label
);
assert.equal(kartu.detail.komentar, "Halo @Budi Santoso");
assert.deepEqual(kartu.detail.perubahan, ["description → baru dua"]);

console.log("teks-html: semua pemeriksaan lolos");
