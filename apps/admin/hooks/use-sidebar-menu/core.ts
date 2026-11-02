/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Cog, KeyRound, Mail, ScrollText, ToggleRight, Users } from "lucide-react";
// plane imports
import { LockIcon, WorkspaceIcon } from "@plane/propel/icons";
// types
import type { TSidebarMenuItem } from "./types";

export type TCoreSidebarMenuKey =
  | "general"
  | "email"
  | "workspace"
  | "authentication"
  | "features"
  | "members"
  | "logs"
  | "apiKeys";

export const coreSidebarMenuLinks: Record<TCoreSidebarMenuKey, TSidebarMenuItem> = {
  general: {
    Icon: Cog,
    name: "General",
    description: "Identify your instances and get key details.",
    href: `/general/`,
  },
  email: {
    Icon: Mail,
    name: "Email",
    description: "Configure your SMTP controls.",
    href: `/email/`,
  },
  workspace: {
    Icon: WorkspaceIcon,
    name: "Workspaces",
    description: "Manage all workspaces on this instance.",
    href: `/workspace/`,
  },
  authentication: {
    Icon: LockIcon,
    name: "Authentication",
    description: "Configure authentication modes.",
    href: `/authentication/`,
  },
  // Paradise. Accounts, organization structure, and new member defaults (tabs).
  members: {
    Icon: Users,
    name: "Members",
    description: "Accounts, organization, and defaults.",
    href: `/members/`,
  },
  // Paradise. Sign-in activity, the audit log, and the trash (tabs).
  logs: {
    Icon: ScrollText,
    name: "Logs",
    description: "Activity, audit log, and trash.",
    href: `/logs/`,
  },
  // Paradise. Modules, automations, and operational settings (KEP-40).
  features: {
    Icon: ToggleRight,
    name: "Features",
    description: "Modules, automations, and timings.",
    href: `/features/`,
  },
  // Paradise. AI, image library, and Google credentials (tabs).
  apiKeys: {
    Icon: KeyRound,
    name: "API keys",
    description: "AI, image library, and Google credentials.",
    href: `/api-keys/`,
  },
};
