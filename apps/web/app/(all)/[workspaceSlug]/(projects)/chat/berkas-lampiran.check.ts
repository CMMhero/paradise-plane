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

// --- seret -------------------------------------------------------------------
{
  assert.equal(seretBerkas({ types: ["Files"] } as unknown as DataTransfer), true);
  // Teks atau tautan yang diseret bukan lampiran.
  assert.equal(seretBerkas({ types: ["text/plain"] } as unknown as DataTransfer), false);
  assert.equal(seretBerkas(null), false);
}

console.log("berkas-lampiran: semua pemeriksaan lulus");
