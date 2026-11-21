/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// components
import { Navigate, Outlet, useParams } from "react-router";
import { AppHeader } from "@/components/core/app-header";
import { ContentWrapper } from "@/components/core/content-wrapper";
// hooks
import { useIsDirektur } from "@/hooks/use-is-direktur";
// local components
import { ProjectsListHeader } from "@/plane-web/components/projects/header";
import { ProjectsListMobileHeader } from "@/plane-web/components/projects/mobile-header";

function ProjectListLayout() {
  const { workspaceSlug } = useParams();
  const { hiddenNavKeys } = useIsDirektur(workspaceSlug);
  // Arsip disembunyikan untuk Direktur (God Mode, DIRECTOR_SIDEBAR_HIDES): arahkan ke beranda,
  // sama seperti halaman lain yang tertutup.
  if (hiddenNavKeys.includes("archives")) return <Navigate to={`/${workspaceSlug}/`} replace />;
  return (
    <>
      <AppHeader header={<ProjectsListHeader />} mobileHeader={<ProjectsListMobileHeader />} />
      <ContentWrapper>
        <Outlet />
      </ContentWrapper>
    </>
  );
}

export default observer(ProjectListLayout);
