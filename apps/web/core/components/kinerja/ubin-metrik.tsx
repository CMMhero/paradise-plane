/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: dashboard KPI
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu ubin per metrik: angkanya, lalu selisih terhadap periode sebelumnya.
 * Warna hanya di catatan selisih (baik/buruk); angkanya sendiri tetap netral.
 */

import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
import type { TKpiMetric, TKpiReport } from "@/services/kinerja.service";
import { formatDelta, formatMetric } from "./bagian";
import type { TKpiTone } from "./kinerja";
import { deltaTone, metricDelta } from "./kinerja";

const TONE_CLASS: Record<TKpiTone, string> = {
  good: "text-success-primary",
  bad: "text-danger-primary",
  neutral: "text-tertiary",
};

export function MetricTiles({ report, metrics }: { report: TKpiReport; metrics: TKpiMetric[] }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
      {metrics.map((metric) => (
        <MetricTile key={metric.key} metric={metric} report={report} />
      ))}
    </div>
  );
}

function MetricTile({ metric, report }: { metric: TKpiMetric; report: TKpiReport }) {
  const { t, currentLocale } = useTranslation();
  const delta = metricDelta(metric, report.values, report.previous);
  // Metrik sesaat dibandingkan dengan keadaannya di awal periode, bukan dengan periode sebelumnya.
  const against = metric.snapshot ? "start" : "prev";

  return (
    <div className="rounded-card border border-subtle bg-layer-1 px-4 py-3">
      <p className="text-24 leading-tight font-semibold text-primary">
        {formatMetric(metric, report.values[metric.key], t, currentLocale)}
      </p>
      <p className="mt-0.5 text-12 text-tertiary">{t(metric.label_key)}</p>
      {delta !== null && (
        <p className={cn("mt-1 text-11", TONE_CLASS[deltaTone(metric, delta)])}>
          {delta === 0
            ? t(`kinerja.delta.same_${against}`)
            : t(`kinerja.delta.vs_${against}`, { delta: formatDelta(metric, delta, t, currentLocale) })}
        </p>
      )}
    </div>
  );
}
