/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: galat unggah yang seragam
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Pemeriksaan normalizeUploadError dan retryTransient. Jalankan dari packages/i18n:
 *
 *   cd packages/i18n
 *   pnpm exec tsx ../services/src/file/upload-error.check.ts
 */

import assert from "node:assert/strict";
import { getUploadErrorI18nKey, isTransientUploadError, normalizeUploadError, retryTransient } from "./upload-error";
import type { TUploadErrorCode } from "./upload-error";

const xml = (kode: string) => `<?xml version="1.0"?><Error><Code>${kode}</Code><Message>x</Message></Error>`;

const axiosError = (response?: { status: number; data: unknown }, code?: string) => ({
  isAxiosError: true,
  message: "boom",
  code,
  response,
});

// --- jaringan: tidak ada respons sama sekali (dulu dilempar sebagai undefined) --
{
  const e = normalizeUploadError(axiosError(undefined, "ERR_NETWORK"));
  assert.equal(e.code, "network");
  assert.ok(isTransientUploadError(e));
  assert.equal(normalizeUploadError(undefined).code, "unknown");
  assert.equal(normalizeUploadError(axiosError(undefined, "ECONNABORTED")).code, "timeout");
}

// --- MinIO membalas XML ---------------------------------------------------------
{
  assert.equal(normalizeUploadError(axiosError({ status: 400, data: xml("EntityTooLarge") })).code, "file_too_large");
  assert.equal(normalizeUploadError(axiosError({ status: 400, data: xml("EntityTooSmall") })).code, "empty_file");
  assert.equal(normalizeUploadError(axiosError({ status: 403, data: xml("AccessDenied") })).code, "forbidden");
  assert.equal(normalizeUploadError(axiosError({ status: 400, data: xml("ExpiredToken") })).code, "expired");
  assert.equal(normalizeUploadError(axiosError({ status: 503, data: xml("SlowDown") })).code, "server");
}

// --- Django membalas { error, code } -------------------------------------------
{
  const tipe = normalizeUploadError(
    axiosError({ status: 400, data: { error: "Invalid file type 'x/y' for ISSUE_DESCRIPTION.", status: false } })
  );
  assert.equal(tipe.code, "type_not_allowed");
  assert.equal(tipe.status, 400);
  assert.ok(!isTransientUploadError(tipe));

  const kuota = normalizeUploadError(
    axiosError({ status: 413, data: { error: "Kuota habis", code: "STORAGE_QUOTA_EXCEEDED" } })
  );
  assert.equal(kuota.code, "quota");
  assert.equal(kuota.error, "Kuota habis");

  assert.equal(normalizeUploadError(axiosError({ status: 502, data: "<html>Bad gateway</html>" })).code, "server");
  assert.equal(normalizeUploadError(axiosError({ status: 413, data: "" })).code, "file_too_large");
}

// --- pembatalan tidak dianggap galat sesaat -------------------------------------
{
  const e = normalizeUploadError({ __CANCEL__: true, message: "Upload canceled" });
  assert.equal(e.code, "cancelled");
  assert.ok(!isTransientUploadError(e));
}

// --- normalisasi idempoten ------------------------------------------------------
{
  const once = normalizeUploadError(axiosError(undefined, "ERR_NETWORK"));
  assert.deepEqual(normalizeUploadError(once), once);
}

// --- kunci pesan: tiap kode punya jawaban, pembatalan diam ----------------------
{
  const semua: TUploadErrorCode[] = [
    "cancelled",
    "network",
    "timeout",
    "file_too_large",
    "empty_file",
    "type_not_allowed",
    "expired",
    "quota",
    "forbidden",
    "server",
    "rejected",
    "unknown",
  ];
  const dariServer = new Set<TUploadErrorCode>(["cancelled", "quota", "rejected"]);
  for (const kode of semua) {
    const kunci = getUploadErrorI18nKey(kode);
    if (dariServer.has(kode)) assert.equal(kunci, null, kode);
    else assert.match(kunci ?? "", /^unggah_ui\.[a-z_]+$/, kode);
  }
}

// --- retryTransient -------------------------------------------------------------
const tidur: number[] = [];
const sleep = async (ms: number) => {
  tidur.push(ms);
};

const jalan = async () => {
  // sukses di percobaan ketiga: dua kali gagal sesaat
  let n = 0;
  const hasil = await retryTransient(
    async () => {
      n += 1;
      if (n < 3) throw axiosError(undefined, "ERR_NETWORK");
      return "ok";
    },
    { sleep, baseDelayMs: 100 }
  );
  assert.equal(hasil, "ok");
  assert.equal(n, 3);
  assert.deepEqual(tidur, [100, 200]);

  // galat tetap sesaat: menyerah sesudah retries, melempar bentuk yang sudah dinormalkan
  let m = 0;
  await assert.rejects(
    retryTransient(
      async () => {
        m += 1;
        throw axiosError({ status: 503, data: "" });
      },
      { sleep, retries: 1 }
    ),
    (e: unknown) => (e as { code: string }).code === "server"
  );
  assert.equal(m, 2);

  // galat permanen: tidak diulang sama sekali (kontrol negatif)
  let k = 0;
  await assert.rejects(
    retryTransient(
      async () => {
        k += 1;
        throw axiosError({ status: 400, data: { error: "Invalid file type ''" } });
      },
      { sleep }
    ),
    (e: unknown) => (e as { code: string }).code === "type_not_allowed"
  );
  assert.equal(k, 1);

  // pembatalan tidak diulang
  let c = 0;
  await assert.rejects(
    retryTransient(
      async () => {
        c += 1;
        throw { __CANCEL__: true };
      },
      { sleep }
    )
  );
  assert.equal(c, 1);

  console.log("upload-error.check.ts: semua lolos");
};

void jalan();
