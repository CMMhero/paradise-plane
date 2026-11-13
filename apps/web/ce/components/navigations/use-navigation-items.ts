/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo, useCallback } from "react";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { BookOpen, Stamp } from "lucide-react";
import { CycleIcon, IntakeIcon, ModuleIcon, PageIcon, ViewsIcon, WorkItemsIcon } from "@plane/propel/icons";
import type { EUserProjectRoles, IPartialProject } from "@plane/types";
import type { TNavigationItem } from "@/components/navigation/tab-navigation-root";
import { useInstance } from "@/hooks/store/use-instance";
import { useFolderWikiProject } from "@/hooks/use-pohon-wiki";
import { WIKI_MATERIALS_NAV_KEY, isNavKeyEnabled } from "@/lib/paradise-modules";

type UseNavigationItemsProps = {
  workspaceSlug: string;
  projectId: string;
  project?: IPartialProject;
  allowPermissions: (
    access: EUserPermissions[] | EUserProjectRoles[],
    level: EUserPermissionsLevel,
    workspaceSlug: string,
    projectId: string
  ) => boolean;
};

export const useNavigationItems = ({
  workspaceSlug,
  projectId,
  project,
  allowPermissions,
}: UseNavigationItemsProps): TNavigationItem[] => {
  // Modul yang dimatikan di God Mode > Features (Views) tidak muncul sebagai tab.
  const { config: instanceConfig } = useInstance();
  const folderWiki = useFolderWikiProject(
    workspaceSlug,
    projectId,
    isNavKeyEnabled(instanceConfig, WIKI_MATERIALS_NAV_KEY)
  );
  // Base navigation items
  const baseNavigation = useCallback(
    (slug: string, id: string): TNavigationItem[] => [
      {
        i18n_key: "sidebar.work_items",
        key: "work_items",
        name: "Work items",
        href: `/${slug}/projects/${id}/issues`,
        icon: WorkItemsIcon,
        access: [EUserPermissions.ADMIN, EUserPermissions.MEMBER, EUserPermissions.GUEST],
        shouldRender: true,
        sortOrder: 1,
      },
      {
        i18n_key: "sidebar.cycles",
        key: "cycles",
        name: "Cycles",
        href: `/${slug}/projects/${id}/cycles`,
        icon: CycleIcon,
        access: [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
        shouldRender: !!project?.cycle_view,
        sortOrder: 2,
      },
      {
        i18n_key: "sidebar.modules",
        key: "modules",
        name: "Modules",
        href: `/${slug}/projects/${id}/modules`,
        icon: ModuleIcon,
        access: [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
        shouldRender: !!project?.module_view,
        sortOrder: 3,
      },
      {
        i18n_key: "sidebar.views",
        key: "views",
        name: "Views",
        href: `/${slug}/projects/${id}/views`,
        icon: ViewsIcon,
        access: [EUserPermissions.ADMIN, EUserPermissions.MEMBER, EUserPermissions.GUEST],
        shouldRender: !!project?.issue_views_view,
        sortOrder: 4,
      },
      {
        i18n_key: "sidebar.pages",
        key: "pages",
        name: "Pages",
        href: `/${slug}/projects/${id}/pages`,
        icon: PageIcon,
        access: [EUserPermissions.ADMIN, EUserPermissions.MEMBER, EUserPermissions.GUEST],
        shouldRender: !!project?.page_view,
        sortOrder: 5,
      },
      {
        i18n_key: "sidebar.intake",
        key: "intake",
        name: "Intake",
        href: `/${slug}/projects/${id}/intake`,
        icon: IntakeIcon,
        access: [EUserPermissions.ADMIN, EUserPermissions.MEMBER, EUserPermissions.GUEST],
        shouldRender: !!project?.inbox_view,
        sortOrder: 6,
      },
      // Paradise: antrean persetujuan (KEP-55), cermin item di sidebar
      // (`project-navigation.tsx`) supaya tab header dan sidebar sama.
      {
        i18n_key: "sidebar.persetujuan",
        key: "persetujuan",
        name: "Approval",
        href: `/${slug}/projects/${id}/persetujuan`,
        icon: Stamp,
        access: [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
        shouldRender: true,
        sortOrder: 7,
      },
      // Paradise KEP-97: materi Wiki departemen ini. Ikut modul Wiki (God Mode)
      // dan hanya tampil kalau project ini milik departemen yang punya folder Wiki.
      {
        i18n_key: "wiki_ui.tab.title",
        key: WIKI_MATERIALS_NAV_KEY,
        name: "Materials",
        href: `/${slug}/projects/${id}/materials`,
        icon: BookOpen,
        access: [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
        shouldRender: !!folderWiki,
        sortOrder: 8,
      },
    ],
    [project, folderWiki]
  );

  // Combine, filter, and sort navigation items
  const navigationItems = useMemo(() => {
    const navItems = baseNavigation(workspaceSlug, projectId);

    // Filter by permissions and shouldRender
    const filteredItems = navItems.filter((item) => {
      if (!item.shouldRender || !isNavKeyEnabled(instanceConfig, item.key)) return false;
      const hasAccess = allowPermissions(item.access, EUserPermissionsLevel.PROJECT, workspaceSlug, project?.id ?? "");
      return hasAccess;
    });

    // Sort by sortOrder
    // oxlint-disable-next-line unicorn/no-array-sort -- filteredItems is a fresh array; lib is ES2022 so toSorted does not type-check
    return filteredItems.sort((a, b) => (a.sortOrder || 0) - (b.sortOrder || 0));
  }, [workspaceSlug, projectId, baseNavigation, allowPermissions, project?.id, instanceConfig]);

  return navigationItems;
};
