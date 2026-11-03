/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Paradise pages. Without an entry the breadcrumb falls back to the URL segment
// in sentence case ("project-defaults" -> "Project defaults"), never caps.
export const EXTENDED_HEADER_SEGMENT_LABELS: Record<string, string> = {
  workspace: "Workspaces",
  "project-defaults": "New project defaults",
  preview: "Preview",
  members: "Members",
  organization: "Organization",
  defaults: "New member defaults",
  logs: "Logs",
  audit: "Audit log",
  trash: "Trash",
  features: "Features",
  "api-keys": "API keys",
  image: "Image library",
  google: "Google",
};
