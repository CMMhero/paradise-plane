/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: wadah halaman bersama
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu wadah untuk halaman Paradise: padding, lebar maksimum, dan judul yang
 * sama di semua halaman. Menggulir tetap tugas ContentWrapper di layout.
 *
 * - default: daftar dan formulir (max-w-3xl)
 * - wide: dasbor dan grid (max-w-6xl)
 * - full: tanpa padding dan tanpa batas lebar, untuk halaman yang mengurus
 *   tata letaknya sendiri (obrolan)
 */

import type { ReactNode } from "react";
// plane imports
import { cn } from "@plane/utils";

export type TPageShellWidth = "default" | "wide" | "full";

const WIDTH_CLASS: Record<TPageShellWidth, string> = {
  default: "mx-auto flex max-w-3xl flex-col gap-5 px-page-x py-6",
  wide: "mx-auto flex max-w-6xl flex-col gap-5 px-page-x py-6",
  full: "h-full min-h-0",
};

type TPageShellProps = {
  width?: TPageShellWidth;
  className?: string;
  children: ReactNode;
};

function PageShellRoot({ width = "default", className, children }: TPageShellProps) {
  return <div className={cn("w-full", WIDTH_CLASS[width], className)}>{children}</div>;
}

type TPageShellHeaderProps = {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
};

function PageShellHeader({ title, description, actions }: TPageShellHeaderProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h1 className="truncate text-20 font-semibold text-primary">{title}</h1>
        {description && <div className="text-12 text-tertiary">{description}</div>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export const PageShell = Object.assign(PageShellRoot, { Header: PageShellHeader });
