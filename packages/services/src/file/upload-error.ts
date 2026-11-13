/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: galat unggah yang seragam
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Fungsi murni tanpa impor, diperiksa lewat tsx (upload-error.check.ts).
 *
 * Kenapa ada: layanan unggah dulu melempar `error?.response?.data`. Untuk galat
 * jaringan (tanpa respons) itu `undefined`; untuk galat MinIO itu string XML;
 * untuk galat Django itu `{ error }`. Pemanggil tidak punya cara membedakannya,
 * jadi hasilnya toast generik atau tidak ada sama sekali, dan kegagalan sesaat
 * (sambungan putus, proxy 502) tidak pernah dicoba ulang.
 */

export type TUploadErrorCode =
  | "cancelled"
  | "network"
  | "timeout"
  | "file_too_large"
  | "empty_file"
  | "type_not_allowed"
  | "expired"
  | "quota"
  | "forbidden"
  | "server"
  | "rejected"
  | "unknown";

/** Bentuk tunggal yang dilempar semua layanan unggah. `error` tetap teks, seperti galat API lain. */
export type TUploadError = {
  error: string;
  code: TUploadErrorCode;
  status?: number;
};

type TAnyRecord = Record<string, unknown>;

const isRecord = (value: unknown): value is TAnyRecord => typeof value === "object" && value !== null;

/** Kode galat S3/MinIO dari badan XML, mis. `<Code>EntityTooLarge</Code>`. */
const readS3Code = (body: unknown): string | undefined => {
  if (typeof body !== "string") return undefined;
  return /<Code>([^<]+)<\/Code>/.exec(body)?.[1];
};

const fromS3Code = (s3Code: string): TUploadErrorCode | undefined => {
  switch (s3Code) {
    case "EntityTooLarge":
    case "MaxMessageLengthExceeded":
      return "file_too_large";
    case "EntityTooSmall":
      return "empty_file";
    case "ExpiredToken":
    case "RequestTimeTooSkewed":
    case "InvalidPolicyDocument":
      return "expired";
    case "AccessDenied":
    case "SignatureDoesNotMatch":
      return "forbidden";
    case "SlowDown":
    case "ServiceUnavailable":
    case "InternalError":
      return "server";
    default:
      return undefined;
  }
};

const fromServerCode = (code: unknown, message: string): TUploadErrorCode | undefined => {
  if (typeof code === "string") {
    if (code === "FILE_TOO_LARGE") return "file_too_large";
    if (code === "EMPTY_FILE") return "empty_file";
    if (code.includes("QUOTA") || code.includes("DORMANT") || code.includes("LIMIT")) return "quota";
  }
  if (/invalid file type/i.test(message)) return "type_not_allowed";
  return undefined;
};

const fromStatus = (status: number | undefined): TUploadErrorCode => {
  if (status === undefined) return "unknown";
  if (status === 408 || status === 504) return "timeout";
  if (status === 413) return "file_too_large";
  if (status === 401 || status === 403) return "forbidden";
  if (status === 429 || status >= 500) return "server";
  if (status >= 400) return "rejected";
  return "unknown";
};

const KNOWN_CODES: ReadonlySet<string> = new Set<TUploadErrorCode>([
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
]);

/** Apa pun yang tertangkap saat mengunggah, dijadikan satu bentuk. Tidak pernah melempar. */
export const normalizeUploadError = (raw: unknown): TUploadError => {
  if (isRecord(raw) && typeof raw.error === "string" && KNOWN_CODES.has(raw.code as string)) {
    // sudah dinormalkan (mis. dilempar ulang oleh lapisan di atasnya)
    return raw as TUploadError;
  }

  if (raw === undefined || raw === null) return { error: "Unknown upload error", code: "unknown" };

  if (isRecord(raw) && raw["__CANCEL__"] === true) return { error: "Upload canceled", code: "cancelled" };

  const response = isRecord(raw) && isRecord(raw.response) ? raw.response : undefined;
  const status = typeof response?.status === "number" ? response.status : undefined;
  const body = response ? response.data : isRecord(raw) && "error" in raw ? raw : undefined;

  const bodyMessage = isRecord(body) && typeof body.error === "string" ? body.error : undefined;
  const s3Code = readS3Code(body);

  const code: TUploadErrorCode =
    (s3Code ? fromS3Code(s3Code) : undefined) ??
    (isRecord(body) ? fromServerCode(body.code, bodyMessage ?? "") : undefined) ??
    (response ? fromStatus(status) : undefined) ??
    (isRecord(raw) && (raw.code === "ECONNABORTED" || raw.code === "ETIMEDOUT") ? "timeout" : undefined) ??
    // axios sets code ERR_NETWORK / no response when the request never got an answer (offline, CORS, reset)
    (isRecord(raw) && (raw.code === "ERR_NETWORK" || raw.isAxiosError === true) && !response ? "network" : undefined) ??
    "unknown";

  const message =
    bodyMessage ??
    (s3Code
      ? `Storage error: ${s3Code}`
      : isRecord(raw) && typeof raw.message === "string"
        ? raw.message
        : "Upload failed");

  return { error: message, code, ...(status !== undefined ? { status } : {}) };
};

/** Kegagalan yang layak dicoba lagi: tidak ada jawaban, kehabisan waktu, atau server sibuk. */
export const isTransientUploadError = (error: TUploadError): boolean =>
  error.code === "network" || error.code === "timeout" || error.code === "server";

type TRetryOptions = {
  /** percobaan ulang sesudah yang pertama */
  retries?: number;
  baseDelayMs?: number;
  /** diganti saat pengujian */
  sleep?: (ms: number) => Promise<void>;
};

const defaultSleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/**
 * Menjalankan `run`, mengulang hanya untuk kegagalan sesaat, dengan jeda yang
 * berlipat. Galat yang dilempar selalu sudah dinormalkan. Hanya untuk langkah
 * yang AMAN diulang: mengirim ke URL presigned dan menandai aset terunggah.
 * Jangan dipakai untuk langkah yang membuat baris (POST pembuat aset).
 */
export const retryTransient = async <T>(run: () => Promise<T>, options: TRetryOptions = {}): Promise<T> => {
  const { retries = 2, baseDelayMs = 800, sleep = defaultSleep } = options;
  // recursion instead of a loop: every attempt waits for the one before it by design
  const attempt = async (index: number): Promise<T> => {
    try {
      return await run();
    } catch (raw) {
      const error = normalizeUploadError(raw);
      if (index >= retries || !isTransientUploadError(error)) throw error;
      await sleep(baseDelayMs * 2 ** index);
      return attempt(index + 1);
    }
  };
  return attempt(0);
};

/**
 * Kunci i18n (namespace paradise) untuk pesan ramah tiap kode galat. `null` berarti
 * jangan menampilkan apa pun (pembatalan oleh pengguna) atau pakai teks dari server
 * (kuota dan penolakan, yang membawa alasan spesifik dari API).
 */
export const getUploadErrorI18nKey = (code: TUploadErrorCode): string | null => {
  switch (code) {
    case "cancelled":
    case "quota":
    case "rejected":
      return null;
    case "network":
      return "unggah_ui.network";
    case "timeout":
      return "unggah_ui.timeout";
    case "server":
      return "unggah_ui.server";
    case "file_too_large":
      return "unggah_ui.file_too_large";
    case "empty_file":
      return "unggah_ui.empty_file";
    case "type_not_allowed":
      return "unggah_ui.type_not_allowed";
    case "expired":
      return "unggah_ui.expired";
    case "forbidden":
      return "unggah_ui.forbidden";
    default:
      return "unggah_ui.generic";
  }
};
