/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// components
import { Outlet } from "react-router";
import { AppHeader } from "@/components/core/app-header";
import { ContentWrapper } from "@/components/core/content-wrapper";
import { ProjectIssuesHeader } from "./header";

export default function ProjectIssuesLayout() {
  return (
    <>
      {/* Paradise: alat HP ikut di dalam baris header (lihat ./header.tsx), bukan mobileHeader terpisah. */}
      <AppHeader header={<ProjectIssuesHeader />} />
      <ContentWrapper>
        <Outlet />
      </ContentWrapper>
    </>
  );
}
