/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: satu baris antrean persetujuan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Baris memakai `ListItem` yang sama dengan daftar Pages/Cycles, jadi tinggi,
 * garis, hover, dan perilaku klik (buka work item) sama dengan halaman lain.
 */

import { useRef } from "react";
import { observer } from "mobx-react";
import { AlertTriangle, CheckCircle2, Clock, Send, XCircle } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { EPillSize, EPillVariant, Pill } from "@plane/propel/pill";
import { Tooltip } from "@plane/propel/tooltip";
import { Avatar } from "@plane/ui";
import { getFileURL, renderFormattedDate } from "@plane/utils";
// components
import { ListItem } from "@/components/core/list";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { usePlatformOS } from "@/hooks/use-platform-os";
// services
import type { TPersetujuanPenugasan } from "@/services/persetujuan.service";
// local imports
import { ApprovalDecisionButtons, usePutuskanPersetujuan } from "./approval-actions";

type TStatusPillProps = { baris: TPersetujuanPenugasan };

function StatusPill({ baris }: TStatusPillProps) {
  const { t } = useTranslation();
  const tanggal = renderFormattedDate(baris.diputuskan_pada) ?? "-";

  if (baris.status === "menunggu") {
    return (
      <Pill variant={EPillVariant.WARNING} size={EPillSize.XS} className="gap-1">
        <Clock className="size-3 shrink-0" aria-hidden />
        {t("issue.approval.badge.pending")}
      </Pill>
    );
  }

  const disetujui = baris.status === "disetujui";
  const siapa = baris.diputuskan_oleh_nama
    ? t(disetujui ? "issue.approval.queue.row_approved_by" : "issue.approval.queue.row_rejected_by", {
        name: baris.diputuskan_oleh_nama,
        date: tanggal,
      })
    : t("issue.approval.queue.row_decided", { date: tanggal });
  const alasan =
    !disetujui && baris.alasan ? t("issue.approval.queue.rejection_reason", { reason: baris.alasan }) : null;

  return (
    <Tooltip
      tooltipContent={
        <span className="flex max-w-72 flex-col gap-1">
          <span>{siapa}</span>
          {alasan && <span className="text-tertiary">{alasan}</span>}
        </span>
      }
    >
      <span className="cursor-default">
        <Pill variant={disetujui ? EPillVariant.SUCCESS : EPillVariant.ERROR} size={EPillSize.XS} className="gap-1">
          {disetujui ? (
            <CheckCircle2 className="size-3 shrink-0" aria-hidden />
          ) : (
            <XCircle className="size-3 shrink-0" aria-hidden />
          )}
          {disetujui ? t("issue.approval.badge.approved") : t("issue.approval.badge.rejected")}
        </Pill>
      </span>
    </Tooltip>
  );
}

type TApprovalQueueRowProps = {
  workspaceSlug: string;
  projectId: string;
  baris: TPersetujuanPenugasan;
};

export const ApprovalQueueRow = observer(function ApprovalQueueRow(props: TApprovalQueueRowProps) {
  const { workspaceSlug, projectId, baris } = props;
  const { t } = useTranslation();
  const { isMobile } = usePlatformOS();
  const { getUserDetails } = useMember();
  const { putuskan, prosesId } = usePutuskanPersetujuan();
  const parentRef = useRef<HTMLDivElement>(null);

  const pemohon = getUserDetails(baris.pemohon.id);
  const namaPemohon = pemohon?.display_name ?? baris.pemohon.nama ?? baris.pemohon.email ?? "-";
  const menunggu = baris.status === "menunggu";
  // Tugas yang ditolak kembali ke draft pemohon dan tidak punya halaman di papan.
  const bisaDibuka = baris.status !== "ditolak" && !!baris.tugas.nomor;
  const tanpaPenyetuju = menunggu && baris.penyetuju_di_divisi.length === 0;
  const bolehAjukanUlang = baris.status === "ditolak" && baris.peran_saya === "pemohon";

  return (
    <ListItem
      parentRef={parentRef}
      isMobile={isMobile}
      title={baris.tugas.judul ?? t("issue.approval.queue.untitled")}
      itemLink={bisaDibuka ? `/${workspaceSlug}/browse/${baris.tugas.nomor}/` : ""}
      disableLink={!bisaDibuka}
      prependTitleElement={
        <span className="w-16 shrink-0 truncate text-13 font-medium text-tertiary">{baris.tugas.nomor ?? "-"}</span>
      }
      actionableItems={
        <>
          {tanpaPenyetuju && (
            <Tooltip tooltipContent={t("issue.approval.queue.no_approver")} isMobile={isMobile}>
              <span className="grid size-5 cursor-default place-items-center text-warning-primary">
                <AlertTriangle className="size-4" aria-label={t("issue.approval.queue.no_approver")} />
              </span>
            </Tooltip>
          )}
          <StatusPill baris={baris} />
          <Tooltip
            tooltipContent={t("issue.approval.queue.row_submitted", {
              name: namaPemohon,
              date: renderFormattedDate(baris.created_at) ?? "-",
            })}
            isMobile={isMobile}
          >
            <span className="flex cursor-default items-center gap-2 text-13 text-tertiary">
              <Avatar name={namaPemohon} src={getFileURL(pemohon?.avatar_url ?? "")} showTooltip={false} />
              <span className="hidden whitespace-nowrap md:inline">{renderFormattedDate(baris.created_at)}</span>
            </span>
          </Tooltip>
          {menunggu && baris.boleh_saya_putuskan && (
            <ApprovalDecisionButtons workspaceSlug={workspaceSlug} projectId={projectId} baris={baris} variant="full" />
          )}
          {bolehAjukanUlang && (
            <Button
              variant="secondary"
              size="base"
              loading={prosesId === baris.id}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                void putuskan(workspaceSlug, projectId, baris, "ajukan-ulang");
              }}
              prependIcon={<Send className="size-3.5" aria-hidden />}
            >
              {t("issue.approval.actions.resubmit")}
            </Button>
          )}
        </>
      }
    />
  );
});
