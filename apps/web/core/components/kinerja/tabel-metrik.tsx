/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: dashboard KPI
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tabel "satu baris per orang" dan "satu baris per departemen/divisi". Kolomnya
 * datang dari tabel metrik server; klik judul kolom untuk mengurutkan, klik
 * nama untuk membuka KPI baris itu.
 */

import { useState } from "react";
import type { ReactNode } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
import type { TKpiMetric, TKpiValues } from "@/services/kinerja.service";
import { formatMetric } from "./bagian";
import type { TSort } from "./kinerja";
import { metricsWithData, sortRows } from "./kinerja";

type TRow = { id: string; values: TKpiValues };

type Props<T extends TRow> = {
  caption: string;
  nameHeader: string;
  rows: T[];
  metrics: TKpiMetric[];
  nameOf: (row: T) => string;
  renderName: (row: T) => ReactNode;
  onOpen: (row: T) => void;
  initialSort?: TSort;
};

export function MetricTable<T extends TRow>(props: Props<T>) {
  const { caption, nameHeader, rows, nameOf, renderName, onOpen, initialSort } = props;
  const { t, currentLocale } = useTranslation();
  const [sort, setSort] = useState<TSort>(initialSort ?? { key: "name", descending: false });
  const metrics = metricsWithData(props.metrics, rows);
  const sorted = sortRows(rows, sort, nameOf);

  const toggle = (key: string) =>
    setSort((current) =>
      current.key === key ? { key, descending: !current.descending } : { key, descending: key !== "name" }
    );

  const header = (key: string, label: string, isNumeric: boolean) => {
    const isActive = sort.key === key;
    const Arrow = sort.descending ? ArrowDown : ArrowUp;
    return (
      <th
        key={key}
        scope="col"
        aria-sort={isActive ? (sort.descending ? "descending" : "ascending") : "none"}
        className={cn("px-3 py-2 font-medium whitespace-nowrap", isNumeric ? "text-right" : "text-left")}
      >
        <button
          type="button"
          onClick={() => toggle(key)}
          className={cn(
            "inline-flex items-center gap-1 rounded-item outline-none hover:text-primary focus-visible:ring-2 focus-visible:ring-accent-strong",
            isActive ? "text-primary" : "text-tertiary"
          )}
        >
          {label}
          <Arrow aria-hidden className={cn("size-3", !isActive && "invisible")} />
        </button>
      </th>
    );
  };

  return (
    <div className="overflow-x-auto rounded-card border border-subtle bg-layer-1">
      <table className="w-full min-w-max text-13">
        <caption className="sr-only">{caption}</caption>
        <thead className="border-b border-subtle text-12">
          <tr>
            {header("name", nameHeader, false)}
            {metrics.map((m) => header(m.key, t(m.label_key), true))}
          </tr>
        </thead>
        <tbody className="divide-y divide-subtle">
          {sorted.map((row) => (
            <tr key={row.id} className="hover:bg-layer-2">
              <th scope="row" className="font-normal px-3 py-2 text-left">
                <button
                  type="button"
                  onClick={() => onOpen(row)}
                  aria-label={t("kinerja.open_kpi_of", { name: nameOf(row) })}
                  className="flex max-w-[16rem] items-center gap-2 rounded-item text-left text-primary outline-none hover:underline focus-visible:ring-2 focus-visible:ring-accent-strong"
                >
                  {renderName(row)}
                </button>
              </th>
              {metrics.map((m) => (
                <td key={m.key} className="px-3 py-2 text-right text-secondary tabular-nums">
                  {formatMetric(m, row.values[m.key], t, currentLocale)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
