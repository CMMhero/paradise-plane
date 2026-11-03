/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: saklar fitur di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** Saklar "0"/"1" milik Paradise. Cermin `SAKLAR_BAWAAN` di apps/api/plane/utils/saklar_instance.py. */
export type TInstanceParadiseToggleKeys =
  | "ENABLE_DEADLINE_REMINDER"
  | "ENABLE_CHAT_EMAIL"
  | "ENABLE_GOOGLE_CALENDAR_SYNC"
  | "ENABLE_TUGAS_KE_DM"
  | "HIERARKI_GERBANG_TUGAS"
  | "AUTO_START_DATE_ON_START"
  | "AUTO_DUE_DATE_ON_DONE"
  | TInstanceParadiseModuleKeys;

/** Saklar modul selalu `ENABLE_<NAMA MODUL>`, sama seperti `MODUL_APLIKASI` di server. */
export type TInstanceParadiseModuleKeys = `ENABLE_${Uppercase<TParadiseModule>}`;

/** Setelan angka milik Paradise. Cermin `SETELAN_ANGKA` di saklar_instance.py. */
export type TInstanceParadiseNumberKeys =
  | "CHAT_EMAIL_QUIET_MINUTES"
  | "CHAT_EMAIL_INTERVAL_MINUTES"
  | "LOGIN_HISTORY_RETENTION_DAYS"
  | "TRASH_RETENTION_DAYS"
  | "DASHBOARD_PERHATIAN_PERSEN"
  | "DASHBOARD_KRITIS_PERSEN"
  | "AUTO_ARCHIVE_DONE_DAYS"
  | "DUE_DATE_ON_EARLY_DONE"
  | "OVERDUE_GRACE_DAYS"
  | "DASHBOARD_ON_TIME_WINDOW_DAYS"
  | "CHAT_DELETE_WINDOW_HOURS";

export type TInstanceGoogleCalendarConfigurationKeys = "GOOGLE_CALENDAR_CLIENT_ID" | "GOOGLE_CALENDAR_CLIENT_SECRET";

export type TInstanceParadiseConfigurationKeys =
  | TInstanceParadiseToggleKeys
  | TInstanceParadiseNumberKeys
  | TInstanceGoogleCalendarConfigurationKeys;

/** Modul aplikasi yang bisa dimatikan. Cermin `MODUL_APLIKASI` di saklar_instance.py. */
export type TParadiseModule =
  // Sidebar utama
  | "inbox"
  | "your_work"
  | "stickies"
  | "drafts"
  | "quick_links"
  // Menu workspace
  | "dashboards"
  | "initiatives"
  | "views"
  | "analytics"
  | "chat"
  | "wiki"
  | "archives"
  // Tab project
  | "work_items"
  | "modules"
  | "pages"
  | "intake"
  | "approvals"
  // Fitur di dalam work item & setelan project
  | "time_tracking"
  | "estimates";
