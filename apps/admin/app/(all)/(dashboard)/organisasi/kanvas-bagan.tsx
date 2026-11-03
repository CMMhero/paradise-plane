/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: bingkai kanvas bagan organisasi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Viewport + toolbar zoom + mode layar penuh di sekeliling isi bagan. Layar
 * penuh = bingkai yang SAMA berganti kelas jadi `fixed inset-0` (bukan
 * Fullscreen API, bukan portal): modal kelola tetap tampil di atasnya (z-30
 * ModalCore > z-20 bingkai) dan state geser/zoom tidak hilang.
 */

import { useEffect, useState, type ReactNode } from "react";
import { Maximize2, Minimize2, Minus, Plus, Scan } from "lucide-react";
// plane imports
import { IconButton } from "@plane/propel/icon-button";
import { Tooltip } from "@plane/propel/tooltip";
import { cn } from "@plane/utils";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { ATRIBUT_ABAIKAN, useKanvasGeser } from "./kanvas";

function TombolAlat({
  label,
  icon,
  onClick,
}: {
  label: string;
  icon: React.FC<{ className?: string }>;
  onClick: () => void;
}) {
  return (
    <Tooltip tooltipContent={label}>
      <IconButton variant="ghost" size="lg" icon={icon} aria-label={label} onClick={onClick} />
    </Tooltip>
  );
}

export function KanvasBagan({ children, judul }: { children: ReactNode; judul?: ReactNode }) {
  const { s } = useGodmodeStrings();
  const [layarPenuh, setLayarPenuh] = useState(false);
  const { viewportRef, kontenRef, tampilan, sedangSeret, zoomMasuk, zoomKeluar, zoomAsli, pasUlang, viewportProps } =
    useKanvasGeser();

  // Layar penuh: kunci scroll halaman, Esc menutup, lalu paskan ulang ke ukuran baru.
  useEffect(() => {
    const raf = requestAnimationFrame(pasUlang);
    if (!layarPenuh) return () => cancelAnimationFrame(raf);
    const overflowLama = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: globalThis.KeyboardEvent) => {
      // Esc di dalam modal kelola milik modalnya, bukan menutup layar penuh.
      if (e.key !== "Escape" || document.querySelector("[role='dialog']")) return;
      setLayarPenuh(false);
    };
    window.addEventListener("keydown", onKey);
    return () => {
      cancelAnimationFrame(raf);
      document.body.style.overflow = overflowLama;
      window.removeEventListener("keydown", onKey);
    };
  }, [layarPenuh, pasUlang]);

  return (
    <div
      className={cn(
        "flex flex-col overflow-hidden border-subtle bg-layer-1",
        layarPenuh ? "fixed inset-0 z-20 border-0" : "relative h-[calc(100vh-18rem)] min-h-[440px] rounded-card border"
      )}
    >
      <div
        className="flex shrink-0 items-center gap-2 border-b border-subtle bg-surface-1 px-3 py-1.5"
        {...{ [ATRIBUT_ABAIKAN]: "" }}
      >
        <div className="min-w-0 flex-1 truncate text-13 font-medium text-primary">{judul}</div>
        <span className="hidden text-11 text-tertiary md:inline">{s.org.canvas_hint}</span>
        <div className="flex items-center gap-0.5 rounded-button border border-subtle bg-layer-1 p-0.5">
          <TombolAlat label={s.org.zoom_out} icon={Minus} onClick={zoomKeluar} />
          <Tooltip tooltipContent={s.org.zoom_reset}>
            <button
              type="button"
              onClick={zoomAsli}
              aria-label={s.org.zoom_reset}
              className="min-w-12 rounded-button px-1.5 py-1 text-center text-11 font-medium text-secondary tabular-nums hover:bg-layer-transparent-hover hover:text-primary"
            >
              {Math.round(tampilan.k * 100)}%
            </button>
          </Tooltip>
          <TombolAlat label={s.org.zoom_in} icon={Plus} onClick={zoomMasuk} />
        </div>
        <TombolAlat label={s.org.zoom_fit} icon={Scan} onClick={pasUlang} />
        <TombolAlat
          label={layarPenuh ? s.org.fullscreen_exit : s.org.fullscreen}
          icon={layarPenuh ? Minimize2 : Maximize2}
          onClick={() => setLayarPenuh((v) => !v)}
        />
      </div>

      <div
        ref={viewportRef}
        role="application"
        aria-label={s.org.canvas_label}
        // oxlint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- kanvas digeser lewat papan ketik (panah, +/-, 0)
        tabIndex={0}
        className={cn(
          "relative flex-1 touch-none overflow-hidden outline-none focus-visible:ring-2 focus-visible:ring-accent-strong focus-visible:ring-inset",
          "bg-[radial-gradient(circle,var(--border-color-subtle)_1px,transparent_1px)] bg-[length:20px_20px]",
          sedangSeret ? "cursor-grabbing select-none" : "cursor-grab"
        )}
        {...viewportProps}
      >
        <div
          ref={kontenRef}
          className="absolute top-0 left-0 w-max origin-top-left will-change-transform"
          style={{ transform: `translate(${tampilan.x}px, ${tampilan.y}px) scale(${tampilan.k})` }}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
