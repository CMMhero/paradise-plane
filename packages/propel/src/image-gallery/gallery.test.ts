/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: galeri gambar (uji logika murni)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vite-plus/test";
import {
  buildGalleryItems,
  canGoNext,
  canGoPrevious,
  clampIndex,
  findTargetIndex,
  getImageGalleryItemProps,
  indexForKey,
  neighbourIndexes,
  readGalleryEntries,
  reconcileIndex,
  sameItemKeys,
  stepIndex,
  swipeDirection,
} from "./gallery";

/** Just enough of an element for readGalleryEntries, no DOM needed. */
const fakeElement = (attrs: Record<string, string>, region: unknown = null) =>
  ({
    getAttribute: (name: string) => attrs[name] ?? null,
    closest: () => region,
    contains: () => false,
  }) as unknown as HTMLElement;

describe("index math", () => {
  it("clamps into the list and treats an empty list as 0", () => {
    expect(clampIndex(-1, 3)).toBe(0);
    expect(clampIndex(5, 3)).toBe(2);
    expect(clampIndex(1, 3)).toBe(1);
    expect(clampIndex(4, 0)).toBe(0);
  });

  it("steps without wrapping around", () => {
    expect(stepIndex(0, 3, -1)).toBe(0);
    expect(stepIndex(2, 3, 1)).toBe(2);
    expect(stepIndex(1, 3, 1)).toBe(2);
    expect(canGoPrevious(0)).toBe(false);
    expect(canGoNext(2, 3)).toBe(false);
    expect(canGoNext(1, 3)).toBe(true);
  });

  it("preloads only neighbours that exist", () => {
    expect(neighbourIndexes(0, 1)).toEqual([]);
    expect(neighbourIndexes(0, 3)).toEqual([1]);
    expect(neighbourIndexes(1, 3)).toEqual([0, 2]);
    expect(neighbourIndexes(2, 3)).toEqual([1]);
  });
});

describe("key handling", () => {
  it("moves with arrows, Home and End", () => {
    expect(indexForKey("ArrowRight", 0, 3)).toBe(1);
    expect(indexForKey("ArrowLeft", 2, 3)).toBe(1);
    expect(indexForKey("Home", 2, 3)).toBe(0);
    expect(indexForKey("End", 0, 3)).toBe(2);
  });

  it("does nothing at the ends, for one image, or for other keys", () => {
    expect(indexForKey("ArrowLeft", 0, 3)).toBeNull();
    expect(indexForKey("ArrowRight", 2, 3)).toBeNull();
    expect(indexForKey("End", 2, 3)).toBeNull();
    expect(indexForKey("ArrowRight", 0, 1)).toBeNull();
    expect(indexForKey("Enter", 0, 3)).toBeNull();
  });
});

describe("swipe", () => {
  it("left swipe = next, right swipe = previous", () => {
    expect(swipeDirection(-80, 5)).toBe(1);
    expect(swipeDirection(80, -5)).toBe(-1);
  });

  it("ignores short or mostly vertical drags", () => {
    expect(swipeDirection(-20, 0)).toBe(0);
    expect(swipeDirection(-60, 80)).toBe(0);
  });
});

describe("list derivation", () => {
  it("keeps DOM order and keys repeated pictures apart", () => {
    const items = buildGalleryItems([{ src: "a" }, { src: "b", downloadSrc: "b-dl" }, { src: "a" }]);
    expect(items.map((i) => i.key)).toEqual(["a", "b", "a#2"]);
    expect(items[0].downloadSrc).toBe("a");
    expect(items[1].downloadSrc).toBe("b-dl");
  });

  it("appends extra images after the page's own, without duplicates", () => {
    const items = buildGalleryItems([{ src: "a" }], [{ src: "a" }, { src: "c", name: "c.png" }, { src: "" }]);
    expect(items.map((i) => i.key)).toEqual(["a", "c"]);
    expect(items[1].name).toBe("c.png");
  });

  it("reads marked elements and skips ignored areas inside the root", () => {
    const draft = {};
    const kept = fakeElement(getImageGalleryItemProps({ src: "a", name: "A" }));
    const ignored = fakeElement(getImageGalleryItemProps({ src: "draft" }), draft);
    const root = {
      querySelectorAll: () => [kept, ignored],
      contains: (node: unknown) => node === draft,
    } as unknown as Element;
    const entries = readGalleryEntries(root);
    expect(entries).toHaveLength(1);
    expect(entries[0]).toMatchObject({ src: "a", downloadSrc: "a", name: "A", element: kept });
  });

  it("reads an ignored area when it is the root itself (a draft's own gallery)", () => {
    const draftRoot = { contains: () => true } as unknown as Element;
    const image = fakeElement(getImageGalleryItemProps({ src: "draft" }), draftRoot);
    Object.assign(draftRoot, { querySelectorAll: () => [image] });
    expect(readGalleryEntries(draftRoot).map((e) => e.src)).toEqual(["draft"]);
  });

  it("finds the opened image by element, by the element around it, or by key", () => {
    const img = fakeElement({});
    const wrapper = { contains: (node: unknown) => node === img } as unknown as Element;
    const items = buildGalleryItems([{ src: "a" }, { src: "b", element: img }], [{ src: "c" }]);
    expect(findTargetIndex(items, img)).toBe(1);
    expect(findTargetIndex(items, wrapper)).toBe(1);
    expect(findTargetIndex(items, "c")).toBe(2);
    expect(findTargetIndex(items, "missing")).toBe(-1);
  });
});

const list = (...keys: string[]) => buildGalleryItems(keys.map((src) => ({ src })));

describe("list changes while open", () => {
  it("stays on the same picture when older images load above it", () => {
    expect(reconcileIndex(list("x", "y", "a", "b"), "a", 0)).toBe(2);
  });

  it("stays put when an image is added after it", () => {
    expect(reconcileIndex(list("a", "b", "new"), "b", 1)).toBe(1);
  });

  it("falls back to the nearest position when the picture is gone", () => {
    expect(reconcileIndex(list("a", "b"), "c", 2)).toBe(1);
    expect(reconcileIndex(list(), "c", 2)).toBe(0);
  });

  it("notices only real changes", () => {
    expect(sameItemKeys(list("a", "b"), list("a", "b"))).toBe(true);
    expect(sameItemKeys(list("a", "b"), list("b", "a"))).toBe(false);
  });
});
