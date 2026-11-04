/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { index, layout, route } from "@react-router/dev/routes";
import type { RouteConfig } from "@react-router/dev/routes";
import { ALAMAT_BARU } from "./alamat-lama-map";

const D = "./(all)/(dashboard)";

// Settings tabs that are only a list of registry rows share one page module;
// it picks its content from the URL (see settings-tab/page.tsx).
const registryTabs = [
  "general/company",
  "access/sessions",
  "rules",
  "rules/dates",
  "rules/permissions",
  "notifications/sending",
  "notifications/schedule",
  "modules",
  "modules/chat",
  "modules/dashboards",
  "modules/files",
  "logs/retention",
];

export default [
  layout("./(all)/(home)/layout.tsx", [index("./(all)/(home)/page.tsx")]),
  layout(`${D}/layout.tsx`, [
    // General
    route("general", `${D}/general/page.tsx`),
    route("general/workspaces", `${D}/workspace/page.tsx`),
    route("general/workspaces/create", `${D}/workspace/create/page.tsx`),
    // Sign-in & access
    route("access", `${D}/authentication/page.tsx`),
    route("access/providers", `${D}/authentication/providers.tsx`),
    route("access/providers/github", `${D}/authentication/github/page.tsx`),
    route("access/providers/gitlab", `${D}/authentication/gitlab/page.tsx`),
    route("access/providers/gitea", `${D}/authentication/gitea/page.tsx`),
    // People: Accounts + Organization + New member defaults.
    route("people", `${D}/members/page.tsx`),
    route("people/organization", `${D}/organisasi/page.tsx`),
    route("people/defaults", `${D}/bawaan-member/page.tsx`),
    // Work rules
    route("rules/archiving", `${D}/rules/archiving.tsx`),
    route("rules/projects", `${D}/bawaan-project/page.tsx`),
    // Notifications
    route("notifications", `${D}/email/page.tsx`),
    route("notifications/roles", `${D}/bawaan-member/roles.tsx`),
    route("notifications/preview", `${D}/email/preview/page.tsx`),
    // Integrations
    route("integrations", `${D}/kredensial-google/page.tsx`),
    route("integrations/ai", `${D}/ai/page.tsx`),
    route("integrations/image", `${D}/image/page.tsx`),
    // Data & logs. The audit log stays in God Mode only.
    route("logs", `${D}/activity/page.tsx`),
    route("logs/audit", `${D}/logs/page.tsx`),
    route("logs/trash", `${D}/trash/page.tsx`),
    // Plain registry tabs (one module, ids keep the routes apart).
    ...registryTabs.map((path) =>
      route(path, `${D}/settings-tab/page.tsx`, { id: `tab-${path.replaceAll("/", "-")}` })
    ),
    // Old addresses keep working (alamat-lama-map.ts).
    ...Object.keys(ALAMAT_BARU).map((path) =>
      route(path.slice(1), `${D}/alamat-lama.tsx`, { id: `lama-${path.slice(1).replaceAll("/", "-")}` })
    ),
  ]),
  // Catch-all route for 404 handling - must be last
  route("*", "./components/404.tsx"),
] satisfies RouteConfig;
