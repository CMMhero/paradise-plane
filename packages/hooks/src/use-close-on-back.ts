/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tombol Kembali menutup overlay
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef } from "react";

const STATE_KEY = "__paradiseOverlay";

let overlayCounter = 0;

const isOurEntry = (id: string | null): boolean => {
  if (!id || typeof window === "undefined") return false;
  const state = window.history.state as Record<string, unknown> | null;
  return !!state && state[STATE_KEY] === id;
};

/**
 * Makes the browser (and Android hardware) Back button close an overlay
 * instead of leaving the page behind it.
 *
 * While `isOpen` is true, one history entry with the SAME url is pushed. Back
 * pops that entry, which fires `popstate` and calls `onClose`. When the overlay
 * is closed from inside the app (close button, Escape, backdrop), the entry is
 * removed again with `history.back()`, so the history stack never grows and a
 * later Back still leaves the page as the user expects.
 *
 * Only meant for full-screen views (image lightbox, viewer full screen), NOT
 * for ordinary modals: a modal that navigates on submit would otherwise have
 * its new route undone by the cleanup `history.back()`. The cleanup only runs
 * `back()` while our entry is still the current one, so a route change made by
 * the overlay itself is left alone.
 *
 * The cleanup is deferred by one tick so a StrictMode remount (cleanup and
 * effect back to back) reuses the entry instead of pushing a second one.
 */
export const useCloseOnBack = (isOpen: boolean, onClose: () => void): void => {
  const onCloseRef = useRef(onClose);
  const entryIdRef = useRef<string | null>(null);
  const pendingBackRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!isOpen || typeof window === "undefined") return;

    if (pendingBackRef.current && isOurEntry(entryIdRef.current)) {
      // remount right after cleanup: keep the entry we already pushed
      clearTimeout(pendingBackRef.current);
      pendingBackRef.current = null;
    } else {
      overlayCounter += 1;
      const id = `overlay-${Date.now()}-${overlayCounter}`;
      entryIdRef.current = id;
      const currentState = (window.history.state as Record<string, unknown> | null) ?? {};
      window.history.pushState({ ...currentState, [STATE_KEY]: id }, "");
    }

    const id = entryIdRef.current;
    let closedByBack = false;

    const handlePopState = () => {
      // our entry is gone from the top of the stack: the user pressed Back
      if (isOurEntry(id)) return;
      closedByBack = true;
      entryIdRef.current = null;
      onCloseRef.current();
    };
    window.addEventListener("popstate", handlePopState);

    return () => {
      window.removeEventListener("popstate", handlePopState);
      if (closedByBack) return;
      pendingBackRef.current = setTimeout(() => {
        pendingBackRef.current = null;
        if (isOurEntry(id)) window.history.back();
        entryIdRef.current = null;
      }, 0);
    };
  }, [isOpen]);
};
