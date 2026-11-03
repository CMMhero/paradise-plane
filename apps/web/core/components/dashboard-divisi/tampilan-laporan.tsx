/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: laporan tugas selesai (KEP-62)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * "Apa saja yang selesai dalam periode ini?" untuk direktur: empat angka,
 * selesai per divisi, lalu judul tugasnya per divisi > project. Mode Ringkas
 * menjawab "mana yang bermasalah"; laporan ini menjawab "apa yang sudah jadi".
 */

import type { ReactNode } from "react";
import Link from "next/link";
import useSWR from "swr";
import { Download } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { getButtonStyling } from "@plane/propel/button";
import { cn, generateWorkItemLink } from "@plane/utils";
import useLocalStorage from "@/hooks/use-local-storage";
import type {
  TCompletedItem,
  TCompletedReport,
  TReportDivision,
  TReportPeriod,
  TReportProject,
  TReportTiming,
} from "@/services/workspace_dashboard.service";
import { REPORT_PERIODS, WorkspaceDashboardService } from "@/services/workspace_dashboard.service";
import { TrendNote, divisionLabel, formatPercent } from "./bagian";
import { barPercent, completedDelta, formatDay, itemsByProject } from "./laporan";
import { trendTone } from "./ringkasan";

const dashboardService = new WorkspaceDashboardService();
const PERIOD_STORAGE_KEY = "paradise:dashboard-divisi:periode-laporan";

const TIMING_CLASS: Record<TReportTiming, string> = {
  on_time: "bg-success-subtle text-success-primary",
  late: "bg-danger-subtle text-danger-primary",
  no_due_date: "bg-layer-3 text-tertiary",
};

const isPeriod = (value: unknown): value is TReportPeriod => REPORT_PERIODS.includes(value as TReportPeriod);

export function ReportView({ workspaceSlug }: { workspaceSlug: string }) {
  const { t } = useTranslation();
  const { storedValue, setValue: setPeriod } = useLocalStorage<TReportPeriod>(PERIOD_STORAGE_KEY, "7d");
  const period: TReportPeriod = isPeriod(storedValue) ? storedValue : "7d";
  const { data, isLoading } = useSWR(
    ["DIVISION_DASHBOARD_REPORT", workspaceSlug, period],
    () => dashboardService.getCompletedReport(workspaceSlug, period),
    { revalidateOnFocus: false, keepPreviousData: true }
  );

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <fieldset
          aria-label={t("division_dashboard_ui.report_period_label")}
          className="m-0 flex flex-wrap overflow-hidden rounded-button border border-subtle p-0 text-12"
        >
          {REPORT_PERIODS.map((p) => (
            <button
              key={p}
              type="button"
              aria-pressed={period === p}
              onClick={() => setPeriod(p)}
              className={cn(
                "px-3 py-1.5 font-medium transition-colors",
                period === p
                  ? "bg-layer-transparent-active text-primary"
                  : "text-tertiary hover:bg-layer-transparent-hover hover:text-secondary"
              )}
            >
              {t(`division_dashboard_ui.report_period_${p}`)}
            </button>
          ))}
        </fieldset>
        <div className="flex items-center gap-3">
          {data && (
            <span className="text-12 text-tertiary">
              {t("division_dashboard_ui.report_range", {
                start: formatDay(data.period.start),
                end: formatDay(data.period.end, true),
              })}
            </span>
          )}
          <a
            href={dashboardService.completedReportCsvUrl(workspaceSlug, period)}
            className={getButtonStyling("secondary", "lg")}
          >
            <Download className="size-4" /> {t("division_dashboard_ui.report_download_csv")}
          </a>
        </div>
      </div>

      {!data ? (
        <p className="text-13 text-tertiary">
          {t(isLoading ? "chat_ui.loading" : "division_dashboard_ui.load_failed")}
        </p>
      ) : (
        <div className={cn("flex flex-col gap-6 transition-opacity", isLoading && "opacity-60")}>
          <ReportKpis report={data} />
          {data.totals.completed === 0 ? (
            <p className="rounded-card border border-subtle px-4 py-3 text-13 text-tertiary">
              {t("division_dashboard_ui.report_empty")}
            </p>
          ) : (
            <>
              <DivisionBars divisions={data.divisions} />
              <CompletedList workspaceSlug={workspaceSlug} report={data} />
            </>
          )}
        </div>
      )}
    </div>
  );
}

function ReportKpis({ report }: { report: TCompletedReport }) {
  const { t } = useTranslation();
  const { totals } = report;
  const delta = completedDelta(report);
  const withDueDate = totals.on_time + totals.late;

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Kpi value={String(totals.completed)} label={t("division_dashboard_ui.report_kpi_completed")}>
        <TrendNote delta={delta} tone={trendTone(delta, true)} against="period" />
      </Kpi>
      <Kpi value={formatPercent(totals.on_time_rate)} label={t("division_dashboard_ui.report_kpi_on_time")}>
        {withDueDate > 0 && (
          <p className="mt-1 text-11 text-tertiary">
            {t("division_dashboard_ui.report_on_time_hint", { on_time: totals.on_time, total: withDueDate })}
          </p>
        )}
      </Kpi>
      <Kpi value={String(totals.late)} label={t("division_dashboard_ui.report_kpi_late")} isAlert={totals.late > 0} />
      <Kpi value={String(totals.created)} label={t("division_dashboard_ui.report_kpi_created")} />
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

function DivisionBars({ divisions }: { divisions: TReportDivision[] }) {
  const { t } = useTranslation();
  return (
    <section aria-labelledby="laporan-divisi" className="flex flex-col gap-3">
      <h2 id="laporan-divisi" className="text-14 font-semibold text-primary">
        {t("division_dashboard_ui.report_section_divisions")}
      </h2>
      <ul className="flex flex-col gap-2.5 rounded-card border border-subtle bg-layer-1 px-4 py-3">
        {divisions.map((d) => (
          <li key={d.id ?? "tanpa-divisi"} className="grid grid-cols-[minmax(0,10rem)_1fr_auto] items-center gap-3">
            <span className="truncate text-13 text-primary" title={divisionLabel(d.name, t)}>
              {divisionLabel(d.name, t)}
            </span>
            <div aria-hidden className="h-2 overflow-hidden rounded-control bg-layer-3">
              <div
                className="h-full rounded-control bg-accent-primary"
                style={{ width: `${barPercent(d, divisions)}%` }}
              />
            </div>
            <span className="text-12 whitespace-nowrap text-tertiary">
              <span className="font-semibold text-primary">{d.completed}</span>
              {" · "}
              {t("division_dashboard_ui.report_on_time_short", { pct: formatPercent(d.on_time_rate) })}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function CompletedList({ workspaceSlug, report }: { workspaceSlug: string; report: TCompletedReport }) {
  const { t } = useTranslation();
  const byProject = itemsByProject(report.items);

  return (
    <section aria-labelledby="laporan-tugas" className="flex flex-col gap-3">
      <h2 id="laporan-tugas" className="text-14 font-semibold text-primary">
        {t("division_dashboard_ui.report_section_items")}
      </h2>
      {report.divisions.map((d) => (
        <details key={d.id ?? "tanpa-divisi"} open className="group rounded-card border border-subtle bg-layer-1">
          <summary className="flex cursor-pointer items-center justify-between gap-2 px-4 py-2.5 text-13 font-semibold text-primary hover:bg-layer-2">
            <span className="truncate">{divisionLabel(d.name, t)}</span>
            <span className="font-normal shrink-0 text-12 text-tertiary">
              {t("division_dashboard_ui.report_items_count", { count: d.completed })}
            </span>
          </summary>
          <div className="flex flex-col gap-3 border-t border-subtle px-4 py-3">
            {d.projects.map((p) => (
              <ProjectItems key={p.id} workspaceSlug={workspaceSlug} project={p} items={byProject.get(p.id) ?? []} />
            ))}
          </div>
        </details>
      ))}
      {report.items_truncated && (
        <p className="text-12 text-tertiary">
          {t("division_dashboard_ui.report_truncated", { shown: report.items.length, total: report.totals.completed })}
        </p>
      )}
    </section>
  );
}

function ProjectItems({
  workspaceSlug,
  project,
  items,
}: {
  workspaceSlug: string;
  project: TReportProject;
  items: TCompletedItem[];
}) {
  const { t } = useTranslation();
  const where = project.department ? `${project.name} (${project.department.code})` : project.name;
  // Daftar dibatasi server: project lama bisa punya angka tanpa baris yang terkirim.
  const hidden = project.completed - items.length;

  return (
    <div>
      <p className="mb-1 text-12 font-medium text-secondary">
        {where} <span className="font-normal text-tertiary">· {project.completed}</span>
      </p>
      <ul className="divide-y divide-subtle">
        {items.map((item) => (
          <CompletedRow key={item.id} workspaceSlug={workspaceSlug} item={item} />
        ))}
      </ul>
      {hidden > 0 && (
        <p className="pt-1 text-11 text-tertiary">{t("division_dashboard_ui.report_more", { count: hidden })}</p>
      )}
    </div>
  );
}

function CompletedRow({ workspaceSlug, item }: { workspaceSlug: string; item: TCompletedItem }) {
  const { t } = useTranslation();
  const href = generateWorkItemLink({
    workspaceSlug,
    projectId: item.project_id,
    issueId: item.id,
    projectIdentifier: item.project_identifier,
    sequenceId: item.sequence_id,
  });
  const assignees =
    item.assignees.length > 0 ? item.assignees.join(", ") : t("division_dashboard_ui.report_no_assignee");

  return (
    <li>
      <Link href={href} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-1.5 hover:bg-layer-2">
        <span className="font-mono w-20 shrink-0 text-11 text-tertiary">
          {item.project_identifier}-{item.sequence_id}
        </span>
        <span className="min-w-0 flex-1 truncate text-13 text-primary" title={item.name}>
          {item.name}
        </span>
        <span className="max-w-[12rem] truncate text-12 text-tertiary" title={assignees}>
          {assignees}
        </span>
        <span className="w-16 shrink-0 text-right text-12 text-tertiary">{formatDay(item.completed_date)}</span>
        <span
          className={cn(
            "inline-flex shrink-0 items-center rounded-control px-2 py-0.5 text-11 font-semibold whitespace-nowrap",
            TIMING_CLASS[item.timing]
          )}
        >
          {t(`division_dashboard_ui.report_timing_${item.timing}`)}
        </span>
      </Link>
    </li>
  );
}
