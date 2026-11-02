/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: katalog saklar notifikasi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type {
  TNotificationDigestKey,
  TNotificationEmailKey,
  TNotificationInboxKey,
  TNotificationPreferenceKey,
} from "@plane/types";

/**
 * Satu jenis kabar = satu baris matriks: saklar inbox di aplikasi dan saklar email.
 * Profil > Notifikasi, God Mode (preferensi per member) dan God Mode (bawaan jabatan)
 * menggambar dari daftar yang sama, jadi ketiganya tidak bisa tidak sinkron.
 * Cermin `SAKLAR_EMAIL` + `SAKLAR_INBOX` di apps/api/plane/utils/preferensi_email.py.
 *
 * `key` = nama jenis kabar, dipakai sebagai kunci label i18n.
 */
export type TNotificationEvent = {
  key: string;
  inbox: TNotificationInboxKey;
  email: TNotificationEmailKey;
};

export const NOTIFICATION_EVENTS: readonly TNotificationEvent[] = [
  { key: "assigned", inbox: "inbox_assigned", email: "assigned" },
  { key: "mention", inbox: "inbox_mention", email: "mention" },
  { key: "comment", inbox: "inbox_comment", email: "comment" },
  { key: "approval", inbox: "inbox_approval", email: "approval" },
  { key: "deadline", inbox: "inbox_deadline", email: "deadline_reminder" },
  { key: "issue_completed", inbox: "inbox_issue_completed", email: "issue_completed" },
  { key: "state_change", inbox: "inbox_state_change", email: "state_change" },
  { key: "property_change", inbox: "inbox_property_change", email: "property_change" },
  { key: "chat", inbox: "inbox_chat", email: "chat" },
];

/** Bagian isi ringkasan harian, urut tampil. Berlaku untuk edisi pagi (`daily_digest`)
 * dan sore (`daily_digest_sore`); hanya berarti selama salah satunya hidup. */
export const NOTIFICATION_DIGEST_SECTIONS: readonly TNotificationDigestKey[] = [
  "digest_terlambat",
  "digest_hari_ini",
  "digest_depan",
  "digest_diberikan",
  "digest_tim",
];

/** Semua kunci satu baris preferensi. Cermin `SAKLAR_NOTIFIKASI`. */
export const NOTIFICATION_PREFERENCE_KEYS: readonly TNotificationPreferenceKey[] = [
  ...NOTIFICATION_EVENTS.flatMap((e) => [e.inbox, e.email]),
  "daily_digest",
  "daily_digest_sore",
  ...NOTIFICATION_DIGEST_SECTIONS,
];
