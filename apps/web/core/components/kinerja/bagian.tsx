/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: dashboard KPI
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Potongan kecil yang dipakai beberapa bagian halaman KPI.
 */

import type { ReactNode } from "react";
import type { useTranslation } from "@plane/i18n";
import type { TKpiMetric } from "@/services/kinerja.service";

export type TTranslate = ReturnType<typeof useTranslation>["t"];

const number = (value: number, locale: string) => value.toLocaleString(locale, { maximumFractionDigits: 1 });

/** Nilai metrik dengan satuannya; "-" untuk yang belum bisa dihitung. */
export function formatMetric(
  metric: TKpiMetric,
  value: number | null | undefined,
  t: TTranslate,
  locale: string
): string {
  if (value === null || value === undefined) return "-";
  if (metric.unit === "percent") return `${value}%`;
  if (metric.unit === "count") return number(value, locale);
  return t(`kinerja.unit.${metric.unit}`, { value: number(value, locale) });
}

/** Selisih bertanda: "+3", "-1,5 hari", "+5 poin". */
export function formatDelta(metric: TKpiMetric, delta: number, t: TTranslate, locale: string): string {
  const sign = delta > 0 ? "+" : "-";
  const size = number(Math.abs(delta), locale);
  if (metric.unit === "count") return `${sign}${size}`;
  return `${sign}${t(`kinerja.unit.${metric.unit === "percent" ? "points" : metric.unit}`, { value: size })}`;
}

export function Section({
  id,
  title,
  hint,
  children,
}: {
  id: string;
  title: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id={id} className="text-14 font-semibold text-primary">
          {title}
        </h2>
        {hint && <span className="text-12 text-tertiary">{hint}</span>}
      </div>
      {children}
    </section>
  );
}

export function EmptyNote({ children }: { children: ReactNode }) {
  return <p className="rounded-card border border-subtle px-4 py-3 text-13 text-tertiary">{children}</p>;
}
