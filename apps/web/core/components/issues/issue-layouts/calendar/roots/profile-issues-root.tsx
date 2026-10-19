/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kalender di halaman Your Work
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
// hooks
import { useUserPermissions } from "@/hooks/store/user";
// local imports
import { ProjectIssueQuickActions } from "../../quick-action-dropdowns";
import { BaseCalendarRoot } from "../base-calendar-root";

type Props = {
  /** "assigned" | "created" | "subscribed". Store profil menolak memuat apa pun tanpa ini. */
  viewId: string;
};

export const ProfileIssuesCalendarLayout = observer(function ProfileIssuesCalendarLayout(props: Props) {
  const { viewId } = props;
  // router
  const { workspaceSlug } = useParams();
  // store hooks
  const { allowPermissions } = useUserPermissions();

  // Halaman ini melintasi banyak project sekaligus, jadi hak edit diperiksa
  // PER PROJECT, bukan sekali untuk seluruh halaman. Seseorang bisa jadi member
  // di project A dan cuma guest di project B, dan work item keduanya muncul di
  // kalender yang sama.
  const canEditPropertiesBasedOnProject = (projectId: string) =>
    allowPermissions(
      [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
      EUserPermissionsLevel.PROJECT,
      workspaceSlug?.toString(),
      projectId
    );

  return (
    <BaseCalendarRoot
      QuickActions={ProjectIssueQuickActions}
      canEditPropertiesBasedOnProject={canEditPropertiesBasedOnProject}
      viewId={viewId}
    />
  );
});
