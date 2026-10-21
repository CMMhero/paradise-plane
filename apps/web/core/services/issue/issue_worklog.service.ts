/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Time Tracking
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

export type TIssueWorkLog = {
  id: string;
  duration: number; // menit
  description: string;
  logged_at: string;
  logged_by: string;
  logged_by_detail?: {
    id: string;
    display_name?: string;
    first_name?: string;
    last_name?: string;
    avatar_url?: string;
  };
};

export type TWorkLogList = {
  total_duration: number;
  work_logs: TIssueWorkLog[];
};

export class IssueWorkLogService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private base(workspaceSlug: string, projectId: string, issueId: string): string {
    return `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/work-logs/`;
  }

  async list(workspaceSlug: string, projectId: string, issueId: string): Promise<TWorkLogList> {
    return this.get(this.base(workspaceSlug, projectId, issueId))
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async create(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    data: { duration: number; description?: string }
  ): Promise<TIssueWorkLog> {
    return this.post(this.base(workspaceSlug, projectId, issueId), data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async remove(workspaceSlug: string, projectId: string, issueId: string, workLogId: string): Promise<void> {
    return this.delete(`${this.base(workspaceSlug, projectId, issueId)}${workLogId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
