/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: old God Mode URLs and where they went
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * KEP-83 regrouped God Mode into eight menus. Every URL that ever existed keeps
 * working: routes.ts registers one redirect route per entry, so a bookmark never
 * falls into the 404. Keys have no trailing slash. This file is plain data
 * (no imports) because routes.ts reads it while the router is being built.
 */

export const ALAMAT_BARU: Record<string, string> = {
  // Before KEP-83 (current until 2.2.x)
  "/workspace": "/general/workspaces/",
  "/workspace/create": "/general/workspaces/create/",
  "/workspace/project-defaults": "/rules/projects/",
  "/email": "/notifications/",
  "/email/preview": "/notifications/preview/",
  "/authentication": "/access/",
  "/authentication/github": "/access/providers/github/",
  "/authentication/gitlab": "/access/providers/gitlab/",
  "/authentication/gitea": "/access/providers/gitea/",
  "/authentication/google": "/integrations/",
  "/api-keys": "/integrations/ai/",
  "/api-keys/image": "/integrations/image/",
  "/api-keys/google": "/integrations/",
  "/features": "/modules/",
  "/members": "/people/",
  "/members/organization": "/people/organization/",
  "/members/defaults": "/people/defaults/",
  // Older still (before the Logs and API keys menus)
  "/activity": "/logs/",
  "/activity/audit-log": "/logs/audit/",
  "/trash": "/logs/trash/",
  "/ai": "/integrations/ai/",
  "/image": "/integrations/image/",
};
