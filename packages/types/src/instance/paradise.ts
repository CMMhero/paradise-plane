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
  | "ENABLE_EMAIL_BATCH"
  | "ENABLE_EMAIL_THREADING"
  | "ENABLE_EMAIL_ACTIVE_ONLY"
  | "ENABLE_ADMIN_RETENTION_EMAIL"
  | TInstanceParadiseModuleKeys;

/** Saklar modul selalu `ENABLE_<NAMA MODUL>`, sama seperti `MODUL_APLIKASI` di server. */
export type TInstanceParadiseModuleKeys = `ENABLE_${Uppercase<TParadiseModule>}`;

/** Setelan angka milik Paradise. Cermin `SETELAN_ANGKA` di saklar_instance.py. */
export type TInstanceParadiseNumberKeys =
  | "CHAT_EMAIL_QUIET_MINUTES"
  | "CHAT_EMAIL_INTERVAL_MINUTES"
  | "LOGIN_HISTORY_RETENTION_DAYS"
  | "ADMIN_RETENTION_EMAIL_INTERVAL_DAYS"
  | "TRASH_RETENTION_DAYS"
  | "DASHBOARD_PERHATIAN_PERSEN"
  | "DASHBOARD_KRITIS_PERSEN"
  | "AUTO_ARCHIVE_DONE_DAYS"
  | "DUE_DATE_ON_EARLY_DONE"
  | "OVERDUE_GRACE_DAYS"
  | "DASHBOARD_ON_TIME_WINDOW_DAYS"
  | "CHAT_DELETE_WINDOW_HOURS"
  | "EMAIL_BATCH_DELAY_MINUTES"
  | "EMAIL_ACTIVE_DAYS";

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

/**
 * Settings registry served by `GET /api/instances/settings/`. The server is the
 * only place that knows defaults, ranges, choices and which rules are sensitive;
 * God Mode renders whatever the registry says and never mirrors it.
 */
export type TInstanceSettingKind = "toggle" | "number" | "choice" | "time" | "day_list" | "weekday_set" | "timezone";

export type TInstanceSetting = {
  key: string;
  kind: TInstanceSettingKind;
  /** Always a string: "0"/"1", "30", "08:30", "-3,0,3", "1,2,3,4,5", "Asia/Jakarta". */
  default: string;
  value: string;
  /** Number kind only. */
  min: number | null;
  max: number | null;
  /** Choice kind only: the allowed integer values. */
  choices: number[] | null;
  /** Changing it needs the typed confirmation phrase and is written to the audit log. */
  sensitive: boolean;
};

export type TInstanceSettingsResponse = { settings: TInstanceSetting[] };

export type TInstanceSettingsUpdate = {
  values: Record<string, string>;
  /** Required by the server when a sensitive key changes. */
  confirm?: string;
};

/** Error body of `PATCH /api/instances/settings/`: per-key messages, or `confirm_required`. */
export type TInstanceSettingsError = {
  errors?: Record<string, string>;
  error?: string;
};
