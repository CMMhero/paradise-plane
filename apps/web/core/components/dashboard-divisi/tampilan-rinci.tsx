/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Dashboard Divisi rinci (KEP-60)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tabel lengkap, dikelompokkan per divisi. Divisi yang bermasalah terbuka,
 * yang lancar tertutup, jadi angka yang tidak perlu dibaca tidak menghalangi.
 */

import { Fragment, useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronRight, Download } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
import type { TDivisionDashboard, TDivisionGroup, TDivisionStats } from "@/services/workspace_dashboard.service";
import { HealthPill, divisionLabel, formatMinutes, formatPercent } from "./bagian";
import { isExpandedByDefault, projectsOfDivision } from "./ringkasan";

type Props = {
  workspaceSlug: string;
  data: TDivisionDashboard;
  isTimeTrackingEnabled: boolean;
  csvUrl: string;
};

export function DetailView({ workspaceSlug, data, isTimeTrackingEnabled, csvUrl }: Props) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(data.divisions.filter(isExpandedByDefault).map(divisionKey))
  );

  const toggle = (key: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  return (
    <div className="flex flex-col gap-4">
      {isTimeTrackingEnabled && (
        <a
          href={csvUrl}
          className="flex items-center gap-1.5 self-end rounded border border-subtle px-2.5 py-1.5 text-12 font-medium text-secondary hover:bg-layer-2"
        >
          <Download className="size-3.5" /> {t("division_dashboard_ui.download_csv")}
        </a>
      )}

      <div className="overflow-x-auto rounded-md border border-subtle gulir-berpenanda">
        <table className="w-full min-w-[640px] text-left text-13">
          <thead>
            <tr className="border-b border-subtle bg-layer-2 text-12 text-tertiary">
              <th className="px-3 py-2 font-medium">{t("division_dashboard_ui.col_division_department")}</th>
              <th className="px-3 py-2 font-medium">{t("division_dashboard_ui.col_status")}</th>
              <th className="px-3 py-2 text-right font-medium">{t("division_dashboard_ui.done")}</th>
              <th className="px-3 py-2 text-right font-medium">{t("division_dashboard_ui.in_progress")}</th>
              <th className="px-3 py-2 text-right font-medium">{t("division_dashboard_ui.overdue")}</th>
              {isTimeTrackingEnabled && (
                <th className="px-3 py-2 text-right font-medium">{t("division_dashboard_ui.hours_month")}</th>
              )}
            </tr>
          </thead>
          <tbody>
            {data.divisions.map((division) => {
              const key = divisionKey(division);
              const isOpen = expanded.has(key);
              return (
                <Fragment key={key}>
                  <DivisionRow
                    division={division}
                    isOpen={isOpen}
                    onToggle={() => toggle(key)}
                    isTimeTrackingEnabled={isTimeTrackingEnabled}
                  />
                  {isOpen &&
                    projectsOfDivision(division, data.projects).map((p) => (
                      <ProjectRow
                        key={p.id}
                        project={p}
                        workspaceSlug={workspaceSlug}
                        isTimeTrackingEnabled={isTimeTrackingEnabled}
                      />
                    ))}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-12 text-tertiary">{t("division_dashboard_ui.footer_note")}</p>
    </div>
  );
}

const divisionKey = (d: TDivisionGroup): string => d.id ?? "tanpa-divisi";

const NUM = "px-3 py-2 text-right tabular-nums";

type TDivisionRowProps = {
  division: TDivisionGroup;
  isOpen: boolean;
  onToggle: () => void;
  isTimeTrackingEnabled: boolean;
};

function DivisionRow({ division, isOpen, onToggle, isTimeTrackingEnabled }: TDivisionRowProps) {
  const { t } = useTranslation();
  const Chevron = isOpen ? ChevronDown : ChevronRight;
  return (
    <tr className="border-b border-subtle bg-layer-1 font-semibold">
      <td className="px-3 py-2">
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={isOpen}
          className="flex items-center gap-1.5 text-left text-primary hover:text-secondary"
        >
          <Chevron className="size-3.5 shrink-0 text-tertiary" />
          {divisionLabel(division.name, t)}
        </button>
      </td>
      <td className="px-3 py-2">
        <HealthPill health={division.health} />
      </td>
      <td className={NUM}>{formatPercent(division.completion_rate)}</td>
      <td className={NUM}>{division.issues_active}</td>
      <OverdueCell count={division.issues_overdue} />
      {isTimeTrackingEnabled && <td className={NUM}>{formatMinutes(division.worklog_minutes_month, t)}</td>}
    </tr>
  );
}

type TProjectRowProps = { project: TDivisionStats; workspaceSlug: string; isTimeTrackingEnabled: boolean };

function ProjectRow({ project, workspaceSlug, isTimeTrackingEnabled }: TProjectRowProps) {
  const { t } = useTranslation();
  return (
    <tr className="border-b border-subtle text-secondary last:border-0 hover:bg-layer-2">
      <td className="py-2 pr-3 pl-9">
        <Link href={`/${workspaceSlug}/projects/${project.id}/issues`} className="hover:underline">
          <span className="text-primary">{project.department?.name ?? project.name}</span>{" "}
          <span className="text-12 text-tertiary">({project.department?.code ?? project.identifier})</span>
        </Link>
      </td>
      <td className="px-3 py-2">
        <HealthPill health={project.health} />
      </td>
      <td className={NUM}>{formatPercent(project.completion_rate)}</td>
      <td className={NUM}>{project.issues_active}</td>
      <OverdueCell count={project.issues_overdue} />
      {isTimeTrackingEnabled && <td className={NUM}>{formatMinutes(project.worklog_minutes_month, t)}</td>}
    </tr>
  );
}

function OverdueCell({ count }: { count: number }) {
  return <td className={cn(NUM, count > 0 && "font-semibold text-danger-primary")}>{count}</td>;
}
