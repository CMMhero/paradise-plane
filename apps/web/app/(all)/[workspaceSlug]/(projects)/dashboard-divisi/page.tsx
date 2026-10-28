/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Dashboard Divisi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
import { AlertTriangle, CheckCircle2, Clock, Download, FolderKanban, ListTodo } from "lucide-react";
// components
import { useTranslation } from "@plane/i18n";
import { PageHead } from "@/components/core/page-title";
// services
import { WorkspaceDashboardService, type TDivisionDashboard } from "@/services/workspace_dashboard.service";

const dashboardService = new WorkspaceDashboardService();

const formatMinutes = (minutes: number, t: (key: string, params?: Record<string, unknown>) => string): string => {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h > 0 && m > 0) return t("division_dashboard_ui.duration_hm", { h, m });
  if (h > 0) return t("division_dashboard_ui.duration_h", { h });
  return t("division_dashboard_ui.duration_m", { m });
};

type TStatCard = { label: string; value: string; icon: React.ReactNode };

function StatCard({ label, value, icon }: TStatCard) {
  return (
    <div className="flex items-center gap-3 rounded-md border border-subtle bg-layer-1 px-4 py-3">
      <div className="shrink-0 text-secondary">{icon}</div>
      <div className="min-w-0">
        <p className="text-lg font-semibold text-primary">{value}</p>
        <p className="text-xs truncate text-tertiary">{label}</p>
      </div>
    </div>
  );
}

function DivisionDashboardPage() {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const [data, setData] = useState<TDivisionDashboard | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchDashboard = useCallback(async () => {
    if (!workspaceSlug) return;
    try {
      const res = await dashboardService.getDashboard(workspaceSlug);
      setData(res);
    } catch {
      // biarkan null → tampil pesan gagal
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug]);

  useEffect(() => {
    void fetchDashboard();
  }, [fetchDashboard]);

  if (!workspaceSlug) return <></>;

  return (
    <div className="h-full w-full overflow-y-auto px-6 py-5">
      <PageHead title={t("division_dashboard_ui.title")} />

      {isLoading ? (
        <p className="text-sm text-tertiary">{t("chat_ui.loading")}</p>
      ) : !data ? (
        <p className="text-sm text-tertiary">{t("division_dashboard_ui.load_failed")}</p>
      ) : (
        <div className="flex flex-col gap-5">
          {/* Ringkasan total */}
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-lg font-semibold text-primary">{t("division_dashboard_ui.summary")}</h2>
            <a
              href={dashboardService.worklogExportUrl(workspaceSlug)}
              className="text-xs flex items-center gap-1.5 rounded border border-subtle px-2.5 py-1.5 font-medium text-secondary hover:bg-layer-2"
            >
              <Download className="size-3.5" /> {t("division_dashboard_ui.download_csv")}
            </a>
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
            <StatCard
              label={t("division_dashboard_ui.divisions")}
              value={String(data.totals.projects)}
              icon={<FolderKanban className="size-5" />}
            />
            <StatCard
              label={t("division_dashboard_ui.total_tasks")}
              value={String(data.totals.issues_total)}
              icon={<ListTodo className="size-5" />}
            />
            <StatCard
              label={t("division_dashboard_ui.in_progress")}
              value={String(data.totals.issues_open)}
              icon={<ListTodo className="text-amber-500 size-5" />}
            />
            <StatCard
              label={t("division_dashboard_ui.overdue")}
              value={String(data.totals.issues_overdue)}
              icon={<AlertTriangle className="text-red-500 size-5" />}
            />
            <StatCard
              label={t("division_dashboard_ui.done")}
              value={String(data.totals.issues_completed)}
              icon={<CheckCircle2 className="text-green-600 size-5" />}
            />
            <StatCard
              label={t("division_dashboard_ui.hours_month_long")}
              value={formatMinutes(data.totals.worklog_minutes_month, t)}
              icon={<Clock className="size-5" />}
            />
          </div>

          {/* Tabel per divisi */}
          <div className="overflow-x-auto rounded-md border border-subtle gulir-berpenanda">
            <table className="text-sm w-full min-w-[640px] text-left">
              <thead>
                <tr className="text-xs border-b border-subtle bg-layer-2 text-tertiary">
                  <th className="px-3 py-2 font-medium">{t("division_dashboard_ui.col_division")}</th>
                  <th className="px-3 py-2 text-right font-medium">{t("division_dashboard_ui.col_members")}</th>
                  <th className="px-3 py-2 text-right font-medium">{t("division_dashboard_ui.col_total")}</th>
                  <th className="px-3 py-2 text-right font-medium">{t("division_dashboard_ui.in_progress")}</th>
                  <th className="px-3 py-2 text-right font-medium">{t("division_dashboard_ui.overdue")}</th>
                  <th className="px-3 py-2 text-right font-medium">{t("division_dashboard_ui.done")}</th>
                  <th className="px-3 py-2 text-right font-medium">{t("division_dashboard_ui.hours_month")}</th>
                  <th className="px-3 py-2 text-right font-medium">{t("division_dashboard_ui.hours_total")}</th>
                </tr>
              </thead>
              <tbody>
                {data.projects.map((p) => (
                  <tr key={p.id} className="border-b border-subtle last:border-0 hover:bg-layer-2">
                    <td className="px-3 py-2">
                      <span className="font-medium text-primary">{p.name}</span>{" "}
                      <span className="text-xs text-tertiary">({p.identifier})</span>
                    </td>
                    <td className="px-3 py-2 text-right text-secondary">{p.members}</td>
                    <td className="px-3 py-2 text-right text-secondary">{p.issues_total}</td>
                    <td className="px-3 py-2 text-right text-secondary">{p.issues_open}</td>
                    <td
                      className={`px-3 py-2 text-right ${p.issues_overdue > 0 ? "text-red-500 font-semibold" : "text-secondary"}`}
                    >
                      {p.issues_overdue}
                    </td>
                    <td className="px-3 py-2 text-right text-secondary">{p.issues_completed}</td>
                    <td className="px-3 py-2 text-right text-secondary">{formatMinutes(p.worklog_minutes_month, t)}</td>
                    <td className="px-3 py-2 text-right text-secondary">{formatMinutes(p.worklog_minutes_total, t)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-xs text-tertiary">{t("division_dashboard_ui.footer_note")}</p>
        </div>
      )}
    </div>
  );
}

export default observer(DivisionDashboardPage);
