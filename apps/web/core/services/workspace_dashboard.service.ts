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
  totals: TDashboardFigures & {
    projects: number;
    /** Persen tugas bertenggat yang selesai tepat waktu, 30 hari terakhir. */
    on_time_rate: number | null;
  };
  divisions: TDivisionGroup[];
  /** Urut dari yang paling bermasalah. */
  projects: TDivisionStats[];
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

  worklogExportUrl(workspaceSlug: string): string {
    return `${API_BASE_URL}/api/workspaces/${workspaceSlug}/worklogs/export/`;
  }
}
