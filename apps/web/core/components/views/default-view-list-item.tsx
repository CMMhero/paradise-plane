/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: baris view bawaan (workspace & departemen)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useRef } from "react";
import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { ViewsIcon } from "@plane/propel/icons";
// components
import { ListItem } from "@/components/core/list";
import { DefaultWorkspaceViewQuickActions } from "@/components/workspace/views/default-view-quick-action";
// hooks
import { usePlatformOS } from "@/hooks/use-platform-os";
// lib
import type { TViewBawaan } from "@/lib/view-bawaan";
import { getTautanViewBawaan } from "@/lib/view-bawaan";

type Props = {
  view: TViewBawaan;
  workspaceSlug: string;
  /** Ada = view bawaan departemen ini; tidak ada = view bawaan workspace. */
  projectId?: string;
};

/** All work items / Assigned / Created / Subscribed, dalam bentuk baris yang sama dengan view tersimpan. */
export const DefaultViewListItem = observer(function DefaultViewListItem({ view, workspaceSlug, projectId }: Props) {
  // refs
  const parentRef = useRef(null);
  // hooks
  const { t } = useTranslation();
  const { isMobile } = usePlatformOS();
  // derived values
  const itemLink = getTautanViewBawaan(workspaceSlug, view.key, projectId);
  const quickActions = (
    <DefaultWorkspaceViewQuickActions workspaceSlug={workspaceSlug} view={view} viewLink={itemLink.slice(1)} />
  );

  return (
    <ListItem
      prependTitleElement={<ViewsIcon className="h-4 w-4 text-tertiary" />}
      title={t(view.i18n_label)}
      itemLink={itemLink}
      actionableItems={
        <>
          <span className="rounded-control border border-subtle px-2 py-0.5 text-11 text-secondary">
            {t("views_ui.default_badge")}
          </span>
          <div className="hidden md:block">{quickActions}</div>
        </>
      }
      quickActionElement={<div className="block md:hidden">{quickActions}</div>}
      isMobile={isMobile}
      parentRef={parentRef}
    />
  );
});
