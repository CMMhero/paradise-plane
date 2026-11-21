/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: perintah navigasi untuk fitur Paradise
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useParams } from "next/navigation";
import {
  ArrowLeftRight,
  BookText,
  CalendarDays,
  Gauge,
  LayoutDashboard,
  Link2,
  Megaphone,
  MessageSquare,
  Stamp,
  Target,
  UserCog,
} from "lucide-react";
// plane imports
import { EUserPermissionsLevel, PARADISE_NAV_ITEMS } from "@plane/constants";
import type { TParadiseNavKey, TParadiseNavPaletteId } from "@plane/constants";
import { MultipleStickyIcon } from "@plane/propel/icons";
import type { TProfileSettingsTabs } from "@plane/types";
import { EUserProjectRoles, EUserWorkspaceRoles } from "@plane/types";
// components
import type { TPowerKCommandConfig, TPowerKContext } from "@/components/power-k/core/types";
import { handlePowerKNavigate } from "@/components/power-k/utils/navigation";
// hooks
import { useCommandPalette } from "@/hooks/store/use-command-palette";
import { useUser } from "@/hooks/store/user";
import { useNavPersetujuanTerlihat } from "@/plane-web/components/workspace/sidebar/sidebar-item";

export type TPowerKParadiseNavigationCommandKeys =
  | TParadiseNavPaletteId
  | "nav_dashboard_divisi"
  | "nav_stickies"
  | "nav_quick_links"
  | "nav_your_work_calendar"
  | "nav_project_approvals"
  | "open_account_setting";

/** Ikon perintah menu Paradise; sama dengan ikon sidebar-nya (helper.tsx). */
const IKON_MENU: Record<TParadiseNavKey, TPowerKCommandConfig["icon"]> = {
  kinerja: Gauge,
  initiatives: Target,
  persetujuan: Stamp,
  tugas_lintas_divisi: ArrowLeftRight,
  chat: MessageSquare,
  pengumuman: Megaphone,
  wiki: BookText,
};

const slugOf = (ctx: TPowerKContext) => ctx.params.workspaceSlug?.toString();
const inWorkspace = (ctx: TPowerKContext) => Boolean(slugOf(ctx));
const inProject = (ctx: TPowerKContext) => Boolean(slugOf(ctx) && ctx.params.projectId?.toString());

/**
 * Halaman Paradise yang punya menu di sidebar atau tab project. Perintah menu
 * workspace diturunkan dari `PARADISE_NAV_ITEMS` (packages/constants): id,
 * tujuan, akses, dan pintasan sama persis dengan item sidebar-nya. Saklar modul
 * God Mode dipasang di core/paradise-gates.ts, bukan di sini, supaya pintasan
 * kuncinya ikut mati.
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
  const { workspaceSlug } = useParams();
  // Sama dengan menu sidebar: hanya yang punya wewenang memutuskan.
  const persetujuanTerlihat = useNavPersetujuanTerlihat(workspaceSlug?.toString());

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

  // Aturan tambahan di atas `access` registri, sama dengan sidebar.
  const tambahan: Partial<Record<TParadiseNavKey, boolean>> = { persetujuan: persetujuanTerlihat };
  const perintahMenu = Object.fromEntries(
    PARADISE_NAV_ITEMS.flatMap((item) => {
      if (!("palette" in item)) return [];
      const { id, titleKey, keySequence }: { id: TParadiseNavPaletteId; titleKey?: string; keySequence?: string } =
        item.palette;
      const isAllowed = (ctx: TPowerKContext) =>
        hasWorkspaceRole(ctx, [...item.access]) && (tambahan[item.key] ?? true);
      const perintah = workspacePage(id, IKON_MENU[item.key], () => [item.href], isAllowed, keySequence);
      return [[id, titleKey ? { ...perintah, i18n_title: titleKey } : perintah]];
    })
  ) as Record<TParadiseNavPaletteId, TPowerKCommandConfig>;

  return {
    ...perintahMenu,
    nav_dashboard_divisi: workspacePage(
      "nav_dashboard_divisi",
      LayoutDashboard,
      () => ["kinerja", "dasbor"],
      (ctx) => hasWorkspaceRole(ctx, [EUserWorkspaceRoles.ADMIN]),
      "gb"
    ),
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
