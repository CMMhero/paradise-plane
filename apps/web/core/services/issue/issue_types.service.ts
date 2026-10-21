/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Work Item Types & Custom Properties
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

export type TWorkItemType = {
  id: string;
  name: string;
  description: string;
  logo_props: Record<string, unknown>;
  is_default: boolean;
  is_active: boolean;
};

export type TPropertyType = "TEXT" | "DECIMAL" | "BOOLEAN" | "DATETIME" | "OPTION" | "MEMBER";

export type TWorkItemPropertyOption = {
  id: string;
  name: string;
  is_default: boolean;
  is_active: boolean;
};

export type TWorkItemProperty = {
  id: string;
  display_name: string;
  description: string;
  property_type: TPropertyType;
  is_required: boolean;
  is_active: boolean;
  is_multi: boolean;
  options: TWorkItemPropertyOption[];
};

export type TWorkItemPropertyValue = {
  id: string;
  property: string;
  value_text: string | null;
  value_boolean: boolean;
  value_number: number | null;
  value_datetime: string | null;
  value_uuid: string | null;
};

export class WorkItemTypesService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private root(workspaceSlug: string, projectId: string): string {
    return `/api/workspaces/${workspaceSlug}/projects/${projectId}`;
  }

  // ----- Types -----
  async listTypes(workspaceSlug: string, projectId: string): Promise<TWorkItemType[]> {
    return this.get(`${this.root(workspaceSlug, projectId)}/issue-types/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async createType(workspaceSlug: string, projectId: string, data: Partial<TWorkItemType>): Promise<TWorkItemType> {
    return this.post(`${this.root(workspaceSlug, projectId)}/issue-types/`, data)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async updateType(
    workspaceSlug: string,
    projectId: string,
    typeId: string,
    data: Partial<TWorkItemType>
  ): Promise<TWorkItemType> {
    return this.patch(`${this.root(workspaceSlug, projectId)}/issue-types/${typeId}/`, data)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async deleteType(workspaceSlug: string, projectId: string, typeId: string): Promise<void> {
    return this.delete(`${this.root(workspaceSlug, projectId)}/issue-types/${typeId}/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  // ----- Properties (field custom per tipe) -----
  async listProperties(workspaceSlug: string, projectId: string, typeId: string): Promise<TWorkItemProperty[]> {
    return this.get(`${this.root(workspaceSlug, projectId)}/issue-types/${typeId}/properties/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async createProperty(
    workspaceSlug: string,
    projectId: string,
    typeId: string,
    data: Partial<TWorkItemProperty>
  ): Promise<TWorkItemProperty> {
    return this.post(`${this.root(workspaceSlug, projectId)}/issue-types/${typeId}/properties/`, data)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async deleteProperty(workspaceSlug: string, projectId: string, typeId: string, propertyId: string): Promise<void> {
    return this.delete(`${this.root(workspaceSlug, projectId)}/issue-types/${typeId}/properties/${propertyId}/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  // ----- Options (untuk field OPTION) -----
  async createOption(
    workspaceSlug: string,
    projectId: string,
    propertyId: string,
    data: { name: string; is_default?: boolean }
  ): Promise<TWorkItemPropertyOption> {
    return this.post(`${this.root(workspaceSlug, projectId)}/properties/${propertyId}/options/`, data)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async deleteOption(workspaceSlug: string, projectId: string, propertyId: string, optionId: string): Promise<void> {
    return this.delete(`${this.root(workspaceSlug, projectId)}/properties/${propertyId}/options/${optionId}/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  // ----- Values (nilai field pada satu work item) -----
  async listValues(workspaceSlug: string, projectId: string, issueId: string): Promise<TWorkItemPropertyValue[]> {
    return this.get(`${this.root(workspaceSlug, projectId)}/issues/${issueId}/property-values/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async setValue(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    data: Partial<TWorkItemPropertyValue> & { property: string }
  ): Promise<TWorkItemPropertyValue> {
    return this.post(`${this.root(workspaceSlug, projectId)}/issues/${issueId}/property-values/`, data)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }
}
