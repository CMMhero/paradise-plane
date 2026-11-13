/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Outlet } from "react-router";
import { AuthenticationWrapper } from "@/lib/wrappers/authentication-wrapper";
import { WorkspaceContentWrapper } from "@/plane-web/components/workspace/content-wrapper";
import { AppRailVisibilityProvider } from "@/lib/app-rail";
import { GlobalModals } from "@/plane-web/components/common/modal/global";
import { PenjagaNotifikasi } from "@/components/notifikasi/penjaga";
import { SambunganKehadiran } from "@/components/chat/titik-kehadiran";
import { PenyegarLangsung } from "@/components/data-live/penyegar-langsung";
import { PendengarPengajuanPersetujuan } from "@/components/issues/approval-requested-listener";
import { WorkspaceAuthWrapper } from "@/layouts/auth-layout/workspace-wrapper";
import { PenyediaPanggilan } from "./(projects)/chat/penyedia-panggilan";
import type { Route } from "./+types/layout";

export default function WorkspaceLayout(props: Route.ComponentProps) {
  const { workspaceSlug } = props.params;

  return (
    <AuthenticationWrapper>
      <WorkspaceAuthWrapper>
        <AppRailVisibilityProvider>
          <WorkspaceContentWrapper>
            <GlobalModals workspaceSlug={workspaceSlug} />
            {/* Kustomisasi Paradise: dipasang di lapisan workspace,
                bukan di halaman Obrolan atau panel Pemberitahuan. Pemberitahuan yang cuma
                muncul di halaman yang bersangkutan tidak memberi tahu apa pun: orangnya
                sudah ada di sana. */}
            <PenjagaNotifikasi workspaceSlug={workspaceSlug} />
            {/* Satu soket kehadiran per tab: titik online/away di Obrolan. */}
            <SambunganKehadiran workspaceSlug={workspaceSlug} />
            {/* Layar hidup: pendengar dokumen + jam cadangan saat soket putus. */}
            <PenyegarLangsung />
            <PendengarPengajuanPersetujuan />
            {/* Panggilan hidup di sini, bukan di halaman Obrolan: dering sampai
                ke halaman mana pun, dan pindah halaman tidak memutus panggilan. */}
            <PenyediaPanggilan workspaceSlug={workspaceSlug}>
              <Outlet />
            </PenyediaPanggilan>
          </WorkspaceContentWrapper>
        </AppRailVisibilityProvider>
      </WorkspaceAuthWrapper>
    </AuthenticationWrapper>
  );
}
