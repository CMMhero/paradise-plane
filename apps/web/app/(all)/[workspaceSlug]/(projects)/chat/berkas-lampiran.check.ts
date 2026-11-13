/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: lampiran Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Pemeriksaan aturan lampiran (pilih, tempel, seret). Jalankan dari packages/i18n:
 *
 *   cd packages/i18n
 *   pnpm exec tsx "../../apps/web/app/(all)/[workspaceSlug]/(projects)/chat/berkas-lampiran.check.ts"
 */

import assert from "node:assert/strict";
import { BATAS_LAMPIRAN, berkasDariTempel, pilahBerkas, seretBerkas } from "./berkas-lampiran";

const MB = 1024 * 1024;
const berkas = (nama: string, ukuran: number, type = "image/png") => new File([new Uint8Array(ukuran)], nama, { type });

// --- batas ukuran dan jumlah --------------------------------------------------
{
  const { terima, tolak } = pilahBerkas([berkas("a.png", 10), berkas("besar.mp4", 6 * MB)], 0, 5 * MB);
  assert.deepEqual(
    terima.map((f) => f.name),
    ["a.png"]
  );
  assert.deepEqual(tolak, [{ jenis: "terlalu-besar", nama: "besar.mp4" }]);
}
{
  // Sudah ada 4: hanya satu lagi yang diterima, sisanya ditolak karena jumlah.
  const { terima, tolak } = pilahBerkas([berkas("1.png", 1), berkas("2.png", 1)], BATAS_LAMPIRAN - 1, MB);
  assert.equal(terima.length, 1);
  assert.deepEqual(tolak, [{ jenis: "terlalu-banyak", nama: "2.png" }]);
}

// --- tempel ------------------------------------------------------------------
{
  // oxlint-disable-next-line unicorn/consistent-function-scoping -- kept as is: restructuring it is out of scope for this release
  const item = (f: File | null, kind = "file") => ({ kind, getAsFile: () => f });
  const data = {
    items: [item(berkas("image.png", 3)), item(berkas("laporan.pdf", 3, "application/pdf")), item(null, "string")],
  } as unknown as DataTransfer;
  const hasil = berkasDariTempel(data);
  assert.equal(hasil.length, 2);
  // Tangkapan layar "image.png" diberi nama unik supaya tidak kembar.
  assert.match(hasil[0].name, /^tempelan-.+-1\.png$/);
  assert.equal(hasil[0].type, "image/png");
  assert.equal(hasil[1].name, "laporan.pdf");
  assert.deepEqual(berkasDariTempel(null), []);
}
{
  // items kosong tapi files terisi (beberapa peramban): tetap terbaca
  const dariFiles = { items: [], files: [berkas("foto.jpg", 2, "image/jpeg")] } as unknown as DataTransfer;
  assert.deepEqual(
    berkasDariTempel(dariFiles).map((f) => f.name),
    ["foto.jpg"]
  );
  // getAsFile() bisa mengembalikan null untuk item berjenis file
  const nullFile = { items: [{ kind: "file", getAsFile: () => null }] } as unknown as DataTransfer;
  assert.deepEqual(berkasDariTempel(nullFile), []);
  // salin sel Excel: teks + gambar generik. Tempel teks harus jalan, tidak ada lampiran.
  const excel = {
    items: [{ kind: "file", getAsFile: () => berkas("image.png", 3) }],
    getData: () => "a\tb",
  } as unknown as DataTransfer;
  assert.deepEqual(berkasDariTempel(excel), []);
  // berkas bernama sungguhan tetap lampiran walau ada teks (salin berkas di Finder)
  const finder = {
    items: [{ kind: "file", getAsFile: () => berkas("laporan.pdf", 3, "application/pdf") }],
    getData: () => "laporan.pdf",
  } as unknown as DataTransfer;
  assert.equal(berkasDariTempel(finder).length, 1);
}

// --- seret -------------------------------------------------------------------
{
  assert.equal(seretBerkas({ types: ["Files"] } as unknown as DataTransfer), true);
  // Teks atau tautan yang diseret bukan lampiran.
  assert.equal(seretBerkas({ types: ["text/plain"] } as unknown as DataTransfer), false);
  assert.equal(seretBerkas(null), false);
}

console.log("berkas-lampiran: semua pemeriksaan lulus");
