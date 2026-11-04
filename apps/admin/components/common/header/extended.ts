/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Paradise pages. Without an entry the breadcrumb falls back to the URL segment
// in sentence case ("project-defaults" -> "Project defaults"), never caps.
// The breadcrumb stops at the parent: the last segment is the tab shown below.
export const EXTENDED_HEADER_SEGMENT_LABELS: Record<string, string> = {
  company: "Company",
  workspaces: "Workspaces",
  providers: "Providers",
  people: "People",
  organization: "Organization",
  rules: "Work rules",
  notifications: "Notifications",
  modules: "Modules",
  logs: "Data & logs",
  audit: "Audit log",
  trash: "Trash",
};
