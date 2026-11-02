/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tab Persetujuan per divisi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { Stamp } from "lucide-react";
import { useTranslation } from "@plane/i18n";
// ui
import { Breadcrumbs, Header } from "@plane/ui";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
// plane web imports
import { CommonProjectBreadcrumbs } from "@/plane-web/components/breadcrumbs/common";

export const PersetujuanDivisiHeader = observer(function PersetujuanDivisiHeader() {
  // router
  const { t } = useTranslation();
  const { workspaceSlug, projectId } = useParams();

  return (
    <Header>
      <Header.LeftItem>
        <div className="flex flex-grow items-center gap-4">
          <Breadcrumbs>
            <CommonProjectBreadcrumbs workspaceSlug={workspaceSlug?.toString()} projectId={projectId?.toString()} />
            <Breadcrumbs.Item
              component={
                <BreadcrumbLink
                  label={t("sidebar.persetujuan")}
                  href={`/${workspaceSlug}/projects/${projectId}/persetujuan/`}
                  icon={<Stamp className="h-4 w-4 text-tertiary" />}
                  isLast
                />
              }
              isLast
            />
          </Breadcrumbs>
        </div>
      </Header.LeftItem>
    </Header>
  );
});
