/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: which registry keys appear on which God Mode tab
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Only placement lives here (tab, section, order, unit, conditional rows).
 * Defaults, ranges and choices come from the server registry. A key the server
 * does not know is skipped, so a row can never show a setting nothing reads.
 */

import type { TParadiseModule } from "@plane/types";
import type { TGodmodeStrings } from "@/app/i18n/godmode";

type TSettingStrings = TGodmodeStrings["settings"];

export type TSettingRow = {
  key: string;
  /** Key of `settings.units`. */
  unit?: string;
  /** Show the row only while this returns true; receives the current draft value of any key. */
  showWhen?: (valueOf: (key: string) => string) => boolean;
};

export type TSettingSection = {
  id: keyof TSettingStrings["sections"];
  rows: TSettingRow[];
};

/** Tabs whose body is a plain list of registry rows (some add custom blocks around it). */
export type TSettingsTabId =
  | "general_company"
  | "access_sessions"
  | "rules_approvals"
  | "rules_dates"
  | "rules_permissions"
  | "rules_archiving"
  | "notifications_sending"
  | "notifications_schedule"
  | "modules_visibility"
  | "modules_chat"
  | "modules_dashboards"
  | "modules_files"
  | "integrations_google"
  | "logs_retention";

const moduleRows = (modules: TParadiseModule[]): TSettingRow[] =>
  modules.map((m) => ({ key: `ENABLE_${m.toUpperCase()}` }));

export const SETTINGS_LAYOUT: Record<TSettingsTabId, TSettingSection[]> = {
  general_company: [{ id: "company", rows: [{ key: "OFFICE_TIMEZONE" }] }],

  access_sessions: [
    { id: "sessions", rows: [{ key: "SESSION_DAYS", unit: "days" }] },
    { id: "invites", rows: [{ key: "INVITE_EXPIRY_DAYS", unit: "days" }] },
  ],

  rules_approvals: [
    {
      id: "approvals",
      rows: [
        { key: "APPROVAL_REQUIRED_BELOW_LEVEL" },
        { key: "APPROVAL_REJECT_REASON_REQUIRED" },
        // KEP-84: kapan tugas yang disetujui dihitung selesai, dan apakah yang menunggu terlambat.
        { key: "APPROVAL_FINISH_TIME" },
        { key: "APPROVAL_PENDING_NOT_LATE" },
      ],
    },
    { id: "ownership", rows: [{ key: "TASK_DELETE_RULE" }, { key: "DUE_DATE_CHANGE_RULE" }] },
    { id: "hierarchy", rows: [{ key: "ASSIGN_DOWN_ONLY" }, { key: "HIERARKI_GERBANG_TUGAS" }] },
  ],

  rules_dates: [
    {
      id: "dates_fill",
      rows: [{ key: "AUTO_START_DATE_ON_START" }, { key: "AUTO_DUE_DATE_ON_DONE" }, { key: "DUE_DATE_ON_EARLY_DONE" }],
    },
    { id: "dates_overdue", rows: [{ key: "OVERDUE_GRACE_DAYS", unit: "days" }] },
  ],

  // KEP-85: who else may change, archive or delete things besides work items.
  // One section per resource so the tab reads as a matrix.
  rules_permissions: [
    {
      id: "perm_modules",
      rows: [{ key: "PERM_MODULE_EDIT" }, { key: "PERM_MODULE_ARCHIVE" }, { key: "PERM_MODULE_DELETE" }],
    },
    { id: "perm_pages", rows: [{ key: "PERM_PAGE_EDIT" }, { key: "PERM_PAGE_ARCHIVE" }, { key: "PERM_PAGE_DELETE" }] },
    { id: "perm_views", rows: [{ key: "PERM_VIEW_EDIT" }, { key: "PERM_VIEW_DELETE" }] },
    { id: "perm_comments", rows: [{ key: "PERM_COMMENT_EDIT" }, { key: "PERM_COMMENT_DELETE" }] },
    { id: "perm_wiki", rows: [{ key: "PERM_WIKI_EDIT" }, { key: "PERM_WIKI_DELETE" }] },
    {
      id: "perm_projects",
      rows: [
        { key: "PERM_PROJECT_EDIT" },
        { key: "PERM_PROJECT_WORKFLOW" },
        { key: "PERM_PROJECT_ARCHIVE" },
        { key: "PERM_PROJECT_DELETE" },
      ],
    },
    { id: "perm_trash", rows: [{ key: "PERM_TRASH_RESTORE" }, { key: "PERM_TRASH_PURGE" }] },
  ],

  rules_archiving: [{ id: "archive_instance", rows: [{ key: "AUTO_ARCHIVE_DONE_DAYS" }] }],

  notifications_sending: [
    { id: "sending_reminders", rows: [{ key: "ENABLE_DEADLINE_REMINDER" }] },
    {
      id: "sending_chat",
      rows: [
        { key: "ENABLE_CHAT_EMAIL" },
        { key: "CHAT_EMAIL_QUIET_MINUTES", unit: "minutes" },
        { key: "CHAT_EMAIL_INTERVAL_MINUTES", unit: "minutes" },
      ],
    },
    {
      id: "sending_work",
      rows: [
        { key: "ENABLE_EMAIL_BATCH" },
        { key: "EMAIL_BATCH_DELAY_MINUTES", unit: "minutes", showWhen: (v) => v("ENABLE_EMAIL_BATCH") === "1" },
        { key: "ENABLE_EMAIL_THREADING" },
        { key: "ENABLE_EMAIL_ACTIVE_ONLY" },
        { key: "EMAIL_ACTIVE_DAYS", unit: "days", showWhen: (v) => v("ENABLE_EMAIL_ACTIVE_ONLY") === "1" },
      ],
    },
    { id: "sending_assign", rows: [{ key: "ENABLE_TUGAS_KE_DM" }] },
    // Emails only Super Admins receive (logs and the like). One row per kind.
    {
      id: "sending_admin",
      rows: [
        { key: "ENABLE_ADMIN_RETENTION_EMAIL" },
        {
          key: "ADMIN_RETENTION_EMAIL_INTERVAL_DAYS",
          unit: "days",
          showWhen: (v) => v("ENABLE_ADMIN_RETENTION_EMAIL") === "1",
        },
      ],
    },
  ],

  notifications_schedule: [
    {
      id: "schedule_reminders",
      rows: [
        { key: "DEADLINE_REMINDER_EMAIL_DAYS" },
        { key: "DEADLINE_REMINDER_INBOX_DAYS" },
        { key: "DEADLINE_REMINDER_TIME" },
      ],
    },
    {
      id: "schedule_summaries",
      rows: [
        { key: "DIGEST_MORNING_TIME" },
        { key: "DIGEST_EVENING_TIME" },
        { key: "DIRECTOR_DIGEST_TIME" },
        { key: "DIGEST_WEEKDAYS" },
      ],
    },
    {
      id: "schedule_content",
      rows: [
        { key: "DIGEST_LOOKAHEAD_DAYS", unit: "days" },
        { key: "STUCK_AFTER_DAYS", unit: "days" },
      ],
    },
  ],

  modules_visibility: [
    { id: "modules_sidebar", rows: moduleRows(["inbox", "your_work", "stickies", "drafts", "quick_links"]) },
    {
      id: "modules_workspace",
      rows: moduleRows(["dashboards", "initiatives", "views", "analytics", "chat", "wiki", "archives"]),
    },
    { id: "modules_project", rows: moduleRows(["work_items", "modules", "pages", "intake", "approvals"]) },
    { id: "modules_work_item", rows: moduleRows(["time_tracking", "estimates"]) },
  ],

  modules_chat: [
    {
      id: "chat_limits",
      rows: [
        { key: "CHAT_DELETE_WINDOW_HOURS", unit: "hours" },
        { key: "CHAT_EDIT_WINDOW_HOURS", unit: "hours" },
        { key: "CHAT_MESSAGE_MAX_LENGTH", unit: "chars" },
        { key: "CHAT_ATTACHMENTS_MAX", unit: "files" },
      ],
    },
  ],

  modules_dashboards: [
    {
      id: "dashboards_status",
      rows: [
        { key: "DASHBOARD_PERHATIAN_PERSEN", unit: "percent" },
        { key: "DASHBOARD_KRITIS_PERSEN", unit: "percent" },
        { key: "DASHBOARD_ON_TIME_WINDOW_DAYS", unit: "days" },
      ],
    },
    {
      id: "dashboards_attention",
      rows: [
        { key: "ATTENTION_REJECTED_DAYS", unit: "days" },
        { key: "ATTENTION_MENTION_DAYS", unit: "days" },
      ],
    },
  ],

  modules_files: [{ id: "files", rows: [{ key: "UPLOAD_MAX_MB", unit: "mb" }] }],

  integrations_google: [{ id: "google_calendar", rows: [{ key: "ENABLE_GOOGLE_CALENDAR_SYNC" }] }],

  logs_retention: [
    {
      id: "retention",
      rows: [
        { key: "TRASH_RETENTION_DAYS", unit: "days" },
        { key: "LOGIN_HISTORY_RETENTION_DAYS", unit: "days" },
      ],
    },
  ],
};
