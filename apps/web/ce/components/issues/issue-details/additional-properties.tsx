/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TWorkItemAdditionalSidebarProperties = {
  workItemId: string;
  workItemTypeId: string | null;
  projectId: string;
  workspaceSlug: string;
  isEditable: boolean;
  isPeekView?: boolean;
};

// Panel custom properties Paradise dicabut bersama Work Item Types (KEP-53).
// Kembali ke stub CE upstream: tak ada panel, tak ada request.
export function WorkItemAdditionalSidebarProperties(_props: TWorkItemAdditionalSidebarProperties) {
  return null;
}
