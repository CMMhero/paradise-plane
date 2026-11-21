/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: galeri gambar (logika murni)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** One image the viewer can show. `key` stays the same across re-renders. */
export type TImageGalleryItem = {
  key: string;
  src: string;
  downloadSrc: string;
  name?: string;
};

/** An image found in the page or handed over from a store, before keys are assigned. */
export type TImageGalleryEntry = {
  src: string;
  downloadSrc?: string;
  name?: string;
  /** the DOM node that carries the data attributes, used to find the opened image */
  element?: Element;
};

export type TImageGalleryCollectedItem = TImageGalleryItem & { element?: Element };

export const GALLERY_ATTRIBUTE = {
  src: "data-image-gallery-src",
  downloadSrc: "data-image-gallery-download",
  name: "data-image-gallery-name",
  ignore: "data-image-gallery-ignore",
} as const;

/** px a finger has to travel sideways before a drag counts as a swipe */
export const SWIPE_THRESHOLD = 50;

/**
 * Data attributes that make an element part of the gallery of the scope it is
 * rendered in. Spread them on the `<img>` (or a wrapper around it).
 */
export const getImageGalleryItemProps = (item: { src: string; downloadSrc?: string; name?: string }) => ({
  [GALLERY_ATTRIBUTE.src]: item.src,
  [GALLERY_ATTRIBUTE.downloadSrc]: item.downloadSrc ?? item.src,
  ...(item.name ? { [GALLERY_ATTRIBUTE.name]: item.name } : {}),
});

/**
 * Assigns stable keys and drops duplicates. DOM entries keep their order (the
 * reading order); the same picture twice in one text stays two stops, keyed
 * `src`, `src#2`, ... Extra entries (from a store) are appended unless their
 * picture is already on the page.
 */
export const buildGalleryItems = (
  domEntries: TImageGalleryEntry[],
  extraEntries: TImageGalleryEntry[] = []
): TImageGalleryCollectedItem[] => {
  const seen = new Map<string, number>();
  const items: TImageGalleryCollectedItem[] = [];
  for (const entry of domEntries) {
    if (!entry.src) continue;
    const count = (seen.get(entry.src) ?? 0) + 1;
    seen.set(entry.src, count);
    items.push({
      key: count === 1 ? entry.src : `${entry.src}#${count}`,
      src: entry.src,
      downloadSrc: entry.downloadSrc || entry.src,
      name: entry.name,
      element: entry.element,
    });
  }
  for (const entry of extraEntries) {
    if (!entry.src || seen.has(entry.src)) continue;
    seen.set(entry.src, 1);
    items.push({ key: entry.src, src: entry.src, downloadSrc: entry.downloadSrc || entry.src, name: entry.name });
  }
  return items;
};

/**
 * Reads every gallery image inside `root`, in DOM order. Images inside an
 * ignored region (a comment draft) are skipped, unless `root` is that region.
 */
export const readGalleryEntries = (root: Element): TImageGalleryEntry[] =>
  Array.from(root.querySelectorAll<HTMLElement>(`[${GALLERY_ATTRIBUTE.src}]`))
    .filter((element) => {
      const region = element.closest(`[${GALLERY_ATTRIBUTE.ignore}]`);
      return !region || region === root || !root.contains(region);
    })
    .map((element) => ({
      src: element.getAttribute(GALLERY_ATTRIBUTE.src) ?? "",
      downloadSrc: element.getAttribute(GALLERY_ATTRIBUTE.downloadSrc) ?? undefined,
      name: element.getAttribute(GALLERY_ATTRIBUTE.name) ?? undefined,
      element,
    }));

/** Page images inside `root` followed by the extra ones; nothing from the page when there is no root yet. */
export const collectGalleryItems = (
  root: Element | null,
  extraEntries: TImageGalleryEntry[] = []
): TImageGalleryCollectedItem[] => buildGalleryItems(root ? readGalleryEntries(root) : [], extraEntries);

/** The ignored region (a draft) the target sits in, which then is a gallery of its own. */
export const findIgnoredRegion = (target: Element | string): Element | null =>
  typeof target === "string" ? null : target.closest(`[${GALLERY_ATTRIBUTE.ignore}]`);

/**
 * Index of the image the user opened. `target` is the image element itself,
 * an element around it (a button, the image block), or a key / src string.
 */
export const findTargetIndex = (items: TImageGalleryCollectedItem[], target: Element | string): number => {
  if (typeof target === "string") {
    const byKey = items.findIndex((item) => item.key === target);
    return byKey >= 0 ? byKey : items.findIndex((item) => item.src === target);
  }
  return items.findIndex((item) => !!item.element && (item.element === target || target.contains(item.element)));
};

export const clampIndex = (index: number, total: number): number => {
  if (total <= 0) return 0;
  return Math.min(Math.max(index, 0), total - 1);
};

/** Next / previous without wrapping around: the ends are ends. */
export const stepIndex = (index: number, total: number, delta: number): number => clampIndex(index + delta, total);

export const canGoPrevious = (index: number): boolean => index > 0;

export const canGoNext = (index: number, total: number): boolean => index < total - 1;

/** New index for a navigation key, or null when the key is not ours or changes nothing. */
export const indexForKey = (key: string, index: number, total: number): number | null => {
  if (total <= 1) return null;
  let next: number;
  switch (key) {
    case "ArrowLeft":
      next = stepIndex(index, total, -1);
      break;
    case "ArrowRight":
      next = stepIndex(index, total, 1);
      break;
    case "Home":
      next = 0;
      break;
    case "End":
      next = total - 1;
      break;
    default:
      return null;
  }
  return next === index ? null : next;
};

/** Images worth preloading around the current one. */
export const neighbourIndexes = (index: number, total: number): number[] =>
  [index - 1, index + 1].filter((i) => i >= 0 && i < total);

/**
 * Where the viewer should be after the list changed underneath it (an image
 * added, older chat messages loaded above, an image removed). Stays on the
 * same picture when it still exists, otherwise on the nearest position.
 */
export const reconcileIndex = (items: TImageGalleryItem[], currentKey: string, previousIndex: number): number => {
  const sameImage = items.findIndex((item) => item.key === currentKey);
  return sameImage >= 0 ? sameImage : clampIndex(previousIndex, items.length);
};

export const sameItemKeys = (a: TImageGalleryItem[], b: TImageGalleryItem[]): boolean =>
  a.length === b.length && a.every((item, i) => item.key === b[i].key && item.src === b[i].src);

/** -1 = previous, 1 = next, 0 = not a swipe (too short, or mostly vertical). */
export const swipeDirection = (dx: number, dy: number, threshold = SWIPE_THRESHOLD): -1 | 0 | 1 => {
  if (Math.abs(dx) < threshold || Math.abs(dx) < Math.abs(dy) * 1.5) return 0;
  // finger moving left brings the next image in from the right
  return dx < 0 ? 1 : -1;
};
