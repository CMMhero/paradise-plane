/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import useSWR from "swr";
// plane imports
import { DEFAULT_GLOBAL_VIEWS_LIST } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { EmptyStateDetailed } from "@plane/propel/empty-state";
import type { IProjectView, IWorkspaceView } from "@plane/types";
import { calculateTotalFilters } from "@plane/utils";
// components
import { ListLayout } from "@/components/core/list";
import { ViewListLoader } from "@/components/ui/loader/view-list-loader";
import { DefaultViewListItem } from "@/components/views/default-view-list-item";
import { ProjectViewListItem } from "@/components/views/view-list-item";
// hooks
import { useGlobalView } from "@/hooks/store/use-global-view";
import { useProjectView } from "@/hooks/store/use-project-view";
import { useWorkspace } from "@/hooks/store/use-workspace";
// local imports
import { GlobalViewListItem } from "./view-list-item";

type TBaris = { kind: "workspace"; view: IWorkspaceView } | { kind: "department"; view: IProjectView };

/**
 * Kustomisasi Paradise: halaman Views workspace = halaman Views departemen, 1:1.
 * Satu daftar, satu set filter/urutan/cari (state `projectView.filters` yang sama):
 * view bawaan di atas, lalu view workspace dan view departemen yang boleh dibuka
 * (disaring server di `/project-views/`), diurutkan bersama.
 */
export const GlobalViewsList = observer(function GlobalViewsList() {
  // router
  const { workspaceSlug: routerWorkspaceSlug } = useParams();
  const workspaceSlug = routerWorkspaceSlug?.toString();
  // plane hooks
  const { t } = useTranslation();
  // store hooks
  const { currentWorkspace } = useWorkspace();
  const { fetchAllGlobalViews, currentWorkspaceViews, getViewDetailsById } = useGlobalView();
  const { fetchWorkspaceProjectViews, getWorkspaceProjectViews, applyListFilters, filters } = useProjectView();

  useSWR(workspaceSlug ? `GLOBAL_VIEWS_LIST_${workspaceSlug}` : null, () =>
    workspaceSlug ? fetchAllGlobalViews(workspaceSlug) : null
  );
  useSWR(workspaceSlug ? `WORKSPACE_PROJECT_VIEWS_${workspaceSlug}` : null, () =>
    workspaceSlug ? fetchWorkspaceProjectViews(workspaceSlug) : null
  );

  const departmentViews = currentWorkspace ? getWorkspaceProjectViews(currentWorkspace.id) : undefined;
  if (!workspaceSlug || !currentWorkspaceViews || !departmentViews) return <ViewListLoader />;

  const workspaceViews = currentWorkspaceViews
    .map((id) => getViewDetailsById(id))
    .filter((view): view is IWorkspaceView => !!view);

  // View workspace dan departemen berbagi bentuk IssueView, jadi satu penyaring/pengurut melayani keduanya.
  const rows: TBaris[] = applyListFilters<IProjectView>([
    ...(workspaceViews as unknown as IProjectView[]),
    ...departmentViews,
  ]).map((view) =>
    view.project ? { kind: "department", view } : { kind: "workspace", view: view as unknown as IWorkspaceView }
  );

  // View bawaan tidak punya pemilik/tanggal/favorit: tampil selama yang dipakai hanya pencarian.
  const query = filters.searchQuery.toLowerCase();
  const defaultViews =
    calculateTotalFilters(filters.filters ?? {}) === 0
      ? DEFAULT_GLOBAL_VIEWS_LIST.filter((view) => t(view.i18n_label).toLowerCase().includes(query))
      : [];

  if (rows.length === 0 && defaultViews.length === 0) {
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
          <DefaultViewListItem key={view.key} view={view} workspaceSlug={workspaceSlug} />
        ))}
        {rows.map((row) =>
          row.kind === "department" ? (
            <ProjectViewListItem key={row.view.id} view={row.view} showScope />
          ) : (
            <GlobalViewListItem key={row.view.id} view={row.view} />
          )
        )}
      </ListLayout>
    </div>
  );
});
