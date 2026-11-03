/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Dashboard Divisi ringkas (KEP-60)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Potongan kecil yang dipakai tampilan ringkas dan rinci.
 */

import { useTranslation } from "@plane/i18n";
import { Badge } from "@plane/propel/badge";
import type { TBadgeVariant } from "@plane/propel/badge";
import { cn } from "@plane/utils";
import type { TDashboardHealth } from "@/services/workspace_dashboard.service";
import type { TTrendTone } from "./ringkasan";

type TTranslate = ReturnType<typeof useTranslation>["t"];

const HEALTH_VARIANT: Record<TDashboardHealth, TBadgeVariant> = {
  lancar: "success",
  perhatian: "warning",
  kritis: "danger",
};

export function HealthPill({ health }: { health: TDashboardHealth }) {
  const { t } = useTranslation();
  return <Badge variant={HEALTH_VARIANT[health]}>{t(`division_dashboard_ui.health_${health}`)}</Badge>;
}

/**
 * Bilah kemajuan. `percent` null = belum ada tugas, bilah kosong. Hiasan saja:
 * persentasenya selalu tertulis di sebelahnya, jadi pembaca layar tidak kehilangan apa pun.
 */
export function ProgressBar({ percent }: { percent: number | null }) {
  return (
    <div aria-hidden className="h-1.5 w-full overflow-hidden rounded-control bg-layer-3">
      <div className="h-full rounded-control bg-accent-primary" style={{ width: `${percent ?? 0}%` }} />
    </div>
  );
}

const TONE_CLASS: Record<TTrendTone, string> = {
  good: "text-success-primary",
  bad: "text-danger-primary",
  neutral: "text-tertiary",
};

/**
 * "+3 dibanding 7 hari sebelumnya". Tanpa angka pembanding, tidak tampil apa pun.
 * `against` = "period" untuk laporan, yang pembandingnya sepanjang periode terpilih.
 */
export function TrendNote({
  delta,
  tone,
  against = "week",
}: {
  delta: number | null;
  tone: TTrendTone;
  against?: "week" | "period";
}) {
  const { t } = useTranslation();
  if (delta === null) return null;
  const prefix = against === "period" ? "division_dashboard_ui.report_trend" : "division_dashboard_ui.trend";
  const text =
    delta === 0 ? t(`${prefix}_same`) : t(`${prefix}_vs_prev`, { delta: delta > 0 ? `+${delta}` : String(delta) });
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
