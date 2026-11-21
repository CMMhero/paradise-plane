/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: dashboard KPI
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu halaman untuk semua jenjang. Lingkup (KPI siapa) tinggal di query string
 * supaya tautannya bisa dibagikan dan tombol kembali peramban bekerja; periode
 * diingat per peramban. Server yang memutuskan lingkup mana yang boleh dibuka.
 */

import { observer } from "mobx-react";
import { useParams, useSearchParams } from "react-router";
import useSWR from "swr";
import { isParadiseFeatureEnabled } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { Avatar, Loader } from "@plane/ui";
import { cn, getFileURL } from "@plane/utils";
// components
import { PageShell } from "@/components/common/page-shell";
import { PageHead } from "@/components/core/page-title";
import { formatDay } from "@/components/dashboard-divisi/laporan";
import { Section } from "@/components/kinerja/bagian";
import { Workload } from "@/components/kinerja/beban-kerja";
import { ItemList } from "@/components/kinerja/daftar-tugas";
import { TrendChart } from "@/components/kinerja/grafik-tren";
import { sanitizePeriod, scopeFromParams, scopeKey, scopeToParams } from "@/components/kinerja/kinerja";
import { PeriodPicker, ScopePicker } from "@/components/kinerja/pemilih";
import { MetricTable } from "@/components/kinerja/tabel-metrik";
import { MetricTiles } from "@/components/kinerja/ubin-metrik";
// hooks
import { useAturan } from "@/hooks/use-aturan";
import useLocalStorage from "@/hooks/use-local-storage";
// services
import { KinerjaService } from "@/services/kinerja.service";
import type { TKpiPeriod, TKpiReport, TKpiScope } from "@/services/kinerja.service";

const kinerjaService = new KinerjaService();
const PERIOD_STORAGE_KEY = "paradise:kinerja:periode";

/** Hari ini menurut peramban, YYYY-MM-DD; hanya dipakai sebagai isi awal rentang khusus. */
const localToday = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
};

function KinerjaPage() {
  const { t, currentLocale } = useTranslation();
  const { workspaceSlug } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const scope = scopeFromParams(searchParams);
  // Nilai awal null: kosong = belum pernah memilih, jadi periode bawaan dari aturan
  // God Mode. Pilihan tersimpan selalu menang dan tidak pernah ditimpa aturan.
  const { storedValue, setValue: setPeriod } = useLocalStorage<TKpiPeriod | null>(PERIOD_STORAGE_KEY, null);
  const { get } = useAturan();
  const period = sanitizePeriod(storedValue, get("KPI_DEFAULT_PERIOD"));
  // Jam kerja berasal dari Time Tracking; disembunyikan bersama fiturnya.
  const isTimeTrackingEnabled = isParadiseFeatureEnabled("timeTracking");

  const { data: scopes } = useSWR(
    workspaceSlug ? ["KINERJA_LINGKUP", workspaceSlug] : null,
    workspaceSlug ? () => kinerjaService.getScopes(workspaceSlug) : null,
    { revalidateOnFocus: false }
  );
  const { data, error, isLoading, mutate } = useSWR(
    workspaceSlug ? ["KINERJA", workspaceSlug, scopeKey(scope), period.key, period.start, period.end] : null,
    workspaceSlug ? () => kinerjaService.getReport(workspaceSlug, scope, period) : null,
    { revalidateOnFocus: false, keepPreviousData: true, shouldRetryOnError: false }
  );

  if (!workspaceSlug) return <></>;

  const openScope = (next: TKpiScope) => setSearchParams(scopeToParams(next));
  const scopeName = data ? data.scope.name || t("kinerja.scope.organisation") : "";

  return (
    <>
      <PageHead title={t("kinerja.title")} />
      <PageShell width="wide">
        <PageShell.Header
          title={scopeName ? t("kinerja.heading", { name: scopeName }) : t("kinerja.title")}
          description={
            data && (
              <p>
                {t("kinerja.period.range", {
                  start: formatDay(data.period.start, currentLocale),
                  end: formatDay(data.period.end, currentLocale, true),
                })}
                {data.scope.kind !== "orang" && ` · ${t("kinerja.people_count", { count: data.scope.people })}`}
              </p>
            )
          }
          actions={
            <>
              <ScopePicker scope={scope} options={scopes} currentName={scopeName} onChange={openScope} />
              <PeriodPicker period={period} onChange={setPeriod} today={localToday()} />
            </>
          }
        />

        {error && !isLoading ? (
          <div role="alert" className="flex flex-wrap items-center gap-3">
            <p className="text-13 text-tertiary">{t("kinerja.load_failed")}</p>
            <Button variant="secondary" size="base" onClick={() => void mutate()}>
              {t("common.retry")}
            </Button>
            {scope.kind !== "saya" && (
              <Button variant="link" size="base" onClick={() => openScope({ kind: "saya" })}>
                {t("kinerja.back_to_mine")}
              </Button>
            )}
          </div>
        ) : !data ? (
          <Loader className="flex flex-col gap-4">
            <span className="sr-only">{t("common.loading")}</span>
            <Loader.Item height="160px" />
            <Loader.Item height="280px" />
          </Loader>
        ) : (
          <Report
            workspaceSlug={workspaceSlug}
            report={data}
            isStale={isLoading}
            isTimeTrackingEnabled={isTimeTrackingEnabled}
            onOpen={openScope}
          />
        )}
      </PageShell>
    </>
  );
}

type TReportProps = {
  workspaceSlug: string;
  report: TKpiReport;
  isStale: boolean;
  isTimeTrackingEnabled: boolean;
  onOpen: (scope: TKpiScope) => void;
};

function Report({ workspaceSlug, report, isStale, isTimeTrackingEnabled, onOpen }: TReportProps) {
  const { t } = useTranslation();
  const metrics = report.metrics.filter((m) => isTimeTrackingEnabled || m.unit !== "hours");
  const { people, breakdown, items } = report;

  return (
    <div className={cn("flex flex-col gap-6 transition-opacity", isStale && "opacity-60")}>
      <MetricTiles report={report} metrics={metrics} />

      <Section
        id="kinerja-tren"
        title={t("kinerja.section.trend")}
        hint={t(`kinerja.trend.per_${report.trend.bucket}`)}
      >
        <TrendChart trend={report.trend} />
      </Section>

      <Section id="kinerja-beban" title={t("kinerja.section.workload")} hint={t("kinerja.workload.hint")}>
        <Workload workload={report.workload} />
      </Section>

      {breakdown && breakdown.rows.length > 0 && (
        <Section id="kinerja-rincian" title={t(`kinerja.section.breakdown_${breakdown.kind}`)}>
          <MetricTable
            caption={t(`kinerja.section.breakdown_${breakdown.kind}`)}
            nameHeader={t(`kinerja.scope.${breakdown.kind === "divisi" ? "division" : "department"}`)}
            rows={breakdown.rows}
            metrics={metrics}
            nameOf={(row) => row.name}
            renderName={(row) => (
              <>
                <span className="truncate">{row.name}</span>
                <span className="shrink-0 text-11 text-tertiary">
                  {t("kinerja.people_count", { count: row.people })}
                </span>
              </>
            )}
            onOpen={(row) => onOpen({ kind: breakdown.kind, id: row.id })}
          />
        </Section>
      )}

      {people && (
        <Section id="kinerja-orang" title={t("kinerja.section.people")} hint={t("kinerja.people_hint")}>
          <MetricTable
            caption={t("kinerja.section.people")}
            nameHeader={t("kinerja.scope.person")}
            rows={people}
            metrics={metrics}
            nameOf={(row) => row.display_name}
            renderName={(row) => (
              <>
                <Avatar name={row.display_name} src={getFileURL(row.avatar_url ?? "")} size="sm" />
                <span className="truncate">{row.display_name}</span>
              </>
            )}
            onOpen={(row) => onOpen({ kind: "orang", id: row.id })}
            initialSort={{ key: "completed", descending: true }}
          />
        </Section>
      )}

      {items && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Section id="kinerja-terlambat" title={t("kinerja.section.overdue_items")}>
            <ItemList
              workspaceSlug={workspaceSlug}
              items={items.overdue}
              total={report.values.overdue}
              emptyText={t("kinerja.items.no_overdue")}
            />
          </Section>
          <Section id="kinerja-selesai" title={t("kinerja.section.completed_items")}>
            <ItemList
              workspaceSlug={workspaceSlug}
              items={items.completed}
              total={report.values.completed}
              emptyText={t("kinerja.items.no_completed")}
            />
          </Section>
        </div>
      )}

      <p className="text-11 text-tertiary">{t("kinerja.help")}</p>
    </div>
  );
}

export default observer(KinerjaPage);
