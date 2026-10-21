/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useRef, useState } from "react";
import { observer } from "mobx-react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Logo } from "@plane/propel/emoji-icon-picker";
import { PageIcon } from "@plane/propel/icons";
// plane imports
import type { TPageNavigationTabs } from "@plane/types";
import { getPageName } from "@plane/utils";
// components
import { ListItem } from "@/components/core/list";
import { BlockItemAction } from "@/components/pages/list/block-item-action";
// hooks
import { usePlatformOS } from "@/hooks/use-platform-os";
// plane web hooks
import type { EPageStoreType } from "@/hooks/store";
import { usePage, usePageStore } from "@/hooks/store";

/** lebar satu tingkat indentasi, px */
const INDENT_STEP = 24;

type TPageListBlock = {
  pageId: string;
  storeType: EPageStoreType;
  pageType: TPageNavigationTabs;
  depth?: number;
};

export const PageListBlock = observer(function PageListBlock(props: TPageListBlock) {
  const { pageId, storeType, pageType, depth = 0 } = props;
  // refs
  const parentRef = useRef(null);
  // states
  const [isExpanded, setIsExpanded] = useState(true);
  // hooks
  const page = usePage({
    pageId,
    storeType,
  });
  const { getSubPageIds } = usePageStore(storeType);
  const { isMobile } = usePlatformOS();
  // handle page check
  if (!page) return null;
  // derived values
  const { name, logo_props, getRedirectionLink } = page;
  const subPageIds = getSubPageIds(pageId, pageType);
  const hasSubPages = subPageIds.length > 0;

  return (
    <>
      <div style={depth > 0 ? { paddingLeft: depth * INDENT_STEP } : undefined}>
        <ListItem
          prependTitleElement={
            <span className="flex items-center gap-1">
              {hasSubPages ? (
                <button
                  type="button"
                  // chevron ini berada DI DALAM anchor-nya ListItem, jadi tanpa
                  // kedua penahan ini mengklik panah akan ikut membuka halaman
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setIsExpanded((prev) => !prev);
                  }}
                  className="grid size-4 flex-shrink-0 place-items-center rounded text-tertiary hover:bg-layer-3-hover hover:text-secondary"
                  aria-expanded={isExpanded}
                  aria-label={
                    isExpanded ? `Tutup sub-halaman ${getPageName(name)}` : `Buka sub-halaman ${getPageName(name)}`
                  }
                >
                  {isExpanded ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
                </button>
              ) : (
                // penjaga perataan: tanpa ini judul halaman tanpa anak bergeser
                // kiri dan pohonnya terlihat patah
                <span className="size-4 flex-shrink-0" aria-hidden="true" />
              )}
              {logo_props?.in_use ? (
                <Logo logo={logo_props} size={16} type="lucide" />
              ) : (
                <PageIcon className="h-4 w-4 text-tertiary" />
              )}
            </span>
          }
          title={getPageName(name)}
          itemLink={getRedirectionLink()}
          actionableItems={<BlockItemAction page={page} parentRef={parentRef} storeType={storeType} />}
          isMobile={isMobile}
          parentRef={parentRef}
        />
      </div>
      {hasSubPages &&
        isExpanded &&
        subPageIds.map((subPageId) => (
          <PageListBlock
            key={subPageId}
            pageId={subPageId}
            storeType={storeType}
            pageType={pageType}
            depth={depth + 1}
          />
        ))}
    </>
  );
});
