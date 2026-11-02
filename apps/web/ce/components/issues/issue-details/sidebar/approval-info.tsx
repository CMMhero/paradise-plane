/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: properti persetujuan di detail work item
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * KEP-55: staf yang menggeser tugasnya ke Done hanya MENGAJUKAN; tugasnya tidak
 * berpindah sampai atasan menyetujui. Di daftar properti cukup SATU chip, sama
 * persis dengan badge di kartu (`ApprovalStatusChip`): "Awaiting approval", "Approved
 * by <nama>", atau "Rejected"; tanpa pengajuan = "-". Log tiap pengajuan &
 * keputusan ada di Activity (`IssueActivity field="approval"`), bukan di sini
 * (keputusan user 2 Nov).
 *
 * Status dibaca dari `approval_status` di store (ikut payload issue, langsung
 * berubah sesudah PATCH/keputusan). Baris persetujuan terkini hanya diambil
 * untuk nama pemutus dan tombol Setujui/Tolak atasan yang boleh memutuskan.
 */

import { observer } from "mobx-react";
import { ShieldCheck } from "lucide-react";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
// components
import { SidebarPropertyListItem } from "@/components/common/layout/sidebar/property-list-item";
import { AWALAN_KUNCI_PERSETUJUAN, ApprovalDecisionButtons } from "@/components/issues/approval-actions";
import { ApprovalStatusChip } from "@/components/issues/approval-card-badge";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// services
import { PersetujuanService } from "@/services/persetujuan.service";

type TApprovalSidebarProps = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
};

const persetujuanService = new PersetujuanService();

export const ApprovalSidebarInfo = observer(function ApprovalSidebarInfo(props: TApprovalSidebarProps) {
  const { workspaceSlug, projectId, issueId } = props;
  const { t } = useTranslation();
  const {
    issue: { getIssueById },
  } = useIssueDetail();
  const status = getIssueById(issueId)?.approval_status ?? null;

  // Status ikut kunci: keputusan dari papan/menu mengubahnya, jadi baris di
  // sini dimuat ulang tanpa perlu tahu siapa yang memutuskan.
  const { data: terkini } = useSWR(
    status && workspaceSlug && projectId && issueId
      ? `${AWALAN_KUNCI_PERSETUJUAN}:tugas:${workspaceSlug}:${projectId}:${issueId}:${status}`
      : null,
    async () => {
      const hasil = (await persetujuanService.daftar(workspaceSlug, projectId, { tugas: issueId }))?.hasil ?? [];
      // Yang menunggu menang; sisanya urutan server (terbaru dulu).
      return hasil.find((b) => b.status === "menunggu") ?? hasil[0] ?? null;
    },
    // Senyap seperti worklog: sidebar tak boleh berteriak kalau gagal muat.
    { shouldRetryOnError: false }
  );

  const pemutus = terkini?.status === status ? terkini?.diputuskan_oleh_nama : null;

  return (
    <SidebarPropertyListItem icon={ShieldCheck} label={t("issue.approval.sidebar.label")} childrenClassName="px-2">
      {status ? (
        // Setinggi baris properti lain (h-7.5) supaya chip 20px sejajar label.
        <span className="flex h-7.5 min-w-0 items-center">
          <ApprovalStatusChip status={status} decidedBy={pemutus} />
        </span>
      ) : (
        <span className="flex h-7.5 items-center text-body-xs-medium text-placeholder">-</span>
      )}
      {status === "menunggu" && terkini?.boleh_saya_putuskan && (
        <ApprovalDecisionButtons workspaceSlug={workspaceSlug} projectId={projectId} baris={terkini} />
      )}
    </SidebarPropertyListItem>
  );
});
