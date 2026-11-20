/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: dashboard KPI
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Pemilih lingkup (KPI siapa) dan pemilih periode. Isi pemilih lingkup datang
 * dari server, jadi orang tidak pernah ditawari lingkup yang akan ditolak.
 */

import type { ReactNode } from "react";
import { Building2, Factory, Network, User, Users } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Avatar, CustomSearchSelect } from "@plane/ui";
import { cn, getFileURL } from "@plane/utils";
import type { TKpiPeriod, TKpiPeriodKey, TKpiScope, TKpiScopeOptions } from "@/services/kinerja.service";
import { KPI_PERIODS } from "@/services/kinerja.service";
import { scopeFromKey, scopeKey } from "./kinerja";

type TScopeOption = { value: string; query: string; content: ReactNode };

const option = (scope: TKpiScope, name: string, kind: string, icon: ReactNode): TScopeOption => ({
  value: scopeKey(scope),
  query: `${name} ${kind}`,
  content: (
    <div className="flex min-w-0 items-center gap-2">
      {icon}
      <span className="truncate">{name}</span>
      <span className="shrink-0 text-11 text-tertiary">{kind}</span>
    </div>
  ),
});

type TScopePickerProps = {
  scope: TKpiScope;
  options: TKpiScopeOptions | undefined;
  /** Nama lingkup yang sedang dibuka, dari laporan (pemilih bisa belum termuat). */
  currentName: string;
  onChange: (scope: TKpiScope) => void;
};

export function ScopePicker({ scope, options, currentName, onChange }: TScopePickerProps) {
  const { t } = useTranslation();
  const iconClass = "size-3.5 shrink-0 text-tertiary";

  const list: TScopeOption[] = options
    ? [
        option({ kind: "saya" }, options.self.display_name, t("kinerja.scope.self"), <User className={iconClass} />),
        ...(options.organisation
          ? [option({ kind: "organisasi" }, t("kinerja.scope.organisation"), "", <Building2 className={iconClass} />)]
          : []),
        ...(options.branches ?? []).map((c) =>
          option({ kind: "cabang", id: c.id }, c.name, t("cabang.kpi_scope"), <Factory className={iconClass} />)
        ),
        ...options.divisions.map((d) =>
          option({ kind: "divisi", id: d.id }, d.name, t("kinerja.scope.division"), <Network className={iconClass} />)
        ),
        ...options.departments.map((d) =>
          option(
            { kind: "departemen", id: d.id },
            d.name,
            t("kinerja.scope.department"),
            <Users className={iconClass} />
          )
        ),
        ...options.people.map((p) =>
          option(
            { kind: "orang", id: p.id },
            p.display_name,
            t("kinerja.scope.person"),
            <Avatar name={p.display_name} src={getFileURL(p.avatar_url ?? "")} size="sm" />
          )
        ),
      ]
    : [];

  // Staf hanya punya dirinya: tidak ada yang bisa dipilih, jadi tidak ada pemilih.
  if (list.length <= 1) return null;

  return (
    <CustomSearchSelect
      ariaLabel={t("kinerja.scope.label")}
      value={scope.kind === "orang" && scope.id === options?.self.id ? "saya" : scopeKey(scope)}
      label={<span className="truncate text-13 font-medium">{currentName}</span>}
      options={list}
      onChange={(value: string) => onChange(scopeFromKey(value))}
      noResultsMessage={t("kinerja.scope.no_results")}
      maxHeight="lg"
      buttonClassName="max-w-[16rem] border border-subtle"
    />
  );
}

type TPeriodPickerProps = { period: TKpiPeriod; onChange: (period: TKpiPeriod) => void; today: string };

export function PeriodPicker({ period, onChange, today }: TPeriodPickerProps) {
  const { t } = useTranslation();
  const select = (key: TKpiPeriodKey) =>
    // Rentang khusus mulai dari awal bulan sampai hari ini, lalu bisa diubah.
    onChange(key === "custom" ? { key, start: `${today.slice(0, 8)}01`, end: today } : { key });
  const dateClass =
    "rounded-button border border-subtle bg-layer-1 px-2 py-1 text-12 text-primary outline-none focus-visible:ring-2 focus-visible:ring-accent-strong";

  return (
    <div className="flex flex-wrap items-center gap-2">
      <fieldset
        aria-label={t("kinerja.period.label")}
        className="m-0 flex flex-wrap overflow-hidden rounded-button border border-subtle p-0 text-12"
      >
        {KPI_PERIODS.map((key) => (
          <button
            key={key}
            type="button"
            aria-pressed={period.key === key}
            onClick={() => select(key)}
            className={cn(
              "px-3 py-1.5 font-medium transition-colors",
              period.key === key
                ? "bg-layer-transparent-active text-primary"
                : "text-tertiary hover:bg-layer-transparent-hover hover:text-secondary"
            )}
          >
            {t(`kinerja.period.${key}`)}
          </button>
        ))}
      </fieldset>
      {period.key === "custom" && (
        <div className="flex items-center gap-1.5">
          <input
            type="date"
            aria-label={t("kinerja.period.from")}
            className={dateClass}
            value={period.start ?? ""}
            max={period.end}
            onChange={(e) => e.target.value && onChange({ ...period, start: e.target.value })}
          />
          <span aria-hidden className="text-12 text-tertiary">
            -
          </span>
          <input
            type="date"
            aria-label={t("kinerja.period.to")}
            className={dateClass}
            value={period.end ?? ""}
            min={period.start}
            onChange={(e) => e.target.value && onChange({ ...period, end: e.target.value })}
          />
        </div>
      )}
    </div>
  );
}
