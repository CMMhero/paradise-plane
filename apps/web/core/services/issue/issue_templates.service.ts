/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Templates & Recurring
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

export type TIssueTemplate = {
  id: string;
  name: string;
  title: string;
  description_html: string;
  priority: string;
  default_assignee: string | null;
};

export type TRecurringInterval = "DAILY" | "WEEKLY" | "MONTHLY";

export type TRecurringIssue = {
  id: string;
  template: string;
  template_detail?: TIssueTemplate;
  interval: TRecurringInterval;
  next_run_at: string;
  last_run_at: string | null;
  is_active: boolean;
};

export class IssueTemplatesService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private root(workspaceSlug: string, projectId: string): string {
    return `/api/workspaces/${workspaceSlug}/projects/${projectId}`;
  }

  async listTemplates(workspaceSlug: string, projectId: string): Promise<TIssueTemplate[]> {
    return this.get(`${this.root(workspaceSlug, projectId)}/issue-templates/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async createTemplate(
    workspaceSlug: string,
    projectId: string,
    data: Partial<TIssueTemplate>
  ): Promise<TIssueTemplate> {
    return this.post(`${this.root(workspaceSlug, projectId)}/issue-templates/`, data)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async deleteTemplate(workspaceSlug: string, projectId: string, templateId: string): Promise<void> {
    return this.delete(`${this.root(workspaceSlug, projectId)}/issue-templates/${templateId}/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async applyTemplate(workspaceSlug: string, projectId: string, templateId: string): Promise<{ id: string }> {
    return this.post(`${this.root(workspaceSlug, projectId)}/issue-templates/${templateId}/apply/`, {})
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async listRecurring(workspaceSlug: string, projectId: string): Promise<TRecurringIssue[]> {
    return this.get(`${this.root(workspaceSlug, projectId)}/recurring-issues/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async createRecurring(
    workspaceSlug: string,
    projectId: string,
    data: { template: string; interval: TRecurringInterval; next_run_at: string }
  ): Promise<TRecurringIssue> {
    return this.post(`${this.root(workspaceSlug, projectId)}/recurring-issues/`, data)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async updateRecurring(
    workspaceSlug: string,
    projectId: string,
    recurringId: string,
    data: Partial<TRecurringIssue>
  ): Promise<TRecurringIssue> {
    return this.patch(`${this.root(workspaceSlug, projectId)}/recurring-issues/${recurringId}/`, data)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async deleteRecurring(workspaceSlug: string, projectId: string, recurringId: string): Promise<void> {
    return this.delete(`${this.root(workspaceSlug, projectId)}/recurring-issues/${recurringId}/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }
}
