/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: badge status persetujuan di kartu
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Badge "Menunggu persetujuan" di kartu/list/kanban (KEP-25/26): tugas staf
 * yang belum disetujui HARUS terlihat beda di papan, bukan cuma di sidebar
 * detail. Membaca `approval_status` yang sudah ikut di payload issue, tanpa
 * request tambahan per baris. null = tak pernah butuh persetujuan, tak tampil.
 *
 * Kalau yang membuka papan boleh memutuskan, tombol Setujui (satu klik) dan
 * Tolak ikut tampil di sebelah badge. Lihat `approval-actions.tsx`.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { CheckCircle2, Clock, XCircle } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import type { TIssue } from "@plane/types";
import { cn } from "@plane/utils";
// local imports
import { ApprovalDecisionButtons, useBarisBolehSayaPutuskan } from "./approval-actions";

// Bentuknya meniru chip state di kartu (BorderButton varian "border-with-text"
// + Button ghost sm): tinggi 20px, garis 0.5px, ikon berwarna, teks netral.
// Warna status cukup di ikon, sama seperti ikon grup state. Lebarnya selebar
// isinya (`w-fit`): di kartu kanban induknya flex-col, jadi tanpa
// ini chip melar memenuhi kartu.
type TApprovalChipProps = {
  icon: typeof Clock;
  iconClassName: string;
  label: string;
};

export function ApprovalChip({ icon: Icon, iconClassName, label }: TApprovalChipProps) {
  return (
    <span
      className="flex h-5 w-fit max-w-full shrink-0 items-center gap-1.5 rounded-sm border-[0.5px] border-strong px-1.5 text-caption-md-medium text-secondary"
      title={label}
    >
      <Icon className={cn("size-3.5 shrink-0", iconClassName)} aria-hidden />
      <span className="truncate">{label}</span>
    </span>
  );
}

export const ApprovalCardBadge = observer(function ApprovalCardBadge({ issue }: { issue: TIssue }) {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const status = issue.approval_status ?? null;
  const baris = useBarisBolehSayaPutuskan(workspaceSlug?.toString(), issue);

  if (status === "menunggu") {
    const label = t("issue.approval.badge.pending");
    return (
      <span className="flex w-fit max-w-full shrink-0 items-center gap-1.5">
        <ApprovalChip icon={Clock} iconClassName="text-warning-primary" label={label} />
        {baris && workspaceSlug && issue.project_id && (
          <ApprovalDecisionButtons
            workspaceSlug={workspaceSlug.toString()}
            projectId={issue.project_id}
            baris={baris}
          />
        )}
      </span>
    );
  }
  if (status === "ditolak") {
    const label = t("issue.approval.badge.rejected");
    return <ApprovalChip icon={XCircle} iconClassName="text-danger-primary" label={label} />;
  }
  if (status === "disetujui") {
    const label = t("issue.approval.badge.approved");
    return <ApprovalChip icon={CheckCircle2} iconClassName="text-success-primary" label={label} />;
  }
  return <></>;
});
