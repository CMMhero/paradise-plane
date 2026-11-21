/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Bell, Cog, LayoutGrid, ListChecks, LockKeyhole, Plug, ScrollText, Users } from "lucide-react";
import { settingsStrings } from "@/app/i18n/godmode-settings";
import { MENU_TABS } from "@/components/common/menu-tree";
import type { TMenuId } from "@/components/common/menu-tree";
// types
import type { TSidebarMenuItem } from "./types";

export type TCoreSidebarMenuKey = TMenuId;

// Paradise (KEP-83): eight menus, each with tabs. Name and target come from the
// menu tree and its strings, so the sidebar, tabs and command palette agree.
// Only the icon and the one-line sidebar summary live here.
export const coreSidebarMenuLinks: Record<TCoreSidebarMenuKey, TSidebarMenuItem> = {
  general: {
    Icon: Cog,
    name: settingsStrings.menus.general.title,
    description: "Instance, company, and workspaces.",
    href: MENU_TABS.general[0].href,
  },
  access: {
    Icon: LockKeyhole,
    name: settingsStrings.menus.access.title,
    description: "Methods, providers, sessions, and invites.",
    href: MENU_TABS.access[0].href,
  },
  people: {
    Icon: Users,
    name: settingsStrings.menus.people.title,
    description: "Accounts, organization, and defaults.",
    href: MENU_TABS.people[0].href,
  },
  rules: {
    Icon: ListChecks,
    name: settingsStrings.menus.rules.title,
    description: "Approvals, dates, and archiving.",
    href: MENU_TABS.rules[0].href,
  },
  notifications: {
    Icon: Bell,
    name: settingsStrings.menus.notifications.title,
    description: "Email, schedule, and defaults by role.",
    href: MENU_TABS.notifications[0].href,
  },
  modules: {
    Icon: LayoutGrid,
    name: settingsStrings.menus.modules.title,
    description: "Visibility, chat, dashboards, and files.",
    href: MENU_TABS.modules[0].href,
  },
  integrations: {
    Icon: Plug,
    name: settingsStrings.menus.integrations.title,
    description: "Google, AI, and the image library.",
    href: MENU_TABS.integrations[0].href,
  },
  logs: {
    Icon: ScrollText,
    name: settingsStrings.menus.logs.title,
    description: "Activity, audit log, trash, and retention.",
    href: MENU_TABS.logs[0].href,
  },
};
