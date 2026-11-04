/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
// components
import { PageHead } from "@/components/core/page-title";
import { ProjectDetailsForm } from "@/components/project/form";
import { ProjectDetailsFormLoader } from "@/components/project/form-loader";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
import { useIzinSumber } from "@/hooks/use-izin-sumber";
// local imports
import type { Route } from "./+types/page";
import { GeneralProjectSettingsHeader } from "./header";
import { GeneralProjectSettingsControlSection } from "@/components/project/settings/control-section";

function ProjectSettingsPage({ params }: Route.ComponentProps) {
  // router
  const { workspaceSlug, projectId } = params;
  // store hooks
  const { currentProjectDetails } = useProject();
  const { allowPermissions } = useUserPermissions();
  // derived values
  const isProjectAdmin = allowPermissions(
    [EUserPermissions.ADMIN],
    EUserPermissionsLevel.PROJECT,
    workspaceSlug,
    projectId
  );
  // Paradise KEP-85: setelan project = aturan struktur PERM_PROJECT_EDIT (arsip/hapus dinilai di control section).
  const izin = useIzinSumber(workspaceSlug, projectId);
  const isAdmin = isProjectAdmin && izin.struktur("PERM_PROJECT_EDIT");

  const pageTitle = currentProjectDetails?.name ? `${currentProjectDetails?.name} - General Settings` : undefined;

  return (
    <SettingsContentWrapper header={<GeneralProjectSettingsHeader />}>
      <PageHead title={pageTitle} />
      <div className={`w-full ${isAdmin ? "" : "opacity-60"}`}>
        {currentProjectDetails ? (
          <ProjectDetailsForm
            project={currentProjectDetails}
            workspaceSlug={workspaceSlug}
            projectId={projectId}
            isAdmin={isAdmin}
          />
        ) : (
          <ProjectDetailsFormLoader />
        )}
        {isProjectAdmin && <GeneralProjectSettingsControlSection projectId={projectId} />}
      </div>
    </SettingsContentWrapper>
  );
}

export default observer(ProjectSettingsPage);
