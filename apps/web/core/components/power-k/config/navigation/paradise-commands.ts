/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: perintah navigasi untuk fitur Paradise
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { BookText, CalendarDays, LayoutDashboard, Link2, MessageSquare, Stamp, Target, UserCog } from "lucide-react";
// plane imports
import { EUserPermissionsLevel } from "@plane/constants";
import { MultipleStickyIcon } from "@plane/propel/icons";
import type { TProfileSettingsTabs } from "@plane/types";
import { EUserProjectRoles, EUserWorkspaceRoles } from "@plane/types";
// components
import type { TPowerKCommandConfig, TPowerKContext } from "@/components/power-k/core/types";
import { handlePowerKNavigate } from "@/components/power-k/utils/navigation";
// hooks
import { useCommandPalette } from "@/hooks/store/use-command-palette";
import { useUser } from "@/hooks/store/user";

export type TPowerKParadiseNavigationCommandKeys =
  | "nav_chat"
  | "nav_wiki"
  | "nav_dashboard_divisi"
  | "nav_initiatives"
  | "nav_stickies"
  | "nav_quick_links"
  | "nav_your_work_calendar"
  | "nav_project_approvals"
  | "open_account_setting";

const slugOf = (ctx: TPowerKContext) => ctx.params.workspaceSlug?.toString();
const inWorkspace = (ctx: TPowerKContext) => Boolean(slugOf(ctx));
const inProject = (ctx: TPowerKContext) => Boolean(slugOf(ctx) && ctx.params.projectId?.toString());

/**
 * Halaman Paradise yang punya menu di sidebar atau tab project. Akses tiap
 * perintah cermin `access` item sidebar-nya (`WORKSPACE_SIDEBAR_*` di
 * packages/constants/src/workspace.ts, tab Approval di use-navigation-items.ts);
 * saklar modul God Mode dipasang di core/paradise-gates.ts, bukan di sini, supaya
 * pintasan kuncinya ikut mati.
 */
export const usePowerKParadiseNavigationCommandsRecord = (): Record<
  TPowerKParadiseNavigationCommandKeys,
  TPowerKCommandConfig
> => {
  const {
    data: currentUser,
    permission: { allowPermissions },
  } = useUser();
  const { toggleProfileSettingsModal } = useCommandPalette();

  const hasWorkspaceRole = (ctx: TPowerKContext, roles: EUserWorkspaceRoles[]) =>
    inWorkspace(ctx) && allowPermissions(roles, EUserPermissionsLevel.WORKSPACE, slugOf(ctx));
  const isWorkspaceMember = (ctx: TPowerKContext) =>
    hasWorkspaceRole(ctx, [EUserWorkspaceRoles.ADMIN, EUserWorkspaceRoles.MEMBER]);
  const isAnyWorkspaceRole = (ctx: TPowerKContext) =>
    hasWorkspaceRole(ctx, [EUserWorkspaceRoles.ADMIN, EUserWorkspaceRoles.MEMBER, EUserWorkspaceRoles.GUEST]);
  const isProjectMember = (ctx: TPowerKContext) =>
    inProject(ctx) &&
    allowPermissions(
      [EUserProjectRoles.ADMIN, EUserProjectRoles.MEMBER],
      EUserPermissionsLevel.PROJECT,
      slugOf(ctx),
      ctx.params.projectId?.toString()
    );

  /** Perintah "Go to ..." ke satu halaman workspace. */
  const workspacePage = (
    id: TPowerKParadiseNavigationCommandKeys,
    icon: TPowerKCommandConfig["icon"],
    segments: (ctx: TPowerKContext) => (string | undefined)[],
    isAllowed: (ctx: TPowerKContext) => boolean,
    keySequence?: string
  ): TPowerKCommandConfig => ({
    id,
    type: "action",
    group: "navigation",
    i18n_title: `power_k.navigation_actions.${id}`,
    icon,
    keySequence,
    action: (ctx) => handlePowerKNavigate(ctx, [slugOf(ctx), ...segments(ctx)]),
    isEnabled: isAllowed,
    isVisible: isAllowed,
    closeOnSelect: true,
  });

  return {
    nav_chat: workspacePage("nav_chat", MessageSquare, () => ["chat"], isWorkspaceMember, "gc"),
    nav_wiki: workspacePage("nav_wiki", BookText, () => ["wiki"], isWorkspaceMember, "gw"),
    nav_dashboard_divisi: workspacePage(
      "nav_dashboard_divisi",
      LayoutDashboard,
      () => ["dashboard-divisi"],
      (ctx) => hasWorkspaceRole(ctx, [EUserWorkspaceRoles.ADMIN]),
      "gb"
    ),
    nav_initiatives: workspacePage("nav_initiatives", Target, () => ["initiatives"], isWorkspaceMember),
    nav_stickies: workspacePage("nav_stickies", MultipleStickyIcon, () => ["stickies"], isAnyWorkspaceRole, "gt"),
    nav_quick_links: workspacePage("nav_quick_links", Link2, () => ["quick-links"], isAnyWorkspaceRole, "gl"),
    nav_your_work_calendar: workspacePage(
      "nav_your_work_calendar",
      CalendarDays,
      () => ["profile", currentUser?.id, "calendar"],
      (ctx) => isWorkspaceMember(ctx) && Boolean(currentUser?.id)
    ),
    nav_project_approvals: {
      id: "nav_project_approvals",
      type: "action",
      group: "navigation",
      i18n_title: "power_k.navigation_actions.nav_project_approvals",
      icon: Stamp,
      keySequence: "gq",
      action: (ctx) =>
        handlePowerKNavigate(ctx, [slugOf(ctx), "projects", ctx.params.projectId?.toString(), "persetujuan"]),
      isEnabled: isProjectMember,
      isVisible: isProjectMember,
      closeOnSelect: true,
    },
    open_account_setting: {
      id: "open_account_setting",
      type: "change-page",
      group: "navigation",
      i18n_title: "power_k.navigation_actions.open_account_setting",
      icon: UserCog,
      keySequence: "oa",
      page: "open-account-setting",
      onSelect: (data) => toggleProfileSettingsModal({ activeTab: data as TProfileSettingsTabs, isOpen: true }),
      isEnabled: () => true,
      isVisible: () => true,
      closeOnSelect: true,
    },
  };
};
