/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// components
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { cn } from "@plane/utils";
import { TopNavPowerK } from "@/components/navigation";
import { NotificationsPopover } from "@/components/workspace-notifications/popover/root";
import { HelpMenuRoot } from "@/components/workspace/sidebar/help-section/root";
import { UserMenuRoot } from "@/components/workspace/sidebar/user-menu-root";
import { WorkspaceMenuRoot } from "@/components/workspace/sidebar/workspace-menu-root";
import { useAppRailPreferences } from "@/hooks/use-navigation-preferences";
import { useParadiseModules } from "@/hooks/use-paradise-module";

export const TopNavigationRoot = observer(function TopNavigationRoot() {
  // router
  const { workspaceSlug } = useParams();

  // store hooks
  const { preferences } = useAppRailPreferences();
  // Modul "inbox" dimatikan di God Mode = rute /notifications ditutup; lonceng ikut hilang.
  const { isModuleEnabled } = useParadiseModules();

  const showLabel = preferences.displayMode === "icon_with_label";

  return (
    <div
      className={cn("z-[27] flex min-h-10 w-full items-center bg-canvas px-3.5 transition-all duration-300", {
        "px-2": !showLabel,
      })}
    >
      {/* Workspace Menu */}
      <div className="min-w-0 flex-1">
        <WorkspaceMenuRoot variant="top-navigation" />
      </div>
      {/* Power K Search */}
      <div className="shrink-0 px-1">
        <TopNavPowerK />
      </div>
      {/* Additional Actions */}
      <div className="flex shrink-0 items-center justify-end gap-1 md:flex-1">
        {/* Paradise: lonceng membuka popover di tempat (lihat workspace-notifications/popover),
            bukan pindah ke /notifications. Lencana jumlah ikut pindah ke sana. */}
        {workspaceSlug && isModuleEnabled("inbox") && <NotificationsPopover workspaceSlug={workspaceSlug.toString()} />}
        <HelpMenuRoot />
        {/* Link "Star us on GitHub" dibuang: ini instrumen promosi upstream, tidak
            ada gunanya di alat internal kantor. Header hak cipta di berkas sumber,
            LICENSE, dan NOTICE.md TETAP, yang dibuang merek produk, bukan
            atribusi hukum. */}
        <div className="flex size-8 items-center justify-center rounded-md hover:bg-layer-1-hover">
          <UserMenuRoot />
        </div>
      </div>
    </div>
  );
});
