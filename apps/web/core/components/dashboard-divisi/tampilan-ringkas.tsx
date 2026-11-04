/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Dashboard Divisi ringkas (KEP-60)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tampilan bawaan untuk direktur dan Super Admin: satu kalimat, empat angka,
 * kesehatan per divisi, dan paling banyak lima hal yang perlu dilihat. Angka
 * per project dan jam kerja sengaja tidak ada di sini; tempatnya tampilan rinci.
 */

import type { ReactNode } from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { cn } from "@plane/utils";
import type { TDivisionDashboard, TDivisionGroup } from "@/services/workspace_dashboard.service";
import { HealthPill, ProgressBar, TrendNote, divisionLabel, formatPercent } from "./bagian";
import type { TAttentionItem } from "./ringkasan";
import { buildAttentionItems, buildHeadline, trendTone, weeklyDelta } from "./ringkasan";

type Props = {
  workspaceSlug: string;
  data: TDivisionDashboard;
  onShowDetail: () => void;
};

export function SummaryView({ workspaceSlug, data, onShowDetail }: Props) {
  const { t } = useTranslation();
  const attention = buildAttentionItems(data);

  return (
    <div className="flex flex-col gap-6">
      <Headline divisions={data.divisions} />
      <KpiRow data={data} />

      <section aria-labelledby="dashboard-kesehatan" className="flex flex-col gap-3">
        <div className="flex items-baseline justify-between gap-2">
          <h2 id="dashboard-kesehatan" className="text-14 font-semibold text-primary">
            {t("division_dashboard_ui.section_health")}
          </h2>
          <span className="text-12 text-tertiary">{t("division_dashboard_ui.section_health_hint")}</span>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data.divisions.map((d) => (
            <DivisionCard key={d.id ?? "tanpa-divisi"} division={d} />
          ))}
        </div>
        <p className="text-11 text-tertiary">
          {t("division_dashboard_ui.health_rule", {
            attention: data.thresholds.attention,
            critical: data.thresholds.critical,
          })}
        </p>
      </section>

      <section aria-labelledby="dashboard-perhatian" className="flex flex-col gap-3">
        <h2 id="dashboard-perhatian" className="text-14 font-semibold text-primary">
          {t("division_dashboard_ui.section_attention")}
        </h2>
        {attention.length === 0 ? (
          <p className="rounded-card border border-subtle px-4 py-3 text-13 text-tertiary">
            {t("division_dashboard_ui.section_attention_empty")}
          </p>
        ) : (
          <ul className="divide-y divide-subtle rounded-card border border-subtle">
            {attention.map((item) => (
              <AttentionRow key={item.key} item={item} workspaceSlug={workspaceSlug} />
            ))}
          </ul>
        )}
      </section>

      <Button
        variant="link"
        size="base"
        className="h-auto max-w-full self-start text-left !whitespace-normal"
        onClick={onShowDetail}
      >
        {t("division_dashboard_ui.detail_hint")}
      </Button>
    </div>
  );
}

function Headline({ divisions }: { divisions: TDivisionGroup[] }) {
  const { t } = useTranslation();
  const headline = buildHeadline(divisions);

  if (headline.kind === "empty") {
    return <p className="text-14 text-tertiary">{t("division_dashboard_ui.headline_empty")}</p>;
  }
  if (headline.kind === "all_ok") {
    return (
      <p className="rounded-card bg-success-subtle px-4 py-3 text-14 text-primary">
        {t("division_dashboard_ui.headline_all_ok")}
      </p>
    );
  }
  const isCritical = headline.worst.health === "kritis";
  return (
    <p
      className={cn(
        "rounded-card px-4 py-3 text-14 leading-relaxed text-primary",
        isCritical ? "bg-danger-subtle" : "bg-warning-subtle"
      )}
    >
      {t("division_dashboard_ui.headline_ok_count", { ok: headline.ok, total: headline.total })}{" "}
      <span className="font-semibold">
        {t("division_dashboard_ui.headline_worst", {
          name: divisionLabel(headline.worst.name, t),
          count: headline.worst.issues_overdue,
        })}
      </span>
    </p>
  );
}

function KpiRow({ data }: { data: TDivisionDashboard }) {
  const { t } = useTranslation();
  const { totals } = data;
  const doneDelta = weeklyDelta(totals.completed_7d, totals.completed_prev_7d);
  const overdueDelta = weeklyDelta(totals.issues_overdue, totals.overdue_prev_7d);

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Kpi
        value={formatPercent(totals.on_time_rate)}
        label={t("tanggal_ui.kpi_on_time", { days: data.on_time_window_days ?? 30 })}
      />
      <Kpi value={String(totals.completed_7d)} label={t("division_dashboard_ui.kpi_done_7d")}>
        <TrendNote delta={doneDelta} tone={trendTone(doneDelta, true)} />
      </Kpi>
      <Kpi
        value={String(totals.issues_overdue)}
        label={t("division_dashboard_ui.kpi_overdue")}
        isAlert={totals.issues_overdue > 0}
      >
        <TrendNote delta={overdueDelta} tone={trendTone(overdueDelta, false)} />
      </Kpi>
      <Kpi
        value={String(totals.pending_approvals)}
        label={t("division_dashboard_ui.kpi_approvals")}
        isAlert={totals.pending_approvals > 0}
      />
    </div>
  );
}

type TKpiProps = { value: string; label: string; isAlert?: boolean; children?: ReactNode };

function Kpi({ value, label, isAlert = false, children }: TKpiProps) {
  return (
    <div className="rounded-card border border-subtle bg-layer-1 px-4 py-3">
      <p className={cn("text-24 leading-tight font-semibold", isAlert ? "text-danger-primary" : "text-primary")}>
        {value}
      </p>
      <p className="mt-0.5 text-12 text-tertiary">{label}</p>
      {children}
    </div>
  );
}

function DivisionCard({ division }: { division: TDivisionGroup }) {
  const { t } = useTranslation();
  const name = divisionLabel(division.name, t);
  return (
    <div className="rounded-card border border-subtle bg-layer-1 px-4 py-3">
      <div className="flex items-center justify-between gap-2">
        <p className="truncate text-14 font-semibold text-primary" title={name}>
          {name}
        </p>
        <HealthPill health={division.health} />
      </div>
      <div className="mt-3 mb-1.5">
        <ProgressBar percent={division.completion_rate} />
      </div>
      <div className="flex justify-between gap-2 text-12 text-tertiary">
        <span>{t("division_dashboard_ui.done_pct", { pct: formatPercent(division.completion_rate) })}</span>
        <span className={division.issues_overdue > 0 ? "font-medium text-danger-primary" : undefined}>
          {t("division_dashboard_ui.overdue_count", { count: division.issues_overdue })}
        </span>
      </div>
    </div>
  );
}

function AttentionRow({ item, workspaceSlug }: { item: TAttentionItem; workspaceSlug: string }) {
  const { t } = useTranslation();
  const { project } = item;
  const base = `/${workspaceSlug}/projects/${project.id}`;
  const isApproval = item.kind === "approvals";
  const href = isApproval ? `${base}/persetujuan` : `${base}/issues`;
  const where = project.department ? `${project.name} (${project.department.code})` : project.name;
  const detail = isApproval
    ? t("division_dashboard_ui.attention_approvals", { count: item.count })
    : item.oldestDays === null
      ? t("division_dashboard_ui.overdue_count", { count: item.count })
      : t("division_dashboard_ui.attention_overdue", { count: item.count, days: item.oldestDays });

  return (
    <li>
      <Link href={href} className="group flex items-center justify-between gap-3 px-4 py-2.5 hover:bg-layer-2">
        <div className="min-w-0">
          <p className="truncate text-13 font-medium text-primary">{where}</p>
          <p className={cn("text-12", isApproval ? "text-warning-primary" : "text-danger-primary")}>{detail}</p>
        </div>
        <span className="flex shrink-0 items-center gap-0.5 text-12 text-tertiary group-hover:text-secondary">
          {t(isApproval ? "division_dashboard_ui.review" : "division_dashboard_ui.open")}
          <ChevronRight className="size-3.5" />
        </span>
      </Link>
    </li>
  );
}
