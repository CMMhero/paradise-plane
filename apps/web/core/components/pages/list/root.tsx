/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// types
import type { TPageNavigationTabs } from "@plane/types";
// components
import { ListLayout } from "@/components/core/list";
// plane web hooks
import type { EPageStoreType } from "@/hooks/store";
import { usePageStore } from "@/hooks/store";
// local imports
import { PageListBlock } from "./block";

type TPagesListRoot = {
  pageType: TPageNavigationTabs;
  storeType: EPageStoreType;
};

export const PagesListRoot = observer(function PagesListRoot(props: TPagesListRoot) {
  const { pageType, storeType } = props;
  // store hooks
  const { getCurrentProjectRootPageIdsByTab } = usePageStore(storeType);
  // derived values
  // hanya akar yang dirender di sini; tiap blok merender anaknya sendiri
  const rootPageIds = getCurrentProjectRootPageIdsByTab(pageType);

  if (!rootPageIds) return <></>;
  return (
    <ListLayout>
      {rootPageIds.map((pageId) => (
        <PageListBlock key={pageId} pageId={pageId} storeType={storeType} pageType={pageType} />
      ))}
    </ListLayout>
  );
});
