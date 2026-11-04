/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
// components
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { PageHead } from "@/components/core/page-title";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { SettingsHeading } from "@/components/settings/heading";
import { ProjectSettingsFeatureControlItem } from "@/components/settings/project/content/feature-control-item";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
import { useIzinSumber } from "@/hooks/use-izin-sumber";
// local imports
import type { Route } from "./+types/page";
import { FeaturesIntakeProjectSettingsHeader } from "./header";

function FeaturesIntakeSettingsPage({ params }: Route.ComponentProps) {
  const { workspaceSlug, projectId } = params;
  // store hooks
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();
  const { currentProjectDetails } = useProject();
  // translation
  const { t } = useTranslation();
  // derived values
  const pageTitle = currentProjectDetails?.name
    ? `${currentProjectDetails?.name} settings - ${t("project_settings.features.intake.short_title")}`
    : undefined;
  const canPerformProjectAdminActions = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT);
  // Paradise KEP-85: menyalakan/mematikan intake = aturan struktur PERM_PROJECT_WORKFLOW.
  const izin = useIzinSumber(workspaceSlug, projectId);

  if (workspaceUserInfo && !canPerformProjectAdminActions) {
    return <NotAuthorizedView section="settings" isProjectView className="h-auto" />;
  }

  return (
    <SettingsContentWrapper header={<FeaturesIntakeProjectSettingsHeader />}>
      <PageHead title={pageTitle} />
      <section className="w-full">
        <SettingsHeading
          title={t("project_settings.features.intake.title")}
          description={t("project_settings.features.intake.description")}
        />
        <div className="mt-7">
          <ProjectSettingsFeatureControlItem
            title={t("project_settings.features.intake.toggle_title")}
            description={t("project_settings.features.intake.toggle_description")}
            featureProperty="inbox_view"
            projectId={projectId}
            value={!!currentProjectDetails?.inbox_view}
            disabled={!izin.struktur("PERM_PROJECT_WORKFLOW")}
            workspaceSlug={workspaceSlug}
          />
        </div>
      </section>
    </SettingsContentWrapper>
  );
}

export default observer(FeaturesIntakeSettingsPage);
