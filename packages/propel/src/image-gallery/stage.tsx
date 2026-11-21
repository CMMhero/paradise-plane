/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: galeri gambar (zoom & geser satu gambar)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Download, ImageOff, Minus, Plus, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type React from "react";
import { NewTabIcon } from "../icons/actions/new-tab-icon";
import { cn } from "../utils/classname";
import type { TImageGalleryItem } from "./gallery";
import { swipeDirection } from "./gallery";
import type { TImageGalleryLabels } from "./labels";

const MIN_ZOOM = 0.5;
const MAX_ZOOM = 4;
const ZOOM_STEPS = [0.5, 0.75, 1, 1.5, 2, 3, 4];
const WHEEL_ZOOM_SPEED = 0.0015;
const DOUBLE_TAP_ZOOM = 2;
/** pointer travel (px) below which a press still counts as a click/tap */
const CLICK_SLOP = 6;

type Point = { x: number; y: number };

const clampZoom = (value: number) => Math.min(Math.max(value, MIN_ZOOM), MAX_ZOOM);

const distance = (a: Point, b: Point) => Math.hypot(a.x - b.x, a.y - b.y);

type Props = {
  item: TImageGalleryItem;
  alt: string;
  failed: boolean;
  isTouchDevice: boolean;
  labels: TImageGalleryLabels;
  /** aspect ratio once known (from this load or an earlier preload) */
  aspectRatio: number | undefined;
  onClose: () => void;
  onError: () => void;
  onLoad: (aspectRatio: number) => void;
  onSwipe: (direction: -1 | 1) => void;
};

/**
 * One image with its zoom and pan. The viewer mounts a new stage per image
 * (keyed by the image), so moving to another image always starts at 100%.
 *
 * Zoom works with the toolbar buttons, the keyboard (+, -, 0), the mouse wheel
 * or trackpad pinch, a two-finger pinch on touch screens, and a double click or
 * double tap. `touch-action: none` keeps the browser from zooming the whole
 * page instead, which used to leave phones stuck in a zoomed-in layout. At 100%
 * a sideways swipe moves to the next or previous image.
 */
export function ImageGalleryStage(props: Props) {
  const { item, alt, failed, isTouchDevice, labels, aspectRatio, onClose, onError, onLoad, onSwipe } = props;
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState<Point>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const pointers = useRef(new Map<number, Point>());
  const gesture = useRef<{
    startOffset: Point;
    startPoint: Point;
    startZoom: number;
    startDistance: number;
    moved: boolean;
    /** pointer capture retargets pointerup, so remember where the press began */
    startedOnImage: boolean;
    multiTouch: boolean;
  } | null>(null);
  const lastTap = useRef(0);
  // wheel events arrive faster than renders: each one has to build on the last
  const zoomRef = useRef(1);

  const applyZoom = useCallback((next: number) => {
    const clamped = clampZoom(next);
    zoomRef.current = clamped;
    setZoom(clamped);
    // back at (or below) the fitted size there is nothing to pan to
    if (clamped <= 1) setOffset({ x: 0, y: 0 });
  }, []);

  const resetView = useCallback(() => applyZoom(1), [applyZoom]);

  const stepZoom = useCallback(
    (direction: "increase" | "decrease") => {
      const prev = zoomRef.current;
      applyZoom(
        direction === "increase"
          ? (ZOOM_STEPS.find((step) => step > prev + 0.001) ?? MAX_ZOOM)
          : (ZOOM_STEPS.findLast((step) => step < prev - 0.001) ?? MIN_ZOOM)
      );
    },
    [applyZoom]
  );

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!["+", "=", "-", "0"].includes(e.key) || e.ctrlKey || e.metaKey) return;
      e.preventDefault();
      e.stopPropagation();
      if (e.key === "+" || e.key === "=") stepZoom("increase");
      else if (e.key === "-") stepZoom("decrease");
      else resetView();
    };

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      // trackpad pinch arrives as ctrl+wheel with small deltas; plain wheel
      // zooms too, there is nothing to scroll inside the viewer
      const factor = Math.exp(-e.deltaY * WHEEL_ZOOM_SPEED * (e.ctrlKey ? 4 : 1));
      applyZoom(zoomRef.current * factor);
    };

    document.addEventListener("keydown", handleKeyDown, true);
    window.addEventListener("wheel", handleWheel, { passive: false });
    return () => {
      document.removeEventListener("keydown", handleKeyDown, true);
      window.removeEventListener("wheel", handleWheel);
    };
  }, [stepZoom, resetView, applyZoom]);

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest("button")) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const points = [...pointers.current.values()];
    const previous = gesture.current;
    gesture.current = {
      startOffset: offset,
      startPoint:
        points.length === 1 ? points[0] : { x: (points[0].x + points[1].x) / 2, y: (points[0].y + points[1].y) / 2 },
      startZoom: zoom,
      startDistance: points.length >= 2 ? distance(points[0], points[1]) : 0,
      moved: points.length === 1 ? false : (previous?.moved ?? false),
      startedOnImage: (e.target as HTMLElement).tagName === "IMG",
      multiTouch: points.length >= 2 || (previous?.multiTouch ?? false),
    };
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!pointers.current.has(e.pointerId) || !gesture.current) return;
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const points = [...pointers.current.values()];
    const g = gesture.current;

    if (points.length >= 2 && g.startDistance > 0) {
      g.moved = true;
      setIsPanning(true);
      applyZoom(g.startZoom * (distance(points[0], points[1]) / g.startDistance));
      return;
    }

    const dx = points[0].x - g.startPoint.x;
    const dy = points[0].y - g.startPoint.y;
    if (Math.abs(dx) > CLICK_SLOP || Math.abs(dy) > CLICK_SLOP) g.moved = true;
    if (g.moved && zoom > 1) {
      setIsPanning(true);
      setOffset({ x: g.startOffset.x + dx, y: g.startOffset.y + dy });
    }
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!pointers.current.has(e.pointerId)) return;
    pointers.current.delete(e.pointerId);
    const g = gesture.current;
    setIsPanning(false);

    if (pointers.current.size > 0) {
      // one finger lifted out of a pinch: continue as a pan from here
      const remaining = [...pointers.current.values()][0];
      gesture.current = {
        startOffset: offset,
        startPoint: remaining,
        startZoom: zoom,
        startDistance: 0,
        moved: true,
        startedOnImage: false,
        multiTouch: true,
      };
      return;
    }
    gesture.current = null;
    if (!g || e.type === "pointercancel") return;

    if (g.moved) {
      // a one-finger drag at the fitted size has nothing to pan, so it browses
      if (zoom <= 1 && !g.multiTouch) {
        const direction = swipeDirection(e.clientX - g.startPoint.x, e.clientY - g.startPoint.y);
        if (direction !== 0) onSwipe(direction);
      }
      return;
    }

    const isOnImage = g.startedOnImage;
    const now = Date.now();
    if (isOnImage && now - lastTap.current < 300) {
      // double click / double tap toggles between fitted and zoomed in
      lastTap.current = 0;
      if (zoom > 1) resetView();
      else applyZoom(DOUBLE_TAP_ZOOM);
      return;
    }
    lastTap.current = isOnImage ? now : 0;
    // a plain click or tap on the dark backdrop closes the viewer
    if (!isOnImage) onClose();
  };

  const controlButtonClassName =
    "grid size-11 flex-shrink-0 place-items-center rounded-md text-white/80 transition-colors duration-200 hover:bg-white/10 hover:text-white focus-visible:outline-2 focus-visible:outline-white disabled:text-white/30 disabled:hover:bg-transparent motion-reduce:transition-none sm:size-9";

  return (
    <>
      <div
        className={cn("relative grid size-full touch-none place-items-center overflow-hidden select-none", {
          "cursor-grab": zoom > 1 && !isPanning,
          "cursor-grabbing": isPanning,
        })}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
      >
        {failed ? (
          <div
            role="alert"
            className="flex max-w-[80vw] flex-col items-center gap-3 rounded-lg bg-black/70 px-6 py-5 text-center text-white ring-1 ring-white/20"
          >
            <ImageOff className="size-8 text-white/70" aria-hidden />
            <p className="text-14">{labels.loadError}</p>
          </div>
        ) : (
          <img
            src={item.src}
            alt={alt}
            draggable={false}
            onLoad={(e) => {
              const { naturalWidth, naturalHeight } = e.currentTarget;
              if (naturalWidth && naturalHeight) onLoad(naturalWidth / naturalHeight);
            }}
            onError={onError}
            className={cn(
              "read-only-image cursor-default rounded-lg transition-[transform,opacity] duration-150 ease-out motion-reduce:transition-none",
              { "transition-none": isPanning, "opacity-0": !aspectRatio }
            )}
            style={{
              // fill 90% of the width or 75% of the height, whichever is hit first
              width: aspectRatio ? `min(90vw, calc(75vh * ${aspectRatio}))` : undefined,
              maxWidth: aspectRatio ? "none" : "90vw",
              maxHeight: aspectRatio ? "none" : "75vh",
              aspectRatio,
              transform: `translate3d(${offset.x}px, ${offset.y}px, 0) scale(${zoom})`,
              transformOrigin: "center",
            }}
          />
        )}
      </div>

      <div className="absolute bottom-[max(1.5rem,env(safe-area-inset-bottom))] left-1/2 flex -translate-x-1/2 items-center gap-1 rounded-lg bg-black/80 p-1 ring-1 ring-white/20">
        <button
          type="button"
          onClick={() => stepZoom("decrease")}
          className={controlButtonClassName}
          disabled={failed || zoom <= MIN_ZOOM}
          aria-label={labels.zoomOut}
          title={`${labels.zoomOut} (-)`}
        >
          <Minus className="size-4" />
        </button>
        <span className="w-12 text-center text-13 text-white tabular-nums" aria-hidden>
          {Math.round(100 * zoom)}%
        </span>
        <button
          type="button"
          onClick={() => stepZoom("increase")}
          className={controlButtonClassName}
          disabled={failed || zoom >= MAX_ZOOM}
          aria-label={labels.zoomIn}
          title={`${labels.zoomIn} (+)`}
        >
          <Plus className="size-4" />
        </button>
        <button
          type="button"
          onClick={resetView}
          className={controlButtonClassName}
          disabled={zoom === 1 && offset.x === 0 && offset.y === 0}
          aria-label={labels.resetZoom}
          title={`${labels.resetZoom} (0)`}
        >
          <RotateCcw className="size-4" />
        </button>
        {!isTouchDevice && (
          <>
            <button
              type="button"
              onClick={() => window.open(item.downloadSrc, "_blank", "noopener,noreferrer")}
              className={controlButtonClassName}
              aria-label={labels.download}
              title={labels.download}
            >
              <Download className="size-4" />
            </button>
            <button
              type="button"
              onClick={() => window.open(item.src, "_blank", "noopener,noreferrer")}
              className={controlButtonClassName}
              aria-label={labels.openInNewTab}
              title={labels.openInNewTab}
            >
              <NewTabIcon className="size-4" />
            </button>
          </>
        )}
      </div>
    </>
  );
}
