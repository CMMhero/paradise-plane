/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: building blocks for custom God Mode pages
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Every custom God Mode page (Members, Activity, Features, Trash) is built from
 * these pieces so they look like the upstream pages (General, Email, Workspaces)
 * and like each other. Add a variant here instead of restyling inline.
 */

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@plane/propel/button";
import { cn } from "@plane/utils";

/** Sub-navigation for a sidebar entry that groups several pages. */
export type TPageTab = { label: string; href: string };

const tanpaGarisAkhir = (p: string) => p.replace(/\/+$/, "");

export function PageTabs({ tabs }: { tabs: TPageTab[] }) {
  const pathName = usePathname() ?? "";
  return (
    <nav className="mb-6 flex gap-6 border-b border-subtle" aria-label="Section">
      {tabs.map((tab) => {
        const isActive = tanpaGarisAkhir(pathName).endsWith(tanpaGarisAkhir(tab.href));
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={isActive ? "page" : undefined}
            className={cn("-mb-px border-b-2 pb-2 text-13 font-medium transition-colors", {
              "border-accent-strong text-primary": isActive,
              "border-transparent text-tertiary hover:text-secondary": !isActive,
            })}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}

/** Titled block, mirrors the "All workspaces on this instance" header. */
export function Section({
  title,
  description,
  actions,
  children,
  bordered = false,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  /** Wraps children in a bordered list container (rows separated by dividers). */
  bordered?: boolean;
}) {
  return (
    <section className="space-y-3">
      <div className="flex items-end justify-between gap-4">
        <div className="space-y-0.5">
          <h3 className="text-16 font-medium text-primary">{title}</h3>
          {description && <p className="text-11 leading-5 text-tertiary">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      {bordered ? <div className="divide-y divide-subtle rounded-card border border-subtle">{children}</div> : children}
    </section>
  );
}

/** One setting: label + description on the left, control on the right. */
export function SettingRow({
  title,
  description,
  note,
  control,
}: {
  title: string;
  description?: ReactNode;
  note?: ReactNode;
  control: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-6 px-4 py-4">
      <div className="space-y-1">
        <div className="text-13 font-medium text-primary">{title}</div>
        {description && <div className="text-11 leading-5 text-tertiary">{description}</div>}
        {note}
      </div>
      <div className="shrink-0 pt-0.5">{control}</div>
    </div>
  );
}

/** Filter bar above a list or table. */
export function Toolbar({ children, trailing }: { children: ReactNode; trailing?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="flex flex-wrap items-center gap-2">{children}</div>
      {trailing && <div className="text-13 text-tertiary">{trailing}</div>}
    </div>
  );
}

/** Empty, error, or informational placeholder inside a list area. */
export function StateBox({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "danger" }) {
  return (
    <div
      className={cn("rounded-card border p-8 text-center text-13", {
        "border-subtle text-tertiary": tone === "neutral",
        "border-danger-subtle bg-danger-subtle text-danger-primary": tone === "danger",
      })}
    >
      {children}
    </div>
  );
}

/** Warning banner with an icon slot. */
export function Callout({ icon, title, children }: { icon?: ReactNode; title: string; children?: ReactNode }) {
  return (
    <div className="flex items-start gap-3 rounded-card border border-warning-subtle bg-warning-subtle p-3">
      {icon && <span className="mt-0.5 shrink-0 text-warning-primary">{icon}</span>}
      <div className="text-13">
        <div className="font-medium text-primary">{title}</div>
        {children && <div className="mt-0.5 text-secondary">{children}</div>}
      </div>
    </div>
  );
}

/** Small stat tile used on overview pages. */
export function StatCard({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-card border border-subtle bg-layer-1 px-4 py-3">
      <div className="text-h5-semibold text-primary">{value}</div>
      <div className="mt-0.5 text-13 text-secondary">{label}</div>
      {hint && <div className="mt-1 text-11 text-placeholder">{hint}</div>}
    </div>
  );
}

/** "N items · page X of Y" plus prev/next buttons. */
export function Pagination({
  summary,
  page,
  totalPages,
  onChange,
  prevLabel = "Previous page",
  nextLabel = "Next page",
}: {
  summary: ReactNode;
  page: number;
  totalPages: number;
  onChange: (page: number) => void;
  prevLabel?: string;
  nextLabel?: string;
}) {
  // KEP-64: tombol standar propel ukuran normal, bukan tombol buatan sendiri.
  return (
    <div className="flex items-center justify-between gap-3 text-13 text-tertiary">
      <span>{summary}</span>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          size="lg"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          prependIcon={<ChevronLeft />}
        >
          {prevLabel}
        </Button>
        <Button
          variant="secondary"
          size="lg"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
          appendIcon={<ChevronRight />}
        >
          {nextLabel}
        </Button>
      </div>
    </div>
  );
}
