/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu satu tugas di widget "Needs attention"
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { cn, generateWorkItemLink, renderFormattedDate } from "@plane/utils";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// services
import type { TAttentionGroupKey, TAttentionItem } from "@/services/attention.service";
// local
import { DecideActions, ReplyAction, StateAction, tandaiDibaca } from "./actions";
import type { TOnAct } from "./actions";
import { removeItem } from "./data";

/** Kelompok yang memberi alasan merah (terlambat/ditolak). */
export const ALERT_GROUPS = new Set<TAttentionGroupKey>(["overdue_mine", "team_overdue", "rejected"]);
/** Kelompok yang berisi tugas saya sendiri, jadi statusnya boleh diubah dari kartu. */
const STATE_GROUPS = new Set<TAttentionGroupKey>(["overdue_mine", "due_soon", "rejected", "waiting_mine"]);

const tanggal = (iso?: string) => (iso ? (renderFormattedDate(iso) ?? "") : "");

type TCardProps = {
  workspaceSlug: string;
  groupKey: TAttentionGroupKey;
  item: TAttentionItem;
  onAct: TOnAct;
  onDismiss: () => void;
};

export const AttentionCard = observer(function AttentionCard(props: TCardProps) {
  const { workspaceSlug, groupKey, item, onAct, onDismiss } = props;
  const { t } = useTranslation();
  const { setPeekIssue } = useIssueDetail();

  const href = generateWorkItemLink({
    workspaceSlug,
    projectId: item.project_id,
    issueId: item.id,
    projectIdentifier: item.identifier.slice(0, item.identifier.lastIndexOf("-")),
    sequenceId: item.sequence_id,
  });
  const peek = () => setPeekIssue({ workspaceSlug, projectId: item.project_id, issueId: item.id });
  const handleTitleClick = (e: React.MouseEvent) => {
    // Ctrl/Cmd/tengah tetap membuka tab baru; klik biasa membuka peek seperti widget Home lain.
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    e.preventDefault();
    peek();
  };

  const alasan =
    groupKey === "decide"
      ? t("perhatian_aksi.requested_by_on", { name: item.requester ?? "", date: tanggal(item.requested_at) })
      : groupKey === "rejected"
        ? [t("perhatian_aksi.rejected_on", { date: tanggal(item.decided_at) }), item.reason].filter(Boolean).join(" · ")
        : groupKey === "waiting_mine"
          ? t("perhatian_aksi.waiting_since", { date: tanggal(item.requested_at) })
          : groupKey === "mentioned"
            ? item.comment_id
              ? t("perhatian_aksi.mentioned_by_on", { name: item.mentioned_by ?? "", date: tanggal(item.mentioned_at) })
              : t("perhatian_aksi.mentioned_in_description", { date: tanggal(item.mentioned_at) })
            : null;
  const isLate = !!item.target_date && ALERT_GROUPS.has(groupKey) && groupKey !== "rejected";

  const tandaiBaca = () => {
    if (!item.notification_id) return onDismiss();
    void onAct(removeItem(groupKey, item.key), async () => {
      try {
        await tandaiDibaca(workspaceSlug, item.notification_id);
        return true;
      } catch {
        setToast({ type: TOAST_TYPE.ERROR, title: t("perhatian_aksi.failed") });
        return false;
      }
    });
  };

  return (
    <li
      className="flex flex-col gap-1.5 px-4 py-2.5"
      aria-label={t("perhatian_aksi.actions_for", { number: item.identifier })}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <Link
            href={href}
            onClick={handleTitleClick}
            className="block truncate text-13 text-primary hover:underline sentuh:-my-2.5 sentuh:py-2.5"
            title={`${item.identifier} ${item.name}`}
          >
            <span className="mr-1.5 text-12 text-tertiary">{item.identifier}</span>
            {item.name}
          </Link>
          <p className="truncate text-12 text-tertiary" title={item.project_name}>
            {item.project_name}
            {item.state_name && ` · ${item.state_name}`}
          </p>
        </div>
        {item.target_date && (
          <span className={cn("shrink-0 text-12", isLate ? "font-medium text-danger-primary" : "text-tertiary")}>
            {renderFormattedDate(item.target_date)}
          </span>
        )}
      </div>
      {alasan && <p className="text-12 text-secondary">{alasan}</p>}
      {groupKey === "mentioned" && item.snippet && (
        <p className="line-clamp-2 rounded-card bg-layer-2 px-2 py-1 text-12 text-secondary">{item.snippet}</p>
      )}
      <div className="flex flex-wrap items-center gap-1.5">
        {groupKey === "decide" && <DecideActions {...{ workspaceSlug, groupKey, item, onAct }} />}
        {STATE_GROUPS.has(groupKey) && <StateAction {...{ workspaceSlug, groupKey, item, onAct }} />}
        {groupKey === "mentioned" && <ReplyAction {...{ workspaceSlug, groupKey, item, onAct }} />}
        <Button variant="ghost" size="sm" onClick={peek} aria-label={`${t("perhatian_aksi.open")} ${item.identifier}`}>
          {t("perhatian_aksi.open")}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={tandaiBaca}
          aria-label={`${groupKey === "mentioned" ? t("perhatian_aksi.mark_read") : t("perhatian_aksi.dismiss")} ${item.identifier}`}
        >
          {groupKey === "mentioned" ? t("perhatian_aksi.mark_read") : t("perhatian_aksi.dismiss")}
        </Button>
      </div>
    </li>
  );
});
