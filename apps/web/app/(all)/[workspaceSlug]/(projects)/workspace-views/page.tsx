/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// components
import { PageHead } from "@/components/core/page-title";
import { ViewListAppliedFilters } from "@/components/views/view-list-applied-filters";
import { GlobalViewsList } from "@/components/workspace/views/views-list";
// hooks
import { useWorkspace } from "@/hooks/store/use-workspace";

/**
 * Kustomisasi Paradise: sama persis dengan halaman Views departemen (cari, urutan,
 * filter, chip filter aktif, baris, menu), memakai komponen dan state yang sama.
 */
function WorkspaceViewsPage() {
  const { currentWorkspace } = useWorkspace();
  const pageTitle = currentWorkspace?.name ? `${currentWorkspace?.name} - Views` : undefined;

  return (
    <>
      <PageHead title={pageTitle} />
      <ViewListAppliedFilters />
      <GlobalViewsList />
    </>
  );
}

export default observer(WorkspaceViewsPage);
