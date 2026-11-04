/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: the God Mode menu tree
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Plain data, no React: the tabs, the sidebar, the old-URL redirects and the
 * command palette index (components/command-palette) all read it.
 */

import type { TGodmodeStrings } from "@/app/i18n/godmode";

export type TMenuId = "general" | "access" | "people" | "rules" | "notifications" | "modules" | "integrations" | "logs";

export type TTabId = keyof TGodmodeStrings["settings"]["tabs"];

/** Tabs per menu, in display order. The first tab is the menu's own route. */
export const MENU_TABS: Record<TMenuId, { id: TTabId; href: string }[]> = {
  general: [
    { id: "general_instance", href: "/general/" },
    { id: "general_company", href: "/general/company/" },
    { id: "general_workspaces", href: "/general/workspaces/" },
  ],
  access: [
    { id: "access_methods", href: "/access/" },
    { id: "access_providers", href: "/access/providers/" },
    { id: "access_sessions", href: "/access/sessions/" },
  ],
  people: [
    { id: "people_accounts", href: "/people/" },
    { id: "people_organization", href: "/people/organization/" },
    { id: "people_defaults", href: "/people/defaults/" },
  ],
  rules: [
    { id: "rules_approvals", href: "/rules/" },
    { id: "rules_dates", href: "/rules/dates/" },
    { id: "rules_permissions", href: "/rules/permissions/" },
    { id: "rules_archiving", href: "/rules/archiving/" },
    { id: "rules_projects", href: "/rules/projects/" },
  ],
  notifications: [
    { id: "notifications_email", href: "/notifications/" },
    { id: "notifications_sending", href: "/notifications/sending/" },
    { id: "notifications_schedule", href: "/notifications/schedule/" },
    { id: "notifications_roles", href: "/notifications/roles/" },
    { id: "notifications_preview", href: "/notifications/preview/" },
  ],
  modules: [
    { id: "modules_visibility", href: "/modules/" },
    { id: "modules_chat", href: "/modules/chat/" },
    { id: "modules_dashboards", href: "/modules/dashboards/" },
    { id: "modules_files", href: "/modules/files/" },
  ],
  integrations: [
    { id: "integrations_google", href: "/integrations/" },
    { id: "integrations_ai", href: "/integrations/ai/" },
    { id: "integrations_image", href: "/integrations/image/" },
  ],
  logs: [
    { id: "logs_activity", href: "/logs/" },
    { id: "logs_audit", href: "/logs/audit/" },
    { id: "logs_trash", href: "/logs/trash/" },
    { id: "logs_retention", href: "/logs/retention/" },
  ],
};
