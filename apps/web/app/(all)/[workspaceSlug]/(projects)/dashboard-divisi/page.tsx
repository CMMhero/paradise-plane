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
import { Button } from "@plane/propel/button";
import { TabNavigationItem, TabNavigationList } from "@plane/propel/tab-navigation";
import { Loader } from "@plane/ui";
// components
import { PageShell } from "@/components/common/page-shell";
import { PageHead } from "@/components/core/page-title";
import { SummaryView } from "@/components/dashboard-divisi/tampilan-ringkas";
import { ReportView } from "@/components/dashboard-divisi/tampilan-laporan";
import { DetailView } from "@/components/dashboard-divisi/tampilan-rinci";
// hooks
import { useUser } from "@/hooks/store/user";
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

/**
 * Jam pembaruan dalam zona waktu profil pengguna (sama dengan Beranda dan
 * Profil), bukan zona peramban. Zona yang tidak dikenal Intl jatuh ke peramban.
 */
function formatUpdatedAt(iso: string, locale: string, timeZone: string | undefined): string {
  const options: Intl.DateTimeFormatOptions = { dateStyle: "medium", timeStyle: "short" };
  try {
    return new Date(iso).toLocaleString(locale, { ...options, timeZone });
  } catch {
    return new Date(iso).toLocaleString(locale, options);
  }
}

function DivisionDashboardPage() {
  const { t, currentLocale } = useTranslation();
  const { data: currentUser } = useUser();
  // Jam kerja berasal dari Time Tracking; disembunyikan bersama fiturnya.
  const isTimeTrackingEnabled = isParadiseFeatureEnabled("timeTracking");
  const { workspaceSlug } = useParams();
  const { storedValue, setValue: setMode } = useLocalStorage<TMode>(MODE_STORAGE_KEY, "ringkas");
  const mode: TMode = storedValue && MODES.includes(storedValue) ? storedValue : "ringkas";
  // Gagal memuat -> `data` tetap kosong dan halaman menampilkan pesan gagal.
  const { data, isLoading, mutate } = useSWR(
    workspaceSlug ? ["DIVISION_DASHBOARD", workspaceSlug] : null,
    workspaceSlug ? () => dashboardService.getDashboard(workspaceSlug) : null,
    { revalidateOnFocus: false }
  );

  if (!workspaceSlug) return <></>;

  const updatedAt = data ? formatUpdatedAt(data.generated_at, currentLocale, currentUser?.user_timezone) : "";

  return (
    <>
      <PageHead title={t("division_dashboard_ui.title")} />
      <PageShell width="wide">
        <PageShell.Header
          title={t("division_dashboard_ui.title")}
          description={
            <>
              {data && <p>{t("division_dashboard_ui.updated", { time: updatedAt })}</p>}
              {data?.leader_created_only && <p>{t("persetujuan_p29.dashboard_leader_note")}</p>}
            </>
          }
          actions={
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
          }
        />

        {mode === "laporan" ? (
          <ReportView workspaceSlug={workspaceSlug} />
        ) : isLoading ? (
          <Loader className="flex flex-col gap-4">
            <span className="sr-only">{t("common.loading")}</span>
            <Loader.Item height="72px" />
            <Loader.Item height="200px" />
          </Loader>
        ) : !data ? (
          <div role="alert" className="flex flex-wrap items-center gap-3">
            <p className="text-13 text-tertiary">{t("division_dashboard_ui.load_failed")}</p>
            <Button variant="secondary" size="base" onClick={() => void mutate()}>
              {t("common.retry")}
            </Button>
          </div>
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
      </PageShell>
    </>
  );
}

export default observer(DivisionDashboardPage);
