/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pemeriksaan pesan galat media
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Jalankan DARI packages/i18n, karena tsx hanya terpasang di situ:
 *   pnpm exec tsx "../../apps/web/app/(all)/[workspaceSlug]/(projects)/chat/galat-media.check.ts"
 */

import assert from "node:assert/strict";
import { pesanGalatMedia } from "./galat-media";

// Halaman http:// menang atas segalanya: di situ galatnya TypeError yang sama
// sekali tidak menyebut mikrofon, jadi menebak dari nama galat akan meleset.
{
  const p = pesanGalatMedia(new TypeError("navigator.mediaDevices is undefined"), false);
  assert.match(p, /HTTPS/, "halaman tanpa konteks aman harus menyebut HTTPS");
}

// Izin ditolak: yang dibutuhkan orangnya adalah letak tombolnya, bukan nama galat.
{
  const p = pesanGalatMedia({ name: "NotAllowedError" }, true);
  assert.match(p, /gembok/, "izin ditolak harus menunjukkan cara mengizinkan");
}

// Tidak ada mikrofon sama sekali. Menyuruh orangnya mengubah izin percuma.
{
  const p = pesanGalatMedia({ name: "NotFoundError" }, true);
  assert.match(p, /tidak ada mikrofon/i, "tanpa perangkat, sebutkan perangkatnya yang tidak ada");
  assert.doesNotMatch(p, /gembok/, "jangan menyuruh mengubah izin kalau perangkatnya memang tidak ada");
}

// Dipakai aplikasi lain (Zoom, Teams) adalah kasus kantor yang paling sering.
{
  const p = pesanGalatMedia({ name: "NotReadableError" }, true);
  assert.match(p, /aplikasi lain/, "perangkat terkunci harus menyebut aplikasi lain");
}

// PERNAH SALAH: sebab yang tidak dikenal dilaporkan sebagai gangguan jaringan.
// Kalimat itu mengirim orang mencari bug di tempat yang salah selama berjam-jam.
{
  const p = pesanGalatMedia({ name: "GalatBaruYangBelumAda" }, true);
  assert.match(p, /GalatBaruYangBelumAda/, "sebab tak dikenal tetap disebut apa adanya");
  assert.doesNotMatch(p, /jaringan/i, "jangan pernah menuduh jaringan untuk kegagalan mikrofon");
}

// eslint-disable-next-line no-console
console.log("pesanGalatMedia: semua pemeriksaan lulus");
