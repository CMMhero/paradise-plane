/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: cermin web aturan area C (bawaan tampilan)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Cermin aturan `web=True` di apps/api/plane/utils/aturan/area_tampilan.py.
 * Aturan bawaan per akun (`member_default`) tidak ada di sini: web membaca nilai
 * milik akunnya sendiri (profil, ProjectUserProperty, preferensi Home).
 */

import { angkaWeb, daftarWeb, pilihanWeb } from "./jenis";

export const ACTIVITY_DEFAULT_FILTERS_CHOICES = ["ACTIVITY", "COMMENT", "STATE", "ASSIGNEE"] as const;
export const COMMENT_BOX_POSITION_CHOICES = ["follow", "top", "bottom"] as const;
export const COMMENT_REPLY_ORDER_CHOICES = ["oldest", "timeline"] as const;
export const PEEK_MODE_DEFAULT_CHOICES = ["side-peek", "modal", "full-screen"] as const;
export const KPI_DEFAULT_PERIOD_CHOICES = ["this_week", "this_month", "30d", "this_quarter"] as const;
export const DIVISION_DASHBOARD_DEFAULT_MODE_CHOICES = ["ringkas", "rinci", "laporan"] as const;
export const DIVISION_REPORT_DEFAULT_PERIOD_CHOICES = ["7d", "30d", "this_month", "last_month"] as const;

export const ATURAN_WEB_TAMPILAN = {
  ACTIVITY_DEFAULT_FILTERS: daftarWeb(ACTIVITY_DEFAULT_FILTERS_CHOICES, ["ACTIVITY", "COMMENT", "STATE", "ASSIGNEE"]),
  COMMENT_BOX_POSITION: pilihanWeb(COMMENT_BOX_POSITION_CHOICES, "follow"),
  COMMENT_REPLY_ORDER: pilihanWeb(COMMENT_REPLY_ORDER_CHOICES, "oldest"),
  PEEK_MODE_DEFAULT: pilihanWeb(PEEK_MODE_DEFAULT_CHOICES, "side-peek"),
  ATTENTION_DISMISS_DAYS: angkaWeb(30),
  CHANGELOG_RELEASES_SHOWN: angkaWeb(1),
  KPI_DEFAULT_PERIOD: pilihanWeb(KPI_DEFAULT_PERIOD_CHOICES, "this_month"),
  DIVISION_DASHBOARD_DEFAULT_MODE: pilihanWeb(DIVISION_DASHBOARD_DEFAULT_MODE_CHOICES, "ringkas"),
  DIVISION_REPORT_DEFAULT_PERIOD: pilihanWeb(DIVISION_REPORT_DEFAULT_PERIOD_CHOICES, "7d"),
};
