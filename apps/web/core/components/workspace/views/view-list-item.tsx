/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useRef } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { Logo } from "@plane/propel/emoji-icon-picker";
import { ViewsIcon } from "@plane/propel/icons";
import type { IWorkspaceView } from "@plane/types";
// components
import { ListItem } from "@/components/core/list";
import { ViewListItemMeta } from "@/components/views/view-list-item-meta";
// hooks
import { usePlatformOS } from "@/hooks/use-platform-os";
// local imports
import { WorkspaceViewQuickActions } from "./quick-action";

type Props = { view: IWorkspaceView };

/**
 * Kustomisasi Paradise: baris view workspace memakai `ListItem` dan metadata yang sama
 * dengan baris view departemen (ikon, akses, pemilik, menu, klik kanan). Bedanya
 * hanya tanpa bintang favorit: favorit view di server terikat ke departemen.
 */
export const GlobalViewListItem = observer(function GlobalViewListItem({ view }: Props) {
  // refs
  const parentRef = useRef(null);
  // router
  const { workspaceSlug } = useParams();
  // hooks
  const { isMobile } = usePlatformOS();

  if (!workspaceSlug) return null;

  return (
    <ListItem
      prependTitleElement={
        view.logo_props?.in_use ? (
          <Logo logo={view.logo_props} size={16} type="lucide" />
        ) : (
          <ViewsIcon className="h-4 w-4 text-tertiary" />
        )
      }
      title={view.name}
      itemLink={`/${workspaceSlug}/workspace-views/${view.id}`}
      actionableItems={
        <>
          <ViewListItemMeta access={view.access} ownerId={view.owned_by} scope={{ projectId: null }} />
          <div className="hidden md:block">
            <WorkspaceViewQuickActions parentRef={parentRef} workspaceSlug={workspaceSlug.toString()} view={view} />
          </div>
        </>
      }
      quickActionElement={
        <div className="block md:hidden">
          <WorkspaceViewQuickActions workspaceSlug={workspaceSlug.toString()} view={view} />
        </div>
      }
      isMobile={isMobile}
      parentRef={parentRef}
    />
  );
});
