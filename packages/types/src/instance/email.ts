/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TInstanceEmailConfigurationKeys =
  | "EMAIL_HOST"
  | "EMAIL_PORT"
  | "EMAIL_HOST_USER"
  | "EMAIL_HOST_PASSWORD"
  | "EMAIL_USE_TLS"
  | "EMAIL_USE_SSL"
  | "EMAIL_FROM"
  | "ENABLE_SMTP";

/**
 * Email MASUK. Tersimpan tapi BELUM DIBACA apa pun, Plane CE tidak punya
 * pemroses inbound. Dipisah dari tipe SMTP supaya tidak ada kode yang
 * mengiranya bagian dari alur kirim yang sudah jalan.
 */
export type TInstanceImapConfigurationKeys =
  | "IMAP_HOST"
  | "IMAP_PORT"
  | "IMAP_HOST_USER"
  | "IMAP_HOST_PASSWORD"
  | "IMAP_USE_SSL";
