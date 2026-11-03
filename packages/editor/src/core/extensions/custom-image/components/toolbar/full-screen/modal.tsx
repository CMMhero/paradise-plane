/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: lightbox gambar yang selalu bisa ditutup
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Download, Minus, RotateCcw } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactDOM from "react-dom";
import { useCloseOnBack } from "@plane/hooks";
import { NewTabIcon, PlusIcon, CloseIcon } from "@plane/propel/icons";
// plane imports
import { cn } from "@plane/utils";

const MIN_ZOOM = 0.5;
const MAX_ZOOM = 4;
const ZOOM_STEPS = [0.5, 0.75, 1, 1.5, 2, 3, 4];
const WHEEL_ZOOM_SPEED = 0.0015;
const DOUBLE_TAP_ZOOM = 2;
/** pointer travel (px) below which a press still counts as a click/tap */
const CLICK_SLOP = 6;

type Point = { x: number; y: number };

type Props = {
  aspectRatio: number;
  downloadSrc: string;
  isFullScreenEnabled: boolean;
  isTouchDevice: boolean;
  src: string;
  toggleFullScreenMode: (val: boolean) => void;
  width: string;
};

const clampZoom = (value: number) => Math.min(Math.max(value, MIN_ZOOM), MAX_ZOOM);

const distance = (a: Point, b: Point) => Math.hypot(a.x - b.x, a.y - b.y);

/**
 * Full-screen image viewer. Every exit is available at once, because users try
 * them in different orders and any one of them failing felt like being stuck:
 * the close button (top right, high contrast), Escape, a click/tap on the dark
 * backdrop, and the browser or Android Back button (`useCloseOnBack`).
 *
 * Zoom works with the toolbar buttons, the keyboard (+, -, 0), the mouse wheel
 * or trackpad pinch, a two-finger pinch on touch screens, and a double click or
 * double tap. `touch-action: none` keeps the browser from zooming the whole
 * page instead, which used to leave phones stuck in a zoomed-in layout.
 */
function ImageFullScreenModalWithoutPortal(props: Props) {
  const { aspectRatio, isFullScreenEnabled, isTouchDevice, downloadSrc, src, toggleFullScreenMode, width } = props;
  // states
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState<Point>({ x: 0, y: 0 });
  const [fitScale, setFitScale] = useState(1);
  const [isPanning, setIsPanning] = useState(false);
  // refs
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const pointers = useRef(new Map<number, Point>());
  const gesture = useRef<{
    startOffset: Point;
    startPoint: Point;
    startZoom: number;
    startDistance: number;
    moved: boolean;
    /** pointer capture retargets pointerup, so remember where the press began */
    startedOnImage: boolean;
  } | null>(null);
  const lastTap = useRef(0);

  const widthInNumber = useMemo(() => {
    if (!width) return 0;
    return Number(width.replace("px", "")) || 0;
  }, [width]);

  const resetView = useCallback(() => {
    setZoom(1);
    setOffset({ x: 0, y: 0 });
  }, []);

  const handleClose = useCallback(() => {
    toggleFullScreenMode(false);
    resetView();
  }, [resetView, toggleFullScreenMode]);

  // browser / Android Back closes the viewer instead of leaving the page
  useCloseOnBack(isFullScreenEnabled, handleClose);

  // fit the image into the viewport, recomputed on resize/rotation
  useEffect(() => {
    if (!isFullScreenEnabled) return;
    const computeFit = () => {
      const imageWidth = widthInNumber || window.innerWidth * 0.9;
      const imageHeight = imageWidth / (aspectRatio || 1);
      const widthRatio = (window.innerWidth * 0.9) / imageWidth;
      const heightRatio = (window.innerHeight * 0.75) / imageHeight;
      setFitScale(Math.min(widthRatio, heightRatio));
    };
    computeFit();
    window.addEventListener("resize", computeFit);
    return () => window.removeEventListener("resize", computeFit);
  }, [isFullScreenEnabled, widthInNumber, aspectRatio]);

  const applyZoom = useCallback((next: number) => {
    const clamped = clampZoom(next);
    setZoom(clamped);
    // back at (or below) the fitted size there is nothing to pan to
    if (clamped <= 1) setOffset({ x: 0, y: 0 });
  }, []);

  const stepZoom = useCallback((direction: "increase" | "decrease") => {
    setZoom((prev) => {
      const target =
        direction === "increase"
          ? (ZOOM_STEPS.find((step) => step > prev + 0.001) ?? MAX_ZOOM)
          : (ZOOM_STEPS.findLast((step) => step < prev - 0.001) ?? MIN_ZOOM);
      if (target <= 1) setOffset({ x: 0, y: 0 });
      return target;
    });
  }, []);

  // keyboard, wheel, scroll lock and focus handling while open
  useEffect(() => {
    if (!isFullScreenEnabled) return;

    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeButtonRef.current?.focus({ preventScroll: true });

    const handleKeyDown = (e: KeyboardEvent) => {
      const handled = ["Escape", "+", "=", "-", "0"];
      if (!handled.includes(e.key)) return;
      // the viewer sits on top of peeks and modals: Escape must close only us
      e.preventDefault();
      e.stopPropagation();
      if (e.key === "Escape") handleClose();
      else if (e.key === "+" || e.key === "=") stepZoom("increase");
      else if (e.key === "-") stepZoom("decrease");
      else resetView();
    };

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      // trackpad pinch arrives as ctrl+wheel with small deltas; plain wheel
      // zooms too, there is nothing to scroll inside the viewer
      const factor = Math.exp(-e.deltaY * WHEEL_ZOOM_SPEED * (e.ctrlKey ? 4 : 1));
      setZoom((prev) => {
        const next = clampZoom(prev * factor);
        if (next <= 1) setOffset({ x: 0, y: 0 });
        return next;
      });
    };

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", handleKeyDown, true);
    window.addEventListener("wheel", handleWheel, { passive: false });

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown, true);
      window.removeEventListener("wheel", handleWheel);
      previouslyFocused?.focus({ preventScroll: true });
    };
  }, [isFullScreenEnabled, handleClose, stepZoom, resetView]);

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest("button")) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const points = [...pointers.current.values()];
    gesture.current = {
      startOffset: offset,
      startPoint:
        points.length === 1 ? points[0] : { x: (points[0].x + points[1].x) / 2, y: (points[0].y + points[1].y) / 2 },
      startZoom: zoom,
      startDistance: points.length >= 2 ? distance(points[0], points[1]) : 0,
      moved: gesture.current?.moved ?? false,
      startedOnImage: (e.target as HTMLElement).tagName === "IMG",
    };
    if (points.length === 1) gesture.current.moved = false;
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
      };
      return;
    }
    gesture.current = null;
    if (!g || g.moved || e.type === "pointercancel") return;

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
    if (!isOnImage) handleClose();
  };

  if (!isFullScreenEnabled) return null;

  const controlButtonClassName =
    "grid size-9 flex-shrink-0 place-items-center rounded-md text-white/80 transition-colors duration-200 hover:bg-white/10 hover:text-white focus-visible:outline-2 focus-visible:outline-white disabled:text-white/30 disabled:hover:bg-transparent";

  return (
    <div
      className="editor-image-full-screen-modal fixed inset-0 z-[200] size-full bg-black/90"
      role="dialog"
      aria-modal="true"
      aria-label="Fullscreen image viewer"
      // keeps the peek overview underneath open: a click in the viewer is not
      // an "outside click" for it (use-peek-overview-outside-click)
      data-prevent-outside-click
    >
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
        <img
          src={src}
          alt=""
          draggable={false}
          className="read-only-image cursor-default rounded-lg"
          style={{
            width: `${(widthInNumber || window.innerWidth * 0.9) * fitScale}px`,
            maxWidth: "none",
            maxHeight: "none",
            aspectRatio,
            transform: `translate3d(${offset.x}px, ${offset.y}px, 0) scale(${zoom})`,
            transformOrigin: "center",
            transition: isPanning ? "none" : "transform 0.15s ease-out",
          }}
        />
      </div>

      <button
        ref={closeButtonRef}
        type="button"
        onClick={handleClose}
        className="absolute top-[max(1rem,env(safe-area-inset-top))] right-[max(1rem,env(safe-area-inset-right))] grid size-11 place-items-center rounded-full bg-black/70 text-white ring-1 ring-white/30 transition-colors hover:bg-white/20 focus-visible:outline-2 focus-visible:outline-white"
        aria-label="Close image viewer"
        title="Close (Esc)"
      >
        <CloseIcon className="size-6" />
      </button>

      <div className="absolute bottom-[max(1.5rem,env(safe-area-inset-bottom))] left-1/2 flex -translate-x-1/2 items-center gap-1 rounded-lg bg-black/80 p-1 ring-1 ring-white/20">
        <button
          type="button"
          onClick={() => stepZoom("decrease")}
          className={controlButtonClassName}
          disabled={zoom <= MIN_ZOOM}
          aria-label="Zoom out"
          title="Zoom out (-)"
        >
          <Minus className="size-4" />
        </button>
        <span className="w-12 text-center text-13 text-white tabular-nums" aria-live="polite">
          {Math.round(100 * zoom)}%
        </span>
        <button
          type="button"
          onClick={() => stepZoom("increase")}
          className={controlButtonClassName}
          disabled={zoom >= MAX_ZOOM}
          aria-label="Zoom in"
          title="Zoom in (+)"
        >
          <PlusIcon className="size-4" />
        </button>
        <button
          type="button"
          onClick={resetView}
          className={controlButtonClassName}
          disabled={zoom === 1 && offset.x === 0 && offset.y === 0}
          aria-label="Reset zoom"
          title="Reset zoom (0)"
        >
          <RotateCcw className="size-4" />
        </button>
        {!isTouchDevice && (
          <>
            <button
              type="button"
              onClick={() => window.open(downloadSrc, "_blank", "noopener,noreferrer")}
              className={controlButtonClassName}
              aria-label="Download image"
            >
              <Download className="size-4" />
            </button>
            <button
              type="button"
              onClick={() => window.open(src, "_blank", "noopener,noreferrer")}
              className={controlButtonClassName}
              aria-label="Open image in new tab"
            >
              <NewTabIcon className="size-4" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export function ImageFullScreenModal(props: Props) {
  if (typeof document === "undefined") return null;
  const modal = <ImageFullScreenModalWithoutPortal {...props} />;
  // #editor-portal sits outside the app tree, so headless UI dialogs treat it as
  // a root container (clicks inside do not close them) and never mark it inert
  const portal = document.querySelector("#editor-portal") ?? document.body;
  return ReactDOM.createPortal(modal, portal);
}
