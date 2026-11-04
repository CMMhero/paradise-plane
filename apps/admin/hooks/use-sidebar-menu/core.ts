/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Bell, Cog, LayoutGrid, ListChecks, LockKeyhole, Plug, ScrollText, Users } from "lucide-react";
// types
import type { TSidebarMenuItem } from "./types";

export type TCoreSidebarMenuKey =
  | "general"
  | "access"
  | "people"
  | "rules"
  | "notifications"
  | "modules"
  | "integrations"
  | "logs";

// Paradise (KEP-83): eight menus, each with tabs (components/common/section-tabs.tsx).
export const coreSidebarMenuLinks: Record<TCoreSidebarMenuKey, TSidebarMenuItem> = {
  general: {
    Icon: Cog,
    name: "General",
    description: "Instance, company, and workspaces.",
    href: `/general/`,
  },
  access: {
    Icon: LockKeyhole,
    name: "Sign-in & access",
    description: "Methods, providers, sessions, and invites.",
    href: `/access/`,
  },
  people: {
    Icon: Users,
    name: "People",
    description: "Accounts, organization, and defaults.",
    href: `/people/`,
  },
  rules: {
    Icon: ListChecks,
    name: "Work rules",
    description: "Approvals, dates, and archiving.",
    href: `/rules/`,
  },
  notifications: {
    Icon: Bell,
    name: "Notifications",
    description: "Email, schedule, and defaults by role.",
    href: `/notifications/`,
  },
  modules: {
    Icon: LayoutGrid,
    name: "Modules",
    description: "Visibility, chat, dashboards, and files.",
    href: `/modules/`,
  },
  integrations: {
    Icon: Plug,
    name: "Integrations",
    description: "Google, AI, and the image library.",
    href: `/integrations/`,
  },
  logs: {
    Icon: ScrollText,
    name: "Data & logs",
    description: "Activity, audit log, trash, and retention.",
    href: `/logs/`,
  },
};
