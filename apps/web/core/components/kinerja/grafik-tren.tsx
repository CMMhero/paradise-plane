/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: dashboard KPI
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tren selesai, tepat waktu, dan yang baru lewat tenggat. Ketiganya jumlah tugas,
 * jadi satu sumbu. Hijau dan merah di sini memang berarti baik dan buruk; garis
 * "baru lewat tenggat" juga putus-putus supaya tidak hanya dibedakan warna.
 */

import { useTranslation } from "@plane/i18n";
import { LineChart } from "@plane/propel/charts/line-chart";
import { formatDay } from "@/components/dashboard-divisi/laporan";
import type { TKpiReport } from "@/services/kinerja.service";
import { EmptyNote } from "./bagian";

const SERIES = [
  // Langkah `*-strong` berganti sendiri antara tema terang dan gelap.
  { key: "completed", color: "var(--text-color-secondary)", dashed: false },
  { key: "on_time", color: "var(--border-success-strong)", dashed: false },
  { key: "became_overdue", color: "var(--border-danger-strong)", dashed: true },
] as const;

export function TrendChart({ trend }: { trend: TKpiReport["trend"] }) {
  const { t, currentLocale } = useTranslation();
  const isEmpty = trend.points.every((p) => p.completed === 0 && p.became_overdue === 0);
  if (isEmpty) return <EmptyNote>{t("kinerja.trend.empty")}</EmptyNote>;

  const data = trend.points.map((p) => ({ ...p, name: formatDay(p.start, currentLocale) }));

  return (
    <div className="rounded-card border border-subtle bg-layer-1 px-2 pt-4 pb-2">
      <LineChart
        className="h-[280px] w-full"
        margin={{ top: 8, right: 24, bottom: 8, left: 0 }}
        data={data}
        lines={SERIES.map((s) => ({
          key: s.key,
          label: t(`kinerja.trend.${s.key}`),
          stroke: s.color,
          fill: s.color,
          dashedLine: s.dashed,
          showDot: data.length <= 31,
          smoothCurves: false,
        }))}
        xAxis={{ key: "name" }}
        yAxis={{ key: "completed", allowDecimals: false }}
        legend={{ align: "center", verticalAlign: "bottom", layout: "horizontal" }}
      />
      <table className="sr-only">
        <caption>{t("kinerja.section.trend")}</caption>
        <thead>
          <tr>
            <th scope="col">{t(`kinerja.trend.bucket_${trend.bucket}`)}</th>
            {SERIES.map((s) => (
              <th key={s.key} scope="col">
                {t(`kinerja.trend.${s.key}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((p) => (
            <tr key={p.start}>
              <th scope="row">{p.name}</th>
              {SERIES.map((s) => (
                <td key={s.key}>{p[s.key]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
