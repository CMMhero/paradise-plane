/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// components
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { PageHead } from "@/components/core/page-title";
import { EstimateRoot } from "@/components/estimates";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
import { useIzinSumber } from "@/hooks/use-izin-sumber";
// local imports
// Tipe props ditulis tangan, peninggalan masa rute ini bisa dibuang saat build.
// Sekarang rutenya selalu terdaftar dan dijaga ParadiseModuleGate (God Mode).
type TPageProps = { params: { workspaceSlug: string; projectId: string } };
import { EstimatesProjectSettingsHeader } from "./header";

function EstimatesSettingsPage({ params }: TPageProps) {
  const { workspaceSlug, projectId } = params;
  // store
  const { currentProjectDetails } = useProject();
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();

  // derived values
  const pageTitle = currentProjectDetails?.name ? `${currentProjectDetails?.name} - Estimates` : undefined;
  const canPerformProjectAdminActions = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT);
  // Paradise KEP-85: estimate = alur kerja, aturan struktur PERM_PROJECT_WORKFLOW.
  const izin = useIzinSumber(workspaceSlug, projectId);
  const bolehUbahAlur = canPerformProjectAdminActions && izin.struktur("PERM_PROJECT_WORKFLOW");

  if (workspaceUserInfo && !canPerformProjectAdminActions) {
    return <NotAuthorizedView section="settings" isProjectView className="h-auto" />;
  }

  return (
    <SettingsContentWrapper header={<EstimatesProjectSettingsHeader />}>
      <PageHead title={pageTitle} />
      <div className={`w-full ${bolehUbahAlur ? "" : "pointer-events-none opacity-60"}`}>
        <EstimateRoot workspaceSlug={workspaceSlug} projectId={projectId} isAdmin={bolehUbahAlur} />
      </div>
    </SettingsContentWrapper>
  );
}

export default observer(EstimatesSettingsPage);
