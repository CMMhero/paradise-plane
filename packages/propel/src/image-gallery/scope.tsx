/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: galeri gambar (cakupan)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode, RefObject } from "react";
import type { TImageGalleryCollectedItem, TImageGalleryEntry } from "./gallery";
import {
  GALLERY_ATTRIBUTE,
  collectGalleryItems,
  findIgnoredRegion,
  findTargetIndex,
  reconcileIndex,
  sameItemKeys,
} from "./gallery";
import type { TImageGalleryLabels } from "./labels";
import { DEFAULT_IMAGE_GALLERY_LABELS } from "./labels";
import { ImageGalleryViewer } from "./viewer";

export type TImageGalleryApi = {
  /**
   * Opens the viewer on `target`: the image element, an element around it,
   * or a key / src (for images that are not on the page, like attachments).
   * Returns false when the target is not part of this gallery.
   */
  open: (target: Element | string, returnFocusTo?: HTMLElement | null) => boolean;
};

const LabelsContext = createContext<TImageGalleryLabels>(DEFAULT_IMAGE_GALLERY_LABELS);
const ScopeContext = createContext<TImageGalleryApi | null>(null);

/** The gallery of the closest scope, or null outside any scope. */
export const useImageGallery = (): TImageGalleryApi | null => useContext(ScopeContext);

type TProviderProps = { labels: TImageGalleryLabels; children: ReactNode };

/** App-wide translated texts. Without it the viewer speaks English. */
export function ImageGalleryProvider({ labels, children }: TProviderProps) {
  return <LabelsContext.Provider value={labels}>{children}</LabelsContext.Provider>;
}

export type TImageGalleryScopeProps = {
  /** the element whose images make up this gallery, in DOM (reading) order */
  rootRef: RefObject<HTMLElement | null>;
  /** images that are not on the page (or not always), appended after the page's own */
  extraItems?: TImageGalleryEntry[];
  /** closes the viewer when it changes (another work item, another conversation) */
  resetKey?: string | null;
  /** use the enclosing scope when there is one: for editors, which are often part of a larger page */
  inherit?: boolean;
  children: ReactNode;
};

type TOpenState = {
  items: TImageGalleryCollectedItem[];
  index: number;
  returnFocusTo: HTMLElement | null;
  /** set when the image sits in an ignored region (a draft): that region is the whole gallery */
  region: Element | null;
};

function OwnImageGalleryScope(props: TImageGalleryScopeProps) {
  const { rootRef, extraItems, resetKey, children } = props;
  const labels = useContext(LabelsContext);
  const [state, setState] = useState<TOpenState | null>(null);
  const [lastResetKey, setLastResetKey] = useState(resetKey);
  const extraItemsRef = useRef(extraItems);

  // another work item or conversation in the same component: the open viewer
  // belonged to the old one, and coming back must not reopen it
  if (lastResetKey !== resetKey) {
    setLastResetKey(resetKey);
    setState(null);
  }

  useEffect(() => {
    extraItemsRef.current = extraItems;
  }, [extraItems]);

  const open = useCallback<TImageGalleryApi["open"]>(
    (target, returnFocusTo) => {
      const region = findIgnoredRegion(target);
      const items = collectGalleryItems(region ?? rootRef.current, region ? [] : extraItemsRef.current);
      const index = findTargetIndex(items, target);
      if (index < 0) return false;
      const opener = returnFocusTo ?? (document.activeElement instanceof HTMLElement ? document.activeElement : null);
      setState({ items, index, returnFocusTo: opener, region });
      return true;
    },
    [rootRef]
  );

  const isOpen = !!state;
  const region = state?.region ?? null;

  // Images appear and disappear while the viewer is open (lazy rendering,
  // someone editing the description, a new comment, older chat messages
  // loading above). Re-read the list and stay on the same picture.
  useEffect(() => {
    if (!isOpen) return;
    const root = region ?? rootRef.current;
    if (!root) return;
    const refresh = () => {
      const items = collectGalleryItems(root, region ? [] : extraItems);
      setState((prev) => {
        if (!prev) return prev;
        if (items.length === 0) return null;
        if (sameItemKeys(prev.items, items)) return prev;
        const currentKey = prev.items[prev.index]?.key ?? "";
        return { ...prev, items, index: reconcileIndex(items, currentKey, prev.index) };
      });
    };
    const observer = new MutationObserver(refresh);
    observer.observe(root, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: [GALLERY_ATTRIBUTE.src],
    });
    // the extra items may have changed since the viewer opened
    refresh();
    return () => observer.disconnect();
  }, [isOpen, region, rootRef, extraItems]);

  const close = useCallback(() => setState(null), []);
  const changeIndex = useCallback((index: number) => setState((prev) => (prev ? { ...prev, index } : prev)), []);
  const api = useMemo<TImageGalleryApi>(() => ({ open }), [open]);

  return (
    <ScopeContext.Provider value={api}>
      {children}
      {state && (
        <ImageGalleryViewer
          items={state.items}
          index={state.index}
          labels={labels}
          onIndexChange={changeIndex}
          onClose={close}
          returnFocusTo={state.returnFocusTo}
        />
      )}
    </ScopeContext.Provider>
  );
}

/**
 * One gallery: every image inside `rootRef` (marked with
 * `getImageGalleryItemProps`) plus `extraItems`. Opening any of them lets the
 * user browse the rest. Scopes do not leak into each other: an inner scope
 * hides the outer one unless it is `inherit`.
 */
export function ImageGalleryScope(props: TImageGalleryScopeProps) {
  const parent = useContext(ScopeContext);
  if (props.inherit && parent) return <>{props.children}</>;
  return <OwnImageGalleryScope {...props} />;
}
