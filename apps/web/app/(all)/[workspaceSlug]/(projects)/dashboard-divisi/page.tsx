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
import { PageHead } from "@/components/core/page-title";
// services
import { WorkspaceDashboardService, type TDivisionDashboard } from "@/services/workspace_dashboard.service";

const dashboardService = new WorkspaceDashboardService();

const formatMinutes = (minutes: number): string => {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h > 0 && m > 0) return `${h}j ${m}m`;
  if (h > 0) return `${h}j`;
  return `${m}m`;
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
      <PageHead title="Dashboard Divisi" />

      {isLoading ? (
        <p className="text-sm text-tertiary">Memuat…</p>
      ) : !data ? (
        <p className="text-sm text-tertiary">Gagal memuat dashboard. Coba muat ulang halaman.</p>
      ) : (
        <div className="flex flex-col gap-5">
          {/* Ringkasan total */}
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-lg font-semibold text-primary">Ringkasan Divisi</h2>
            <a
              href={dashboardService.worklogExportUrl(workspaceSlug)}
              className="text-xs flex items-center gap-1.5 rounded border border-subtle px-2.5 py-1.5 font-medium text-secondary hover:bg-layer-2"
            >
              <Download className="size-3.5" /> Unduh Laporan Waktu (CSV)
            </a>
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
            <StatCard label="Divisi" value={String(data.totals.projects)} icon={<FolderKanban className="size-5" />} />
            <StatCard
              label="Total Tugas"
              value={String(data.totals.issues_total)}
              icon={<ListTodo className="size-5" />}
            />
            <StatCard
              label="Berjalan"
              value={String(data.totals.issues_open)}
              icon={<ListTodo className="text-amber-500 size-5" />}
            />
            <StatCard
              label="Terlambat"
              value={String(data.totals.issues_overdue)}
              icon={<AlertTriangle className="text-red-500 size-5" />}
            />
            <StatCard
              label="Selesai"
              value={String(data.totals.issues_completed)}
              icon={<CheckCircle2 className="text-green-600 size-5" />}
            />
            <StatCard
              label="Jam Kerja (bulan ini)"
              value={formatMinutes(data.totals.worklog_minutes_month)}
              icon={<Clock className="size-5" />}
            />
          </div>

          {/* Tabel per divisi */}
          <div className="overflow-x-auto rounded-md border border-subtle gulir-berpenanda">
            <table className="text-sm w-full min-w-[640px] text-left">
              <thead>
                <tr className="text-xs border-b border-subtle bg-layer-2 text-tertiary">
                  <th className="px-3 py-2 font-medium">Divisi</th>
                  <th className="px-3 py-2 text-right font-medium">Anggota</th>
                  <th className="px-3 py-2 text-right font-medium">Total</th>
                  <th className="px-3 py-2 text-right font-medium">Berjalan</th>
                  <th className="px-3 py-2 text-right font-medium">Terlambat</th>
                  <th className="px-3 py-2 text-right font-medium">Selesai</th>
                  <th className="px-3 py-2 text-right font-medium">Jam (bulan ini)</th>
                  <th className="px-3 py-2 text-right font-medium">Jam (total)</th>
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
                    <td className="px-3 py-2 text-right text-secondary">{formatMinutes(p.worklog_minutes_month)}</td>
                    <td className="px-3 py-2 text-right text-secondary">{formatMinutes(p.worklog_minutes_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-xs text-tertiary">
            Hanya divisi yang kamu ikuti yang tampil di sini. Laporan CSV berisi seluruh catatan waktu dari
            divisi-divisi tersebut.
          </p>
        </div>
      )}
    </div>
  );
}

export default observer(DivisionDashboardPage);
