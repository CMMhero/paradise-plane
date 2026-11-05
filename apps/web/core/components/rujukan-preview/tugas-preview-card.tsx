/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu pratinjau hover untuk mention (KEP-91)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { CalendarDays, Lock } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { PriorityIcon, StateGroupIcon } from "@plane/propel/icons";
import { ISSUE_PRIORITIES } from "@plane/constants";
import type { TStateGroups } from "@plane/types";
import { renderFormattedDate } from "@plane/utils";
// hooks
import { useInfoTugas } from "@/components/editor/embeds/mentions/use-info-rujukan";

/**
 * Isi kartu hover untuk #PRJ-12: nomor + project, judul, state, prioritas, tenggat, penanggung jawab.
 * Cukup untuk memutuskan perlu dibuka atau tidak; detail selebihnya ada di halaman work item.
 */
export function TugasPreviewCard({ id }: { id: string }) {
  const { t } = useTranslation();
  const { info, isLoading } = useInfoTugas(id);

  if (isLoading || !info) return <p className="text-12 text-tertiary">{t("rujukan_ui.preview_loading")}</p>;

  if (!info.boleh) {
    return (
      <div className="flex items-start gap-2 text-12 text-tertiary">
        <Lock className="mt-0.5 size-3.5 shrink-0" aria-hidden />
        <p>{t("rujukan_ui.work_item_no_access")}</p>
      </div>
    );
  }

  const prioritas = info.prioritas ?? "none";
  const tenggat = info.tenggat ? renderFormattedDate(info.tenggat) : null;
  const sisa = Math.max(0, (info.assignee_jumlah ?? 0) - (info.assignee?.length ?? 0));
  return (
    <div className="flex flex-col gap-2">
      <p className="truncate text-11 text-tertiary">
        <span className="font-medium">{info.nomor}</span>
        {info.project_nama ? ` · ${info.project_nama}` : null}
      </p>
      <p className="line-clamp-2 text-13 font-medium break-words text-primary">{info.judul}</p>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-12 text-secondary">
        {info.state_nama ? (
          <span className="flex min-w-0 items-center gap-1.5">
            <StateGroupIcon stateGroup={(info.state_group as TStateGroups | undefined) ?? "unstarted"} />
            <span className="truncate">{info.state_nama}</span>
          </span>
        ) : null}
        {prioritas !== "none" ? (
          <span className="flex items-center gap-1.5">
            <PriorityIcon priority={prioritas} />
            {ISSUE_PRIORITIES.find((p) => p.key === prioritas)?.title}
          </span>
        ) : null}
        {tenggat ? (
          <span className="flex items-center gap-1.5">
            <CalendarDays className="size-3.5 text-tertiary" aria-hidden />
            {t("rujukan_ui.due", { date: tenggat })}
          </span>
        ) : null}
      </div>
      <p className="truncate text-11 text-tertiary">
        {info.assignee && info.assignee.length > 0
          ? `${info.assignee.join(", ")}${sisa > 0 ? ` ${t("rujukan_ui.assignees_more", { count: sisa })}` : ""}`
          : t("rujukan_ui.unassigned")}
      </p>
    </div>
  );
}
