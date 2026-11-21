/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: galeri gambar (penampil layar penuh)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useCloseOnBack } from "@plane/hooks";
import { CloseIcon } from "../icons/actions/close-icon";
import type { TImageGalleryItem } from "./gallery";
import { canGoNext, canGoPrevious, indexForKey, neighbourIndexes, stepIndex } from "./gallery";
import type { TImageGalleryLabels } from "./labels";
import { ImageGalleryStage } from "./stage";

export type TImageGalleryViewerProps = {
  items: TImageGalleryItem[];
  index: number;
  labels: TImageGalleryLabels;
  onIndexChange: (index: number) => void;
  onClose: () => void;
  /** gets focus back when the viewer closes (the button that opened it) */
  returnFocusTo?: HTMLElement | null;
};

const FOCUSABLE = "button:not([disabled]), [href], [tabindex]:not([tabindex='-1'])";

const isCoarsePointer = () => typeof window !== "undefined" && window.matchMedia("(pointer: coarse)").matches;

/**
 * Full-screen image viewer that browses a list of images. Every exit is
 * available at once, because users try them in different orders and any one
 * of them failing felt like being stuck: the close button (top right, high
 * contrast), Escape, a click/tap on the dark backdrop, and the browser or
 * Android Back button (`useCloseOnBack`).
 *
 * Browsing: the arrow buttons at the sides, ArrowLeft/ArrowRight, Home/End and
 * a sideways swipe. The ends do not wrap, so "last image" is never mistaken
 * for "back at the start".
 */
function ImageGalleryViewerWithoutPortal(props: TImageGalleryViewerProps) {
  const { items, index, labels, onIndexChange, onClose, returnFocusTo } = props;
  const [failedKeys, setFailedKeys] = useState<ReadonlySet<string>>(() => new Set());
  const [aspectRatios, setAspectRatios] = useState<ReadonlyMap<string, number>>(() => new Map());
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const [isTouchDevice] = useState(isCoarsePointer);
  // the opener does not change while the viewer is open
  const returnFocusRef = useRef(returnFocusTo);

  const total = items.length;
  const current = items[index];
  const hasMany = total > 1;

  const go = useCallback(
    (delta: number) => {
      const next = stepIndex(index, total, delta);
      if (next !== index) onIndexChange(next);
    },
    [index, total, onIndexChange]
  );

  const rememberAspectRatio = useCallback((key: string, ratio: number) => {
    setAspectRatios((prev) => (prev.get(key) === ratio ? prev : new Map(prev).set(key, ratio)));
  }, []);

  // browser / Android Back closes the viewer instead of leaving the page
  useCloseOnBack(true, onClose);

  // keyboard, scroll lock, focus in and focus back out
  useEffect(() => {
    const opener = returnFocusRef.current;
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeButtonRef.current?.focus({ preventScroll: true });

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflow;
      const target = opener?.isConnected ? opener : previouslyFocused;
      target?.focus({ preventScroll: true });
    };
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        // the viewer sits on top of peeks and modals: Escape must close only us
        e.preventDefault();
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key === "Tab") {
        // keep focus inside the dialog
        const focusables = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? []);
        if (focusables.length === 0) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        const active = document.activeElement;
        const inside = !!active && !!dialogRef.current?.contains(active);
        if (!inside || (e.shiftKey && active === first) || (!e.shiftKey && active === last)) {
          e.preventDefault();
          (e.shiftKey ? last : first).focus();
        }
        return;
      }
      if (e.altKey || e.ctrlKey || e.metaKey) return;
      const next = indexForKey(e.key, index, total);
      if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) {
        e.preventDefault();
        e.stopPropagation();
      }
      if (next !== null) onIndexChange(next);
    };
    document.addEventListener("keydown", handleKeyDown, true);
    return () => document.removeEventListener("keydown", handleKeyDown, true);
  }, [index, total, onClose, onIndexChange]);

  // warm the cache for the neighbours, so moving on shows the image at once
  useEffect(() => {
    const preloaders = neighbourIndexes(index, total).map((i) => {
      const item = items[i];
      const image = new Image();
      const handleLoad = () => {
        if (image.naturalWidth && image.naturalHeight)
          rememberAspectRatio(item.key, image.naturalWidth / image.naturalHeight);
      };
      image.addEventListener("load", handleLoad);
      image.src = item.src;
      return { image, handleLoad };
    });
    return () => {
      for (const { image, handleLoad } of preloaders) image.removeEventListener("load", handleLoad);
    };
  }, [index, total, items, rememberAspectRatio]);

  if (!current) return null;

  const counter = labels.counter(index + 1, total);
  const navButtonClassName =
    "absolute top-1/2 z-10 grid size-12 -translate-y-1/2 place-items-center rounded-full bg-black/70 text-white ring-1 ring-white/30 transition-colors hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-white disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:bg-black/70 motion-reduce:transition-none sm:size-11";

  return (
    <div
      ref={dialogRef}
      className="editor-image-full-screen-modal fixed inset-0 z-[200] size-full bg-black/90"
      // oxlint-disable-next-line jsx-a11y/prefer-tag-over-role -- a modal <dialog> lives in the top layer, above the toasts and outside #editor-portal
      role="dialog"
      aria-modal="true"
      aria-label={labels.dialog}
      // keeps the peek overview underneath open: a click in the viewer is not
      // an "outside click" for it (use-peek-overview-outside-click)
      data-prevent-outside-click
    >
      <ImageGalleryStage
        key={current.key}
        item={current}
        alt={current.name || counter}
        failed={failedKeys.has(current.key)}
        isTouchDevice={isTouchDevice}
        labels={labels}
        aspectRatio={aspectRatios.get(current.key)}
        onClose={onClose}
        onError={() => setFailedKeys((prev) => new Set(prev).add(current.key))}
        onLoad={(ratio) => rememberAspectRatio(current.key, ratio)}
        onSwipe={go}
      />

      {/* the visible "3 / 12" is compact; screen readers get the full sentence */}
      <p className="sr-only" aria-live="polite" aria-atomic="true">
        {hasMany ? counter : ""}
      </p>
      {hasMany && (
        <div
          aria-hidden
          className="absolute top-[max(1rem,env(safe-area-inset-top))] left-[max(1rem,env(safe-area-inset-left))] rounded-full bg-black/70 px-3 py-1.5 text-13 text-white tabular-nums ring-1 ring-white/30"
        >
          {index + 1} / {total}
        </div>
      )}

      {hasMany && (
        <>
          <button
            type="button"
            onClick={() => go(-1)}
            disabled={!canGoPrevious(index)}
            className={`${navButtonClassName} left-[max(0.5rem,env(safe-area-inset-left))]`}
            aria-label={labels.previous}
            title={`${labels.previous} (←)`}
          >
            <ChevronLeft className="size-6" />
          </button>
          <button
            type="button"
            onClick={() => go(1)}
            disabled={!canGoNext(index, total)}
            className={`${navButtonClassName} right-[max(0.5rem,env(safe-area-inset-right))]`}
            aria-label={labels.next}
            title={`${labels.next} (→)`}
          >
            <ChevronRight className="size-6" />
          </button>
        </>
      )}

      <button
        ref={closeButtonRef}
        type="button"
        onClick={onClose}
        className="absolute top-[max(1rem,env(safe-area-inset-top))] right-[max(1rem,env(safe-area-inset-right))] grid size-11 place-items-center rounded-full bg-black/70 text-white ring-1 ring-white/30 transition-colors hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-white motion-reduce:transition-none"
        aria-label={labels.close}
        title={`${labels.close} (Esc)`}
      >
        <CloseIcon className="size-6" />
      </button>
    </div>
  );
}

export function ImageGalleryViewer(props: TImageGalleryViewerProps) {
  if (typeof document === "undefined") return null;
  // #editor-portal sits outside the app tree, so headless UI dialogs treat it as
  // a root container (clicks inside do not close them) and never mark it inert
  const portal = document.querySelector("#editor-portal") ?? document.body;
  return createPortal(<ImageGalleryViewerWithoutPortal {...props} />, portal);
}
