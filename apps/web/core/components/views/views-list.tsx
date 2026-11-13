/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { DEFAULT_GLOBAL_VIEWS_LIST } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { EmptyStateDetailed } from "@plane/propel/empty-state";
import { calculateTotalFilters } from "@plane/utils";
// components
import { ListLayout } from "@/components/core/list";
import { ViewListLoader } from "@/components/ui/loader/view-list-loader";
// hooks
import { useProjectView } from "@/hooks/store/use-project-view";
// local imports
import { DefaultViewListItem } from "./default-view-list-item";
import { ProjectViewListItem } from "./view-list-item";

export const ProjectViewsList = observer(function ProjectViewsList() {
  const { workspaceSlug, projectId } = useParams();
  // plane hooks
  const { t } = useTranslation();
  // store hooks
  const { getProjectViews, getFilteredProjectViews, loader, filters } = useProjectView();
  // derived values
  const projectViews = getProjectViews(projectId?.toString());
  const filteredProjectViews = getFilteredProjectViews(projectId?.toString());

  if (loader || !projectViews || !filteredProjectViews || !workspaceSlug || !projectId) return <ViewListLoader />;

  // Kustomisasi Paradise: view bawaan (All work items, Assigned, Created, Subscribed) selalu ada
  // di tiap departemen, sama dengan halaman Views workspace. Mereka tidak punya pemilik,
  // tanggal, atau favorit, jadi hanya ikut pencarian; filter lain menyembunyikannya.
  const query = filters.searchQuery.toLowerCase();
  const defaultViews =
    calculateTotalFilters(filters.filters ?? {}) === 0
      ? DEFAULT_GLOBAL_VIEWS_LIST.filter((view) => t(view.i18n_label).toLowerCase().includes(query))
      : [];

  if (filteredProjectViews.length === 0 && defaultViews.length === 0) {
    return (
      <EmptyStateDetailed
        assetKey="search"
        title={t("common_empty_state.search.title")}
        description={t("common_empty_state.search.description")}
      />
    );
  }

  return (
    <div className="flex h-full w-full flex-col">
      <ListLayout>
        {defaultViews.map((view) => (
          <DefaultViewListItem
            key={view.key}
            view={view}
            workspaceSlug={workspaceSlug.toString()}
            projectId={projectId.toString()}
          />
        ))}
        {filteredProjectViews.map((view) => (
          <ProjectViewListItem key={view.id} view={view} />
        ))}
      </ListLayout>
    </div>
  );
});
