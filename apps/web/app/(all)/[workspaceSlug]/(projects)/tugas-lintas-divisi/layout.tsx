/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Tugas Lintas Divisi 
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// components
import { Outlet } from "react-router";
import { AppHeader } from "@/components/core/app-header";
import { ContentWrapper } from "@/components/core/content-wrapper";
// local imports
import { TugasLintasDivisiHeader } from "./header";

export default function TugasLintasDivisiLayout() {
  return (
    <>
      <AppHeader header={<TugasLintasDivisiHeader />} />
      <ContentWrapper>
        <Outlet />
      </ContentWrapper>
    </>
  );
}
