/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Initiatives
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

export type TInitiativeStatus = "PLANNED" | "ACTIVE" | "ON_HOLD" | "COMPLETED";

export type TInitiative = {
  id: string;
  name: string;
  description_html: string;
  status: TInitiativeStatus;
  lead: string | null;
  start_date: string | null;
  end_date: string | null;
  project_ids: string[];
  issues_total: number;
  issues_completed: number;
};

export class InitiativeService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private root(workspaceSlug: string): string {
    return `/api/workspaces/${workspaceSlug}/initiatives/`;
  }

  async list(workspaceSlug: string): Promise<TInitiative[]> {
    return this.get(this.root(workspaceSlug))
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async create(workspaceSlug: string, data: Partial<TInitiative>): Promise<TInitiative> {
    return this.post(this.root(workspaceSlug), data)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async update(workspaceSlug: string, initiativeId: string, data: Partial<TInitiative>): Promise<TInitiative> {
    return this.patch(`${this.root(workspaceSlug)}${initiativeId}/`, data)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async remove(workspaceSlug: string, initiativeId: string): Promise<void> {
    return this.delete(`${this.root(workspaceSlug)}${initiativeId}/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async linkProject(workspaceSlug: string, initiativeId: string, projectId: string): Promise<TInitiative> {
    return this.post(`${this.root(workspaceSlug)}${initiativeId}/projects/`, { project: projectId })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async unlinkProject(workspaceSlug: string, initiativeId: string, projectId: string): Promise<TInitiative> {
    return this.delete(`${this.root(workspaceSlug)}${initiativeId}/projects/${projectId}/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }
}
