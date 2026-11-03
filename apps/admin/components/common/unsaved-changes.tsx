/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: penanda perubahan belum disimpan di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu pola untuk SEMUA formulir setelan God Mode:
 *
 * - `UnsavedChangesProvider` dipasang sekali di layout dashboard. Ia memegang
 *   daftar formulir yang sedang kotor, memasang `beforeunload` (tutup tab,
 *   muat ulang, keluar), dan `useBlocker` React Router (pindah halaman di
 *   dalam God Mode) lalu menanyakan dulu sebelum perubahan dibuang.
 * - `UnsavedChangesBar` dirender layout DI LUAR area gulir, menempel di bawah
 *   konten. Karena bukan bagian halaman yang digulir, bar ini selalu terlihat
 *   di mana pun orang menggulir.
 * - Formulir cukup memanggil `useUnsavedChanges({ isDirty, onSave, onDiscard })`
 *   atau merender `<UnsavedBar ... />`. Formulir di dalam modal memakai
 *   `showBar: false` (footer modal sudah selalu terlihat) plus
 *   `<UnsavedIndicator />` di footer-nya, tapi tetap ikut dijaga saat pindah
 *   halaman.
 *
 * Teks sengaja Inggris dan hardcode: God Mode hanya berbahasa Inggris.
 */

import { createContext, useCallback, useContext, useEffect, useId, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useBlocker } from "react-router";
import type { BlockerFunction } from "react-router";
import { Button } from "@plane/propel/button";
import { cn } from "@plane/utils";
import { EModalWidth, ParadiseModal } from "./paradise-ui";

type TUnsavedEntry = {
  id: string;
  label?: string;
  isSaving: boolean;
  canSave: boolean;
  showBar: boolean;
  save: () => void;
  discard: () => void;
};

type TUnsavedContext = {
  upsert: (entry: TUnsavedEntry) => void;
  remove: (id: string) => void;
  entries: TUnsavedEntry[];
};

const UnsavedChangesContext = createContext<TUnsavedContext | null>(null);

export type TUseUnsavedChanges = {
  isDirty: boolean;
  /** Runs the form's own save (validation included). */
  onSave: () => void | Promise<unknown>;
  /** Puts the form back to the last saved values. */
  onDiscard: () => void;
  isSaving?: boolean;
  /** False while the draft is invalid: Save stays disabled, Discard still works. */
  canSave?: boolean;
  /** Which form this is, shown when a page has more than one (e.g. "SMTP"). */
  label?: string;
  /** False for forms inside a modal, whose footer is already always visible. */
  showBar?: boolean;
};

/** Registers a dirty form with the dashboard: bottom bar + leave-page guard. */
export function useUnsavedChanges({
  isDirty,
  onSave,
  onDiscard,
  isSaving = false,
  canSave = true,
  label,
  showBar = true,
}: TUseUnsavedChanges) {
  const ctx = useContext(UnsavedChangesContext);
  const id = useId();
  const saveRef = useRef(onSave);
  const discardRef = useRef(onDiscard);
  useEffect(() => {
    saveRef.current = onSave;
    discardRef.current = onDiscard;
  });

  const upsert = ctx?.upsert;
  const remove = ctx?.remove;

  // Presence only follows isDirty, so a Saving state change updates the row in place.
  useEffect(() => {
    if (!remove || !isDirty) return;
    return () => remove(id);
  }, [remove, id, isDirty]);

  useEffect(() => {
    if (!upsert || !isDirty) return;
    upsert({
      id,
      label,
      isSaving,
      canSave,
      showBar,
      save: () => void saveRef.current(),
      discard: () => discardRef.current(),
    });
  }, [upsert, id, isDirty, label, isSaving, canSave, showBar]);
}

/** Declarative form of `useUnsavedChanges`. Renders nothing in place; the bar lives in the layout. */
export function UnsavedBar(props: TUseUnsavedChanges) {
  useUnsavedChanges(props);
  return null;
}

/** Small "Unsaved changes" marker for modal footers and inline save rows. */
export function UnsavedIndicator({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 text-12 font-medium text-warning-primary", className)}>
      <span aria-hidden className="size-1.5 shrink-0 rounded-full bg-warning-primary" />
      Unsaved changes
    </span>
  );
}

export function UnsavedChangesProvider({ children }: { children: ReactNode }) {
  const [entries, setEntries] = useState<TUnsavedEntry[]>([]);

  const upsert = useCallback((entry: TUnsavedEntry) => {
    setEntries((prev) => {
      const i = prev.findIndex((e) => e.id === entry.id);
      if (i === -1) return [...prev, entry];
      return prev.map((e, j) => (j === i ? entry : e));
    });
  }, []);
  const remove = useCallback((id: string) => setEntries((prev) => prev.filter((e) => e.id !== id)), []);

  const isDirty = entries.length > 0;

  // Closing the tab, reloading, or a full-page form post (sign out).
  useEffect(() => {
    if (!isDirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      // Older browsers only show the prompt when returnValue is set.
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isDirty]);

  // In-app navigation. Tabs within one page keep the same pathname and are not blocked.
  const shouldBlock = useCallback<BlockerFunction>(
    ({ currentLocation, nextLocation }) => isDirty && currentLocation.pathname !== nextLocation.pathname,
    [isDirty]
  );
  const blocker = useBlocker(shouldBlock);

  const value = useMemo(() => ({ upsert, remove, entries }), [upsert, remove, entries]);

  return (
    <UnsavedChangesContext.Provider value={value}>
      {children}
      <ParadiseModal
        isOpen={blocker.state === "blocked"}
        onClose={() => blocker.reset?.()}
        width={EModalWidth.MD}
        title="Leave without saving?"
        closeLabel="Keep editing"
        footer={
          <>
            <Button variant="secondary" size="base" onClick={() => blocker.reset?.()}>
              Keep editing
            </Button>
            <Button variant="error-fill" size="base" onClick={() => blocker.proceed?.()}>
              Discard and leave
            </Button>
          </>
        }
      >
        <p className="text-13 text-secondary">
          {entries.length > 1
            ? `${entries.length} forms on this page have changes that are not saved yet. They will be lost if you leave.`
            : "This page has changes that are not saved yet. They will be lost if you leave."}
        </p>
      </ParadiseModal>
    </UnsavedChangesContext.Provider>
  );
}

/**
 * Bottom bar of the dashboard content area. Rendered by the layout outside the
 * scrolling region, so it stays on screen no matter how far the page scrolls.
 */
export function UnsavedChangesBar() {
  const ctx = useContext(UnsavedChangesContext);
  const rows = (ctx?.entries ?? []).filter((e) => e.showBar);

  return (
    <section aria-label="Unsaved changes" aria-live="polite" className="shrink-0">
      {rows.length > 0 && (
        <div className="divide-y divide-subtle border-t border-warning-subtle bg-surface-1 shadow-raised-200">
          {rows.map((row) => (
            <div
              key={row.id}
              className="mx-auto flex w-full max-w-[1200px] flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-2.5 md:px-8"
            >
              <div className="flex min-w-0 items-center gap-2">
                <UnsavedIndicator className="text-13" />
                {row.label && <span className="truncate text-12 text-tertiary">· {row.label}</span>}
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Button variant="secondary" size="base" disabled={row.isSaving} onClick={row.discard}>
                  Discard
                </Button>
                <Button
                  variant="primary"
                  size="base"
                  loading={row.isSaving}
                  disabled={!row.canSave || row.isSaving}
                  onClick={row.save}
                >
                  {row.isSaving ? "Saving" : "Save changes"}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
