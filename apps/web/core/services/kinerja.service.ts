/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: dashboard KPI
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

/** Cermin `LINGKUP_SAH` di apps/api/plane/utils/kinerja.py. */
export type TKpiScopeKind = "saya" | "orang" | "departemen" | "divisi" | "organisasi";
export type TKpiScope = { kind: TKpiScopeKind; id?: string };

/** Cermin `PERIODE_SAH` di server. */
export const KPI_PERIODS = ["this_week", "this_month", "30d", "this_quarter", "custom"] as const;
export type TKpiPeriodKey = (typeof KPI_PERIODS)[number];
/** `start` dan `end` (YYYY-MM-DD, inklusif) hanya dipakai periode `custom`. */
export type TKpiPeriod = { key: TKpiPeriodKey; start?: string; end?: string };

/** Satu baris tabel metrik server (`METRIK`); halaman tidak punya daftar sendiri. */
export type TKpiMetric = {
  key: string;
  label_key: string;
  unit: "count" | "percent" | "days" | "hours";
  /** up = makin besar makin baik, down = makin kecil makin baik. */
  direction: "up" | "down" | "neutral";
  /** Keadaan saat ini, tidak mengikuti periode. */
  snapshot: boolean;
};

export type TKpiValues = Record<string, number | null>;

export type TKpiPerson = { id: string; display_name: string; avatar_url: string | null };

export type TKpiItem = {
  id: string;
  project_id: string;
  project_identifier: string;
  sequence_id: number;
  name: string;
  priority: string | null;
  target_date: string | null;
  completed_date: string | null;
  timing: "on_time" | "late" | "no_due_date" | null;
};

export type TKpiTrendPoint = { start: string; completed: number; on_time: number; became_overdue: number };

export type TKpiBreakdownRow = {
  id: string;
  code: string;
  name: string;
  people: number;
  values: TKpiValues;
};

export type TKpiReport = {
  generated_at: string;
  scope: { kind: Exclude<TKpiScopeKind, "saya">; id: string | null; name: string; people: number };
  /** Tanggal inklusif, YYYY-MM-DD, dalam hari kantor. */
  period: { key: TKpiPeriodKey; start: string; end: string; previous_start: string; previous_end: string };
  metrics: TKpiMetric[];
  values: TKpiValues;
  previous: TKpiValues;
  workload: { by_state_group: Record<string, number>; by_priority: Record<string, number> };
  trend: { bucket: "day" | "week"; points: TKpiTrendPoint[] };
  /** Lingkup kelompok saja: orang yang KPI-nya boleh dibuka pemanggil. */
  people: (TKpiPerson & { values: TKpiValues })[] | null;
  /** Per departemen (lingkup divisi) atau per divisi (lingkup organisasi). */
  breakdown: { kind: "departemen" | "divisi"; rows: TKpiBreakdownRow[] } | null;
  /** Lingkup satu orang saja, dan hanya tugas yang boleh dilihat pemanggil. */
  items: { overdue: TKpiItem[]; completed: TKpiItem[] } | null;
};

export type TKpiScopeOptions = {
  self: { id: string; display_name: string };
  organisation: boolean;
  divisions: { id: string; code: string; name: string }[];
  departments: { id: string; code: string; name: string; division_id: string }[];
  people: TKpiPerson[];
};

export class KinerjaService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getReport(workspaceSlug: string, scope: TKpiScope, period: TKpiPeriod): Promise<TKpiReport> {
    return this.get(`/api/workspaces/${workspaceSlug}/kinerja/`, {
      params: { lingkup: scope.kind, id: scope.id, periode: period.key, mulai: period.start, sampai: period.end },
    })
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }

  async getScopes(workspaceSlug: string): Promise<TKpiScopeOptions> {
    return this.get(`/api/workspaces/${workspaceSlug}/kinerja/lingkup/`)
      .then((res) => res?.data)
      .catch((e) => {
        throw e?.response?.data;
      });
  }
}
