/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Dashboard Divisi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

/** Status kesehatan dari porsi tugas aktif yang lewat tenggat (KEP-60). */
export type TDashboardHealth = "lancar" | "perhatian" | "kritis";

/** Angka yang sama di tingkat project, divisi, dan total. Cermin `_rangkum` di server. */
type TDashboardFigures = {
  issues_total: number;
  issues_completed: number;
  /** Total dikurangi selesai (termasuk yang dibatalkan). Perilaku lama, dipertahankan. */
  issues_open: number;
  /** Belum selesai dan belum dibatalkan. Penyebut status kesehatan. */
  issues_active: number;
  issues_overdue: number;
  completed_7d: number;
  completed_prev_7d: number;
  overdue_prev_7d: number;
  pending_approvals: number;
  worklog_minutes_total: number;
  worklog_minutes_month: number;
  /** Persen selesai dari tugas yang tidak dibatalkan; null kalau belum ada tugas. */
  completion_rate: number | null;
  health: TDashboardHealth;
};

export type TDivisionStats = Omit<TDashboardFigures, "health"> & {
  id: string;
  identifier: string;
  name: string;
  members: number;
  health: TDashboardHealth;
  overdue_oldest_days: number | null;
  department: { id: string; code: string; name: string } | null;
  division_id: string | null;
};

export type TDivisionGroup = TDashboardFigures & {
  /** null = project yang belum dipetakan ke departemen mana pun. */
  id: string | null;
  code: string;
  name: string;
  on_time_rate: number | null;
  /** Urut dari yang paling bermasalah. */
  project_ids: string[];
};

export type TDivisionDashboard = {
  generated_at: string;
  thresholds: { attention: number; critical: number };
  /** Jendela `on_time_rate` dalam hari (God Mode DASHBOARD_ON_TIME_WINDOW_DAYS). Tidak ada = server lama, 30. */
  on_time_window_days?: number;
  totals: TDashboardFigures & {
    projects: number;
    /** Persen tugas bertenggat yang selesai tepat waktu, `on_time_window_days` hari terakhir. */
    on_time_rate: number | null;
  };
  divisions: TDivisionGroup[];
  /** Urut dari yang paling bermasalah. */
  projects: TDivisionStats[];
};

/** Periode laporan tugas selesai (KEP-62). Cermin `PERIODE_SAH` di server. */
export const REPORT_PERIODS = ["7d", "30d", "this_month", "last_month"] as const;
export type TReportPeriod = (typeof REPORT_PERIODS)[number];

export type TReportTiming = "on_time" | "late" | "no_due_date";

/** Angka selesai untuk satu tingkat (total, pembanding, divisi, project). */
export type TCompletedFigures = {
  completed: number;
  on_time: number;
  late: number;
  no_due_date: number;
  /** Tepat waktu / (tepat waktu + terlambat); null kalau belum ada yang bertenggat. */
  on_time_rate: number | null;
};

export type TReportProject = TCompletedFigures & {
  id: string;
  identifier: string;
  name: string;
  department: { id: string; code: string; name: string } | null;
};

export type TReportDivision = TCompletedFigures & {
  /** null = project yang belum dipetakan ke departemen. */
  id: string | null;
  code: string;
  name: string;
  /** Terbanyak selesai dulu. */
  projects: TReportProject[];
};

export type TCompletedItem = {
  id: string;
  project_id: string;
  project_identifier: string;
  project_name: string;
  sequence_id: number;
  name: string;
  priority: string | null;
  completed_at: string;
  /** Tanggal selesai dalam hari kantor (WIB), YYYY-MM-DD. */
  completed_date: string;
  target_date: string | null;
  timing: TReportTiming;
  assignees: string[];
};

export type TCompletedReport = {
  generated_at: string;
  /** Tanggal inklusif, YYYY-MM-DD. */
  period: { key: TReportPeriod; start: string; end: string };
  totals: TCompletedFigures & { created: number };
  previous: TCompletedFigures;
  divisions: TReportDivision[];
  /** Terbaru dulu, dibatasi server; `items_truncated` = ada yang tidak dikirim. */
  items: TCompletedItem[];
  items_truncated: boolean;
};

export class WorkspaceDashboardService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getDashboard(workspaceSlug: string): Promise<TDivisionDashboard> {
    return this.get(`/api/workspaces/${workspaceSlug}/divisi-dashboard/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async getCompletedReport(workspaceSlug: string, period: TReportPeriod): Promise<TCompletedReport> {
    return this.get(`/api/workspaces/${workspaceSlug}/divisi-dashboard/laporan/`, { params: { periode: period } })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  completedReportCsvUrl(workspaceSlug: string, period: TReportPeriod): string {
    return `${API_BASE_URL}/api/workspaces/${workspaceSlug}/divisi-dashboard/laporan/?periode=${period}&unduh=csv`;
  }

  worklogExportUrl(workspaceSlug: string): string {
    return `${API_BASE_URL}/api/workspaces/${workspaceSlug}/worklogs/export/`;
  }
}
