/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: rona tipis untuk ikon dan kartu
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu peta rona untuk seluruh aplikasi, supaya warna tambahan di ikon dan
 * kartu tetap berasal dari token label tema (ikut terang/gelap/kontras), bukan
 * palet Tailwind mentah. Palet mentah (`text-red-500` dan kawan-kawan) TIDAK
 * menghasilkan CSS sama sekali di tema ini, karena variables.css mengosongkan
 * `--color-*` bawaan Tailwind.
 *
 * Nama kelas ditulis utuh di tiap entri, jangan dirakit dengan template
 * string: Tailwind hanya membangkitkan kelas yang muncul utuh di sumber.
 */

import type { ReactNode } from "react";
import { cn } from "@plane/utils";

export type TTintHue = "indigo" | "emerald" | "orange" | "purple" | "pink" | "yellow" | "crimson" | "grey";

export const TINT_HUES: readonly TTintHue[] = ["indigo", "emerald", "orange", "purple", "pink", "yellow", "crimson"];

/** Warna ikon saja, untuk ikon yang berdiri tanpa latar (mis. navigasi sidebar). */
export const TINT_ICON_CLASS: Record<TTintHue, string> = {
  indigo: "text-label-indigo-icon",
  emerald: "text-label-emerald-icon",
  orange: "text-label-orange-icon",
  purple: "text-label-purple-icon",
  pink: "text-label-pink-icon",
  yellow: "text-label-yellow-icon",
  crimson: "text-label-crimson-icon",
  grey: "text-label-grey-icon",
};

/** Latar tipis + ikon berona, untuk kotak ikon di kartu dan judul bagian. */
export const TINT_CHIP_CLASS: Record<TTintHue, string> = {
  indigo: "bg-label-indigo-bg text-label-indigo-icon",
  emerald: "bg-label-emerald-bg text-label-emerald-icon",
  orange: "bg-label-orange-bg text-label-orange-icon",
  purple: "bg-label-purple-bg text-label-purple-icon",
  pink: "bg-label-pink-bg text-label-pink-icon",
  yellow: "bg-label-yellow-bg text-label-yellow-icon",
  crimson: "bg-label-crimson-bg text-label-crimson-icon",
  grey: "bg-label-grey-bg text-label-grey-icon",
};

/** Garis aksen kiri yang tipis, untuk kartu yang perlu identitas warna tanpa latar penuh. */
export const TINT_ACCENT_BORDER_CLASS: Record<TTintHue, string> = {
  indigo: "border-l-label-indigo-border",
  emerald: "border-l-label-emerald-border",
  orange: "border-l-label-orange-border",
  purple: "border-l-label-purple-border",
  pink: "border-l-label-pink-border",
  yellow: "border-l-label-yellow-border",
  crimson: "border-l-label-crimson-border",
  grey: "border-l-label-grey-border",
};

/**
 * Rona yang stabil untuk satu kunci (id project, nama divisi, dst): kunci yang
 * sama selalu dapat warna yang sama di setiap render dan setiap perangkat.
 * Grey sengaja tidak ikut diundi, karena justru itu yang mau dihindari.
 */
export function tintHueFromKey(key: string | null | undefined): TTintHue {
  if (!key) return "indigo";
  let hash = 0;
  for (let i = 0; i < key.length; i++) hash = (hash * 31 + key.charCodeAt(i)) | 0;
  return TINT_HUES[Math.abs(hash) % TINT_HUES.length];
}

type TTintedIconBoxProps = {
  hue: TTintHue;
  children: ReactNode;
  className?: string;
};

/** Kotak ikon berona tipis. Ukuran bawaan 28px dengan ikon 16px di tengah. */
export function TintedIconBox({ hue, children, className }: TTintedIconBoxProps) {
  return (
    <span
      className={cn(
        "grid size-7 flex-shrink-0 place-items-center rounded-item [&>svg]:size-4",
        TINT_CHIP_CLASS[hue],
        className
      )}
      aria-hidden
    >
      {children}
    </span>
  );
}
