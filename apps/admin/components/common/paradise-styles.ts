/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: shared classes for custom God Mode pages
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Plain values live apart from components so Fast Refresh keeps hot-swapping
 * the component files (same reason as members/constants.ts).
 */

export const selectClass =
  "rounded-md border border-subtle bg-layer-1 px-2 py-1.5 text-13 text-primary outline-none focus:border-accent-strong";

export const inputClass =
  "rounded-md border border-subtle bg-layer-1 px-2 py-1.5 text-13 text-primary outline-none placeholder:text-placeholder focus:border-accent-strong";

export const tableClass = {
  wrap: "overflow-x-auto rounded-md border border-subtle",
  table: "w-full text-13",
  head: "bg-layer-1 text-tertiary",
  th: "px-3 py-2 text-left font-medium",
  row: "border-t border-subtle",
  td: "px-3 py-2",
};

export const formatDateTime = (iso: string | null | undefined): string =>
  iso
    ? new Date(iso).toLocaleString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";

/** "5m ago", "3h ago", "2d ago"; falls back to the date past a week. */
export const formatRelative = (iso: string | null | undefined, now: number = Date.now()): string => {
  if (!iso) return "—";
  const detik = Math.round((now - new Date(iso).getTime()) / 1000);
  if (Number.isNaN(detik)) return "—";
  if (detik < 60) return "just now";
  const menit = Math.round(detik / 60);
  if (menit < 60) return `${menit}m ago`;
  const jam = Math.round(menit / 60);
  if (jam < 24) return `${jam}h ago`;
  const hari = Math.round(jam / 24);
  if (hari < 7) return `${hari}d ago`;
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
};

export const formatTime = (iso: string): string =>
  new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });

/** Day heading for grouped lists: "Today", "Yesterday", "Wed, 28 Oct 2026". */
const awalHari = (x: Date): number => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();

export const formatDayHeading = (iso: string, now: Date = new Date()): string => {
  const d = new Date(iso);
  const selisih = Math.round((awalHari(now) - awalHari(d)) / 86_400_000);
  if (selisih === 0) return "Today";
  if (selisih === 1) return "Yesterday";
  return d.toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short", year: "numeric" });
};

/** Local calendar day key (YYYY-MM-DD), used to group rows by day. */
export const dayKey = (iso: string): string => {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

/** Avatar fallback colours from the label palette, picked by name so a person keeps one colour.
 * CSS variables, not classes: Propel Avatar takes its fallback colours as inline styles. */
const RONA_AVATAR = ["indigo", "emerald", "yellow", "crimson", "purple", "orange", "pink"];

export const avatarTone = (seed: string): { bg: string; text: string } => {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  const rona = RONA_AVATAR[h % RONA_AVATAR.length];
  return { bg: `var(--label-${rona}-bg)`, text: `var(--label-${rona}-text)` };
};
