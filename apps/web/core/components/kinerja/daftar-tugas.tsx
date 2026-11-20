/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: dashboard KPI
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tugas satu orang yang lewat tenggat dan yang baru selesai. Server hanya
 * mengirim tugas yang boleh dilihat pembuka halaman, jadi daftar ini bisa lebih
 * pendek daripada angka di ubin.
 */

import Link from "next/link";
import { useTranslation } from "@plane/i18n";
import { cn, generateWorkItemLink } from "@plane/utils";
import { formatDay } from "@/components/dashboard-divisi/laporan";
import type { TKpiItem } from "@/services/kinerja.service";
import { EmptyNote } from "./bagian";

const TIMING_CLASS: Record<NonNullable<TKpiItem["timing"]>, string> = {
  on_time: "bg-success-subtle text-success-primary",
  late: "bg-danger-subtle text-danger-primary",
  no_due_date: "bg-layer-3 text-tertiary",
};

type Props = { workspaceSlug: string; items: TKpiItem[]; total: number | null; emptyText: string };

export function ItemList({ workspaceSlug, items, total, emptyText }: Props) {
  const { t } = useTranslation();
  const hidden = (total ?? 0) - items.length;
  return (
    <div className="flex flex-col gap-2">
      {items.length === 0 ? (
        <EmptyNote>{hidden > 0 ? t("kinerja.items.none_visible") : emptyText}</EmptyNote>
      ) : (
        <ul className="divide-y divide-subtle rounded-card border border-subtle bg-layer-1">
          {items.map((item) => (
            <ItemRow key={item.id} workspaceSlug={workspaceSlug} item={item} />
          ))}
        </ul>
      )}
      {items.length > 0 && hidden > 0 && (
        <p className="text-11 text-tertiary">{t("kinerja.items.more", { count: hidden })}</p>
      )}
    </div>
  );
}

function ItemRow({ workspaceSlug, item }: { workspaceSlug: string; item: TKpiItem }) {
  const { t, currentLocale } = useTranslation();
  const href = generateWorkItemLink({
    workspaceSlug,
    projectId: item.project_id,
    issueId: item.id,
    projectIdentifier: item.project_identifier,
    sequenceId: item.sequence_id,
  });
  const day = item.completed_date ?? item.target_date;

  return (
    <li>
      <Link href={href} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2 hover:bg-layer-2">
        <span className="w-20 shrink-0 font-code text-11 text-tertiary">
          {item.project_identifier}-{item.sequence_id}
        </span>
        <span
          className="order-last min-w-0 basis-full truncate text-13 text-primary sm:order-none sm:flex-1 sm:basis-0"
          title={item.name}
        >
          {item.name}
        </span>
        {day && (
          <span className="shrink-0 text-12 text-tertiary">
            {item.completed_date
              ? formatDay(day, currentLocale)
              : t("kinerja.items.due", { date: formatDay(day, currentLocale) })}
          </span>
        )}
        {item.timing && (
          <span
            className={cn(
              "inline-flex shrink-0 items-center rounded-control px-2 py-0.5 text-11 font-semibold whitespace-nowrap",
              TIMING_CLASS[item.timing]
            )}
          >
            {t(`kinerja.timing.${item.timing}`)}
          </span>
        )}
      </Link>
    </li>
  );
}
