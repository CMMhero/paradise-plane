/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { FileText, FolderPlus, Layers, SquarePlus } from "lucide-react";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { DiceIcon, LayersIcon } from "@plane/propel/icons";
// components
import { EUserProjectRoles } from "@plane/types";
import type { TPowerKCommandConfig, TPowerKContext } from "@/components/power-k/core/types";
// hooks
import { useCommandPalette } from "@/hooks/store/use-command-palette";
import { useProject } from "@/hooks/store/use-project";
import { useUser } from "@/hooks/store/user";
import { useInstance } from "@/hooks/store/use-instance";
import { useBolehBuatProject } from "@/hooks/use-boleh-buat-project";

export type TPowerKCreationCommandKeys =
  | "create_work_item"
  | "create_page"
  | "create_view"
  | "create_module"
  | "create_project"
  | "create_workspace";

/**
 * Creation commands - Create any entity in the app
 */
export const usePowerKCreationCommandsRecord = (): Record<TPowerKCreationCommandKeys, TPowerKCommandConfig> => {
  // store
  const { config } = useInstance();
  const {
    canPerformAnyCreateAction,
    permission: { allowPermissions },
  } = useUser();
  const { workspaceProjectIds, getPartialProjectById } = useProject();
  const {
    toggleCreateIssueModal,
    toggleCreateProjectModal,
    toggleCreateModuleModal,
    toggleCreateViewModal,
    toggleCreatePageModal,
  } = useCommandPalette();
  // derived values
  const canCreateWorkItem = canPerformAnyCreateAction && workspaceProjectIds && workspaceProjectIds.length > 0;
  // Paradise: staf / member biasa tidak boleh membuat project.
  const bolehBuatProject = useBolehBuatProject();
  const canCreateProject =
    allowPermissions([EUserPermissions.ADMIN, EUserPermissions.MEMBER], EUserPermissionsLevel.WORKSPACE) &&
    bolehBuatProject;
  const hasProjectMemberLevelPermissions = (ctx: TPowerKContext) =>
    allowPermissions(
      [EUserProjectRoles.ADMIN, EUserProjectRoles.MEMBER],
      EUserPermissionsLevel.PROJECT,
      ctx.params.workspaceSlug?.toString(),
      ctx.params.projectId?.toString()
    );
  const isWorkspaceCreationDisabled = config?.is_workspace_creation_disabled ?? false;

  const getProjectDetails = (ctx: TPowerKContext) =>
    ctx.params.projectId ? getPartialProjectById(ctx.params.projectId.toString()) : undefined;

  return {
    create_work_item: {
      id: "create_work_item",
      type: "action",
      group: "create",
      i18n_title: "power_k.creation_actions.create_work_item",
      icon: LayersIcon,
      keySequence: "ni",
      action: () => toggleCreateIssueModal(true),
      isEnabled: () => Boolean(canCreateWorkItem),
      isVisible: () => Boolean(canCreateWorkItem),
      closeOnSelect: true,
    },
    create_page: {
      id: "create_page",
      type: "action",
      group: "create",
      i18n_title: "power_k.creation_actions.create_page",
      icon: FileText,
      keySequence: "nd",
      action: () => toggleCreatePageModal({ isOpen: true }),
      isEnabled: (ctx) => Boolean(getProjectDetails(ctx)?.page_view && hasProjectMemberLevelPermissions(ctx)),
      isVisible: (ctx) =>
        Boolean(ctx.params.projectId && getProjectDetails(ctx)?.page_view && hasProjectMemberLevelPermissions(ctx)),
      closeOnSelect: true,
    },
    create_view: {
      id: "create_view",
      type: "action",
      group: "create",
      i18n_title: "power_k.creation_actions.create_view",
      icon: Layers,
      keySequence: "nv",
      action: () => toggleCreateViewModal(true),
      isEnabled: (ctx) => Boolean(getProjectDetails(ctx)?.issue_views_view && hasProjectMemberLevelPermissions(ctx)),
      isVisible: (ctx) =>
        Boolean(
          ctx.params.projectId && getProjectDetails(ctx)?.issue_views_view && hasProjectMemberLevelPermissions(ctx)
        ),
      closeOnSelect: true,
    },
    create_module: {
      id: "create_module",
      type: "action",
      group: "create",
      i18n_title: "power_k.creation_actions.create_module",
      icon: DiceIcon,
      keySequence: "nm",
      action: () => toggleCreateModuleModal(true),
      isEnabled: (ctx) => Boolean(getProjectDetails(ctx)?.module_view && hasProjectMemberLevelPermissions(ctx)),
      isVisible: (ctx) =>
        Boolean(ctx.params.projectId && getProjectDetails(ctx)?.module_view && hasProjectMemberLevelPermissions(ctx)),
      closeOnSelect: true,
    },
    create_project: {
      id: "create_project",
      type: "action",
      group: "create",
      i18n_title: "power_k.creation_actions.create_project",
      icon: FolderPlus,
      keySequence: "np",
      action: () => toggleCreateProjectModal(true),
      isEnabled: () => Boolean(canCreateProject),
      isVisible: () => Boolean(canCreateProject),
      closeOnSelect: true,
    },
    create_workspace: {
      id: "create_workspace",
      type: "action",
      group: "create",
      i18n_title: "power_k.creation_actions.create_workspace",
      icon: SquarePlus,
      action: (ctx) => ctx.router.push("/create-workspace"),
      isEnabled: () => Boolean(!isWorkspaceCreationDisabled),
      isVisible: () => Boolean(!isWorkspaceCreationDisabled),
      closeOnSelect: true,
    },
  };
};
