/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: widget "Needs attention" di Home
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Ringkasan singkat pekerjaan yang perlu perhatian: per kelompok jumlah dan
 * paling banyak lima tugas teratas. Kelompok kosong tidak tampil; kalau semuanya
 * kosong, satu kalimat tenang. Satu panggilan server (lihat `plane/utils/perhatian.py`).
 */

import { observer } from "mobx-react";
import Link from "next/link";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import type { THomeWidgetProps } from "@plane/types";
import { cn, generateWorkItemLink, renderFormattedDate } from "@plane/utils";
// hooks
import { useUser } from "@/hooks/store/user";
// services
import { AttentionService } from "@/services/attention.service";
import type { TAttentionGroup, TAttentionGroupKey, TAttentionItem } from "@/services/attention.service";

const attentionService = new AttentionService();

/** Kelompok yang memberi alasan merah (terlambat/ditolak). */
const ALERT_GROUPS = new Set<TAttentionGroupKey>(["overdue_mine", "team_overdue", "rejected"]);
/** Jendela `due_soon` bawaan, untuk server lama yang belum mengirim `lookahead_days`. */
const DEFAULT_LOOKAHEAD_DAYS = 7;

export const AttentionWidget = observer(function AttentionWidget(props: THomeWidgetProps) {
  const { workspaceSlug } = props;
  const { t } = useTranslation();
  const { data: currentUser } = useUser();
  const { data } = useSWR(`HOME_ATTENTION_${workspaceSlug}`, () => attentionService.getAttention(workspaceSlug), {
    revalidateOnFocus: true,
    revalidateIfStale: true,
    dedupingInterval: 30_000,
  });

  // Gagal memuat atau belum ada data: widget diam, Home tetap utuh.
  if (!data) return null;
  const groups = data.groups.filter((group) => group.count > 0);

  const viewAllHref = (group: TAttentionGroup): string | null => {
    if (group.key === "decide")
      return group.top_project_id ? `/${workspaceSlug}/projects/${group.top_project_id}/persetujuan` : null;
    if (["overdue_mine", "due_soon", "rejected", "waiting_mine"].includes(group.key) && currentUser)
      return `/${workspaceSlug}/profile/${currentUser.id}/assigned`;
    return null;
  };

  return (
    <section aria-labelledby="home-attention-title" className="flex flex-col gap-3">
      <h2 id="home-attention-title" className="text-14 font-semibold text-primary">
        {t("attention_ui.title")}
      </h2>
      {groups.length === 0 ? (
        <p className="rounded-card border border-subtle px-4 py-3 text-13 text-tertiary">{t("attention_ui.empty")}</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {groups.map((group) => (
            <AttentionGroup
              key={group.key}
              group={group}
              workspaceSlug={workspaceSlug}
              viewAllHref={viewAllHref(group)}
              lookaheadDays={data.lookahead_days ?? DEFAULT_LOOKAHEAD_DAYS}
            />
          ))}
        </div>
      )}
    </section>
  );
});

type TGroupProps = {
  group: TAttentionGroup;
  workspaceSlug: string;
  viewAllHref: string | null;
  lookaheadDays: number;
};

function AttentionGroup({ group, workspaceSlug, viewAllHref, lookaheadDays }: TGroupProps) {
  const { t } = useTranslation();
  const isAlert = ALERT_GROUPS.has(group.key);
  const hidden = group.count - group.items.length;

  return (
    <div className="flex min-w-0 flex-col rounded-card border border-subtle bg-layer-1">
      <div className="flex items-center justify-between gap-2 px-4 py-2.5">
        <h3 className="min-w-0 truncate text-13 font-semibold text-primary">
          {t(`attention_ui.group_${group.key}`, { days: lookaheadDays })}
        </h3>
        <span className={cn("text-13 font-semibold", isAlert ? "text-danger-primary" : "text-secondary")}>
          {group.count}
        </span>
      </div>
      <ul className="divide-y divide-subtle border-t border-subtle">
        {group.items.map((item) => (
          <AttentionRow key={item.id} item={item} workspaceSlug={workspaceSlug} groupKey={group.key} />
        ))}
      </ul>
      {(viewAllHref || hidden > 0) && (
        <div className="flex items-center justify-between gap-2 border-t border-subtle px-4 py-2 text-12 text-tertiary">
          <span>{hidden > 0 ? t("attention_ui.more", { count: hidden }) : ""}</span>
          {viewAllHref && (
            <Link href={viewAllHref} className="font-medium text-accent-primary hover:underline">
              {t("attention_ui.view_all")}
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

function AttentionRow({
  item,
  workspaceSlug,
  groupKey,
}: {
  item: TAttentionItem;
  workspaceSlug: string;
  groupKey: TAttentionGroupKey;
}) {
  const { t } = useTranslation();
  const href = generateWorkItemLink({
    workspaceSlug,
    projectId: item.project_id,
    issueId: item.id,
    projectIdentifier: item.identifier.slice(0, item.identifier.lastIndexOf("-")),
    sequenceId: item.sequence_id,
  });
  const note =
    groupKey === "rejected" && item.reason
      ? item.reason
      : groupKey === "decide" && item.requester
        ? t("attention_ui.requested_by", { name: item.requester })
        : item.project_name;
  const isLate = item.target_date !== null && ALERT_GROUPS.has(groupKey) && groupKey !== "rejected";

  return (
    <li>
      <Link href={href} className="flex items-center justify-between gap-3 px-4 py-2 hover:bg-layer-2">
        <div className="min-w-0">
          <p className="truncate text-13 text-primary">
            <span className="mr-1.5 text-12 text-tertiary">{item.identifier}</span>
            {item.name}
          </p>
          <p className="truncate text-12 text-tertiary">{note}</p>
        </div>
        {item.target_date && (
          <span className={cn("shrink-0 text-12", isLate ? "font-medium text-danger-primary" : "text-tertiary")}>
            {renderFormattedDate(item.target_date)}
          </span>
        )}
      </Link>
    </li>
  );
}
