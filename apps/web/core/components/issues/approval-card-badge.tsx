/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: chip status persetujuan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * SATU komponen status persetujuan untuk semua layar (kartu kanban/list/
 * spreadsheet, sidebar detail, peek, halaman Persetujuan): ikon, warna, dan
 * label hanya diputuskan di sini, supaya "Menunggu" di papan dan di antrean
 * tidak pernah tampil beda lagi.
 *
 * Badge kartu (KEP-25/26) membaca `approval_status` yang sudah ikut di payload
 * issue, tanpa request tambahan per baris. null = tak pernah butuh
 * persetujuan, tak tampil. Kalau yang membuka papan boleh memutuskan, tombol
 * Setujui (satu klik) dan Tolak ikut tampil. Lihat `approval-actions.tsx`.
 */

import type { ReactNode } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { CheckCircle2, Clock, XCircle } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Tooltip } from "@plane/propel/tooltip";
import type { TIssue } from "@plane/types";
import { cn } from "@plane/utils";
// hooks
import { usePlatformOS } from "@/hooks/use-platform-os";
// services
import type { TStatusPersetujuan } from "@/services/persetujuan.service";
// local imports
import { ApprovalDecisionButtons, useBarisBolehSayaPutuskan } from "./approval-actions";

const TAMPILAN_STATUS: Record<TStatusPersetujuan, { icon: typeof Clock; iconClassName: string }> = {
  menunggu: { icon: Clock, iconClassName: "text-warning-primary" },
  disetujui: { icon: CheckCircle2, iconClassName: "text-success-primary" },
  ditolak: { icon: XCircle, iconClassName: "text-danger-primary" },
};

type TApprovalStatusChipProps = {
  status: TStatusPersetujuan;
  /** Nama pemutus; untuk "disetujui" labelnya menjadi "Approved by <nama>". */
  decidedBy?: string | null;
  /** Isi tooltip (pemutus, tanggal, alasan). Tanpa ini chip memakai `title` biasa. */
  tooltipContent?: ReactNode;
};

/**
 * Bentuknya meniru chip state di kartu (BorderButton varian "border-with-text"
 * + Button ghost sm): tinggi 20px, garis 0.5px, ikon berwarna, teks netral.
 * Warna status cukup di ikon, sama seperti ikon grup state. Lebarnya selebar
 * isinya (`w-fit`): di kartu kanban induknya flex-col, jadi tanpa ini chip
 * melar memenuhi kartu.
 */
export function ApprovalStatusChip({ status, decidedBy, tooltipContent }: TApprovalStatusChipProps) {
  const { t } = useTranslation();
  const { isMobile } = usePlatformOS();
  const { icon: Icon, iconClassName } = TAMPILAN_STATUS[status];
  const label =
    status === "menunggu"
      ? t("issue.approval.badge.pending")
      : status === "ditolak"
        ? t("issue.approval.badge.rejected")
        : decidedBy
          ? t("issue.approval.sidebar.approved_by", { name: decidedBy })
          : t("issue.approval.badge.approved");

  const chip = (
    <span
      className={cn(
        "flex h-5 w-fit max-w-full shrink-0 items-center gap-1.5 rounded-sm border-[0.5px] border-strong px-1.5 text-caption-md-medium text-secondary",
        { "cursor-default": !!tooltipContent }
      )}
      title={tooltipContent ? undefined : label}
    >
      <Icon className={cn("size-3.5 shrink-0", iconClassName)} aria-hidden />
      <span className="truncate">{label}</span>
    </span>
  );

  if (!tooltipContent) return chip;
  return (
    <Tooltip tooltipContent={tooltipContent} isMobile={isMobile}>
      {chip}
    </Tooltip>
  );
}

export const ApprovalCardBadge = observer(function ApprovalCardBadge({ issue }: { issue: TIssue }) {
  const { workspaceSlug } = useParams();
  const status = issue.approval_status ?? null;
  const baris = useBarisBolehSayaPutuskan(workspaceSlug?.toString(), issue);

  if (!status) return <></>;
  if (status !== "menunggu") return <ApprovalStatusChip status={status} />;
  return (
    <span className="flex w-fit max-w-full shrink-0 items-center gap-1.5">
      <ApprovalStatusChip status={status} />
      {baris && workspaceSlug && issue.project_id && (
        <ApprovalDecisionButtons workspaceSlug={workspaceSlug.toString()} projectId={issue.project_id} baris={baris} />
      )}
    </span>
  );
});
