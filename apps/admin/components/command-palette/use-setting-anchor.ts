/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: scroll to the setting a palette link names
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * `/rules/#setting-TASK_DELETE_RULE` opens the tab, waits for the row (the
 * registry loads after the page mounts), scrolls it to the middle of the view
 * and marks it for a moment so the eye lands on it. Works for pasted links too.
 */

import { useEffect } from "react";
import { useLocation } from "react-router";

/** How long to wait for the row to render before giving up. */
const WAIT_MS = 4000;
const HIGHLIGHT_MS = 2200;

export function useSettingAnchor(): void {
  const { hash, key } = useLocation();

  useEffect(() => {
    const id = decodeURIComponent(hash.replace(/^#/, ""));
    if (!id.startsWith("setting-")) return;

    let frame = 0;
    let highlightTimer: ReturnType<typeof setTimeout> | undefined;
    const started = performance.now();

    const seek = () => {
      const el = document.getElementById(id);
      if (!el) {
        if (performance.now() - started < WAIT_MS) frame = requestAnimationFrame(seek);
        return;
      }
      const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      el.scrollIntoView({ block: "center", behavior: reduceMotion ? "auto" : "smooth" });
      el.dataset.highlight = "true";
      highlightTimer = setTimeout(() => delete el.dataset.highlight, HIGHLIGHT_MS);
    };
    frame = requestAnimationFrame(seek);

    return () => {
      cancelAnimationFrame(frame);
      if (highlightTimer) clearTimeout(highlightTimer);
      document.getElementById(id)?.removeAttribute("data-highlight");
    };
    // oxlint-disable-next-line react/exhaustive-effect-dependencies -- key re-runs the scroll when the same hash is opened again
  }, [hash, key]);
}
