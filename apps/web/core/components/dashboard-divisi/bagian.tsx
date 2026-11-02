/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Dashboard Divisi ringkas (KEP-60)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Potongan kecil yang dipakai tampilan ringkas dan rinci.
 */

import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
import type { TDashboardHealth } from "@/services/workspace_dashboard.service";
import type { TTrendTone } from "./ringkasan";

type TTranslate = ReturnType<typeof useTranslation>["t"];

const HEALTH_CLASS: Record<TDashboardHealth, string> = {
  lancar: "bg-success-subtle text-success-primary",
  perhatian: "bg-warning-subtle text-warning-primary",
  kritis: "bg-danger-subtle text-danger-primary",
};

export function HealthPill({ health }: { health: TDashboardHealth }) {
  const { t } = useTranslation();
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-11 font-semibold whitespace-nowrap",
        HEALTH_CLASS[health]
      )}
    >
      {t(`division_dashboard_ui.health_${health}`)}
    </span>
  );
}

/**
 * Bilah kemajuan. `percent` null = belum ada tugas, bilah kosong. Hiasan saja:
 * persentasenya selalu tertulis di sebelahnya, jadi pembaca layar tidak kehilangan apa pun.
 */
export function ProgressBar({ percent }: { percent: number | null }) {
  return (
    <div aria-hidden className="h-1.5 w-full overflow-hidden rounded-full bg-layer-3">
      <div className="h-full rounded-full bg-accent-primary" style={{ width: `${percent ?? 0}%` }} />
    </div>
  );
}

const TONE_CLASS: Record<TTrendTone, string> = {
  good: "text-success-primary",
  bad: "text-danger-primary",
  neutral: "text-tertiary",
};

/** "+3 dibanding 7 hari sebelumnya". Tanpa angka pembanding, tidak tampil apa pun. */
export function TrendNote({ delta, tone }: { delta: number | null; tone: TTrendTone }) {
  const { t } = useTranslation();
  if (delta === null) return null;
  const text =
    delta === 0
      ? t("division_dashboard_ui.trend_same")
      : t("division_dashboard_ui.trend_vs_prev", { delta: delta > 0 ? `+${delta}` : String(delta) });
  return <p className={cn("mt-1 text-11", TONE_CLASS[tone])}>{text}</p>;
}

/** "-" untuk persentase yang belum bisa dihitung. */
export const formatPercent = (value: number | null): string => (value === null ? "-" : `${value}%`);

export const formatMinutes = (minutes: number, t: TTranslate): string => {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h > 0 && m > 0) return t("division_dashboard_ui.duration_hm", { h, m });
  if (h > 0) return t("division_dashboard_ui.duration_h", { h });
  return t("division_dashboard_ui.duration_m", { m });
};

/** Nama divisi; project yang belum dipetakan ke departemen dikumpulkan tanpa nama. */
export const divisionLabel = (name: string, t: TTranslate): string =>
  name || t("division_dashboard_ui.unassigned_division");
