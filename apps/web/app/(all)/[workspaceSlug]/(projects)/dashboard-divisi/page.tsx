/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Dashboard Divisi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tiga mode: "Ringkas" (KEP-60) untuk pimpinan yang hanya perlu tahu bagian mana
 * yang bermasalah, "Rinci" untuk angka lengkap per departemen, "Laporan" (KEP-62)
 * untuk tugas yang selesai dalam satu periode, lengkap dengan judulnya. Semua orang
 * mulai di Ringkas; pilihan terakhir diingat per peramban.
 */

import { observer } from "mobx-react";
import { useParams } from "react-router";
import useSWR from "swr";
import { isParadiseFeatureEnabled } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { TabNavigationItem, TabNavigationList } from "@plane/propel/tab-navigation";
// components
import { PageHead } from "@/components/core/page-title";
import { SummaryView } from "@/components/dashboard-divisi/tampilan-ringkas";
import { ReportView } from "@/components/dashboard-divisi/tampilan-laporan";
import { DetailView } from "@/components/dashboard-divisi/tampilan-rinci";
// hooks
import useLocalStorage from "@/hooks/use-local-storage";
// services
import { WorkspaceDashboardService } from "@/services/workspace_dashboard.service";

const dashboardService = new WorkspaceDashboardService();

type TMode = "ringkas" | "rinci" | "laporan";
const MODE_STORAGE_KEY = "paradise:dashboard-divisi:mode";
const MODES: TMode[] = ["ringkas", "rinci", "laporan"];
const MODE_LABEL: Record<TMode, string> = {
  ringkas: "division_dashboard_ui.mode_summary",
  rinci: "division_dashboard_ui.mode_detail",
  laporan: "division_dashboard_ui.mode_report",
};

function DivisionDashboardPage() {
  const { t } = useTranslation();
  // Jam kerja berasal dari Time Tracking; disembunyikan bersama fiturnya.
  const isTimeTrackingEnabled = isParadiseFeatureEnabled("timeTracking");
  const { workspaceSlug } = useParams();
  const { storedValue, setValue: setMode } = useLocalStorage<TMode>(MODE_STORAGE_KEY, "ringkas");
  const mode: TMode = storedValue && MODES.includes(storedValue) ? storedValue : "ringkas";
  // Gagal memuat -> `data` tetap kosong dan halaman menampilkan pesan gagal.
  const { data, isLoading } = useSWR(
    workspaceSlug ? ["DIVISION_DASHBOARD", workspaceSlug] : null,
    workspaceSlug ? () => dashboardService.getDashboard(workspaceSlug) : null,
    { revalidateOnFocus: false }
  );

  if (!workspaceSlug) return <></>;

  const updatedAt = data
    ? new Date(data.generated_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })
    : "";

  return (
    <div className="h-full w-full overflow-y-auto px-6 py-5">
      <PageHead title={t("division_dashboard_ui.title")} />
      <div className="mx-auto flex max-w-[1100px] flex-col gap-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-20 font-semibold text-primary">{t("division_dashboard_ui.title")}</h1>
            {data && <p className="text-12 text-tertiary">{t("division_dashboard_ui.updated", { time: updatedAt })}</p>}
          </div>
          <fieldset aria-label={t("division_dashboard_ui.mode_label")} className="m-0 border-0 p-0">
            <TabNavigationList>
              {MODES.map((m) => (
                <button
                  key={m}
                  type="button"
                  aria-label={t(MODE_LABEL[m])}
                  aria-pressed={mode === m}
                  onClick={() => setMode(m)}
                  className="rounded-item outline-none focus-visible:ring-2 focus-visible:ring-accent-strong"
                >
                  <TabNavigationItem isActive={mode === m}>
                    <span>{t(MODE_LABEL[m])}</span>
                  </TabNavigationItem>
                </button>
              ))}
            </TabNavigationList>
          </fieldset>
        </div>

        {mode === "laporan" ? (
          <ReportView workspaceSlug={workspaceSlug} />
        ) : isLoading ? (
          <p className="text-13 text-tertiary">{t("chat_ui.loading")}</p>
        ) : !data ? (
          <p className="text-13 text-tertiary">{t("division_dashboard_ui.load_failed")}</p>
        ) : mode === "ringkas" ? (
          <SummaryView workspaceSlug={workspaceSlug} data={data} onShowDetail={() => setMode("rinci")} />
        ) : (
          <DetailView
            workspaceSlug={workspaceSlug}
            data={data}
            isTimeTrackingEnabled={isTimeTrackingEnabled}
            csvUrl={dashboardService.worklogExportUrl(workspaceSlug)}
          />
        )}
      </div>
    </div>
  );
}

export default observer(DivisionDashboardPage);
