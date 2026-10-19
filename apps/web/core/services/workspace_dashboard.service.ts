/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Dashboard Divisi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

export type TDivisionStats = {
  id: string;
  identifier: string;
  name: string;
  members: number;
  issues_total: number;
  issues_completed: number;
  issues_open: number;
  issues_overdue: number;
  worklog_minutes_total: number;
  worklog_minutes_month: number;
};

export type TDivisionDashboard = {
  totals: {
    projects: number;
    issues_total: number;
    issues_open: number;
    issues_overdue: number;
    issues_completed: number;
    worklog_minutes_total: number;
    worklog_minutes_month: number;
  };
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
