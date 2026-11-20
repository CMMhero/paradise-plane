/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: dashboard KPI
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tugas terbuka menurut status dan prioritas. Bilah mendatar dengan label dan
 * angka di tiap baris, jadi warnanya tidak pernah jadi satu-satunya penanda.
 */

import { useTranslation } from "@plane/i18n";
import type { TKpiReport } from "@/services/kinerja.service";
import { EmptyNote } from "./bagian";

const STATE_GROUPS = ["backlog", "unstarted", "started"] as const;
const PRIORITIES = ["urgent", "high", "medium", "low", "none"] as const;

// Rona status mengikuti ikon grup status; prioritas mengikuti token prioritas aplikasi.
const STATE_COLOR: Record<(typeof STATE_GROUPS)[number], string> = {
  backlog: "var(--text-color-tertiary)",
  unstarted: "var(--priority-low)",
  started: "var(--priority-medium)",
};

type TBar = { key: string; label: string; count: number; color: string };

export function Workload({ workload }: { workload: TKpiReport["workload"] }) {
  const { t } = useTranslation();
  const states: TBar[] = STATE_GROUPS.map((key) => ({
    key,
    label: t(`kinerja.state_group.${key}`),
    count: workload.by_state_group[key] ?? 0,
    color: STATE_COLOR[key],
  }));
  const priorities: TBar[] = PRIORITIES.map((key) => ({
    key,
    label: t(`kinerja.priority.${key}`),
    count: workload.by_priority[key] ?? 0,
    color: `var(--priority-${key})`,
  }));

  if (states.every((s) => s.count === 0)) return <EmptyNote>{t("kinerja.workload.empty")}</EmptyNote>;

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      <BarList title={t("kinerja.workload.by_state")} bars={states} />
      <BarList title={t("kinerja.workload.by_priority")} bars={priorities} />
    </div>
  );
}

function BarList({ title, bars }: { title: string; bars: TBar[] }) {
  const max = Math.max(1, ...bars.map((b) => b.count));
  return (
    <div className="rounded-card border border-subtle bg-layer-1 px-4 py-3">
      <h3 className="mb-2.5 text-12 font-medium text-secondary">{title}</h3>
      <ul className="flex flex-col gap-2">
        {bars.map((bar) => (
          <li key={bar.key} className="grid grid-cols-[minmax(0,6.5rem)_1fr_2.5rem] items-center gap-3">
            <span className="truncate text-13 text-primary">{bar.label}</span>
            <div aria-hidden className="h-2 overflow-hidden rounded-control bg-layer-3">
              <div
                className="h-full rounded-control"
                style={{ width: `${(bar.count * 100) / max}%`, backgroundColor: bar.color }}
              />
            </div>
            <span className="text-right text-13 font-semibold text-primary tabular-nums">{bar.count}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
