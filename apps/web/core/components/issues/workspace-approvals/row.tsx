/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: satu baris halaman Persetujuan workspace
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * `ListItem` yang sama dengan antrean per departemen. Pengajuan selesai memakai
 * tombol keputusan bersama (`ApprovalDecisionButtons`); permintaan lintas
 * departemen diterima/ditolak lewat Intake departemen tujuan.
 */

import { useRef, useState } from "react";
import { observer } from "mobx-react";
import { Check, X } from "lucide-react";
import { useSWRConfig } from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { StateGroupIcon } from "@plane/propel/icons";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Tooltip } from "@plane/propel/tooltip";
import { Row } from "@plane/ui";
import { renderFormattedDate } from "@plane/utils";
// components
import { ListItem } from "@/components/core/list";
import { ButtonAvatars } from "@/components/dropdowns/member/avatar";
// hooks
import { usePlatformOS } from "@/hooks/use-platform-os";
// services
import { CrossDivisionService, type TKeputusanPermintaan } from "@/services/cross_division.service";
import type { TBarisAntreanWorkspace } from "@/services/persetujuan.service";
// local imports
import {
  AWALAN_KUNCI_PERSETUJUAN,
  ApprovalDecisionButtons,
  ApprovalRejectModal,
  pesanGagalPersetujuan,
} from "../approval-actions";

const crossDivisionService = new CrossDivisionService();

type TBarisPermintaan = Extract<TBarisAntreanWorkspace, { jenis: "permintaan" }>;

/** Terima (satu klik) dan Tolak (dialog alasan) untuk satu permintaan lintas departemen. */
const RequestDecisionButtons = observer(function RequestDecisionButtons(props: {
  workspaceSlug: string;
  baris: TBarisPermintaan;
}) {
  const { workspaceSlug, baris } = props;
  const { t } = useTranslation();
  const { mutate } = useSWRConfig();
  const [proses, setProses] = useState(false);
  const [modalTolak, setModalTolak] = useState(false);

  const putuskan = async (status: TKeputusanPermintaan, alasan = ""): Promise<boolean> => {
    setProses(true);
    try {
      await crossDivisionService.putuskanPermintaan(workspaceSlug, baris.project.id, baris.tugas.id, status, alasan);
      void mutate((key) => typeof key === "string" && key.startsWith(AWALAN_KUNCI_PERSETUJUAN));
      setToast(
        status === 1
          ? {
              type: TOAST_TYPE.SUCCESS,
              title: t("persetujuan_p29.accepted_toast_title"),
              message: t("persetujuan_p29.accepted_toast_message", { number: baris.tugas.nomor }),
            }
          : {
              type: TOAST_TYPE.SUCCESS,
              title: t("persetujuan_p29.declined_toast_title"),
              message: t("persetujuan_p29.declined_toast_message"),
            }
      );
      return true;
    } catch (err) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("persetujuan_p29.decision_failed"),
        message: pesanGagalPersetujuan(err, t("issue.approval.toast.save_failed_message")),
      });
      return false;
    } finally {
      setProses(false);
    }
  };

  return (
    // Sama dengan ApprovalDecisionButtons: klik (termasuk di dalam dialog) tidak membuka baris.
    <span
      className="flex shrink-0 items-center gap-1 sentuh:gap-3"
      onClick={(e) => {
        e.stopPropagation();
        if (e.target === e.currentTarget) e.preventDefault();
      }}
      role="presentation"
    >
      <Button
        variant="primary"
        size="base"
        loading={proses}
        onClick={(e) => {
          e.preventDefault();
          void putuskan(1);
        }}
        prependIcon={<Check className="size-3.5" aria-hidden />}
      >
        {t("persetujuan_p29.accept")}
      </Button>
      <Button
        variant="error-outline"
        size="base"
        disabled={proses}
        onClick={(e) => {
          e.preventDefault();
          setModalTolak(true);
        }}
        prependIcon={<X className="size-3.5" aria-hidden />}
      >
        {t("persetujuan_p29.decline")}
      </Button>
      <ApprovalRejectModal
        workspaceSlug={workspaceSlug}
        projectId={baris.project.id}
        isOpen={modalTolak}
        isSubmitting={proses}
        title={t("persetujuan_p29.decline_title")}
        description={t("persetujuan_p29.decline_description")}
        confirmLabel={t("persetujuan_p29.decline")}
        onClose={() => setModalTolak(false)}
        onConfirm={async (alasan) => {
          const berhasil = await putuskan(-1, alasan.trim());
          if (berhasil) setModalTolak(false);
          return berhasil;
        }}
      />
    </span>
  );
});

type TWorkspaceApprovalRowProps = {
  workspaceSlug: string;
  baris: TBarisAntreanWorkspace;
};

export const WorkspaceApprovalRow = observer(function WorkspaceApprovalRow(props: TWorkspaceApprovalRowProps) {
  const { workspaceSlug, baris } = props;
  const { t } = useTranslation();
  const { isMobile } = usePlatformOS();
  const parentRef = useRef<HTMLDivElement>(null);
  const { tugas } = baris;
  const permintaan = baris.jenis === "permintaan";
  // Permintaan masih di Triage: work item-nya hanya terbuka dari halaman Intake.
  const tautan = permintaan
    ? `/${workspaceSlug}/projects/${baris.project.id}/intake/?currentTab=open&inboxIssueId=${tugas.id}`
    : `/${workspaceSlug}/browse/${tugas.nomor}/`;
  const diminta = t("persetujuan_p29.requested_by", {
    name: baris.pemohon?.nama ?? "-",
    date: renderFormattedDate(baris.diminta_pada) ?? "-",
  });

  return (
    <div>
      <ListItem
        className={permintaan ? "border-b-0" : undefined}
        parentRef={parentRef}
        isMobile={isMobile}
        title={tugas.judul}
        itemLink={tautan}
        prependTitleElement={
          <span className="flex shrink-0 items-center gap-2">
            <span className="rounded-control bg-layer-3 px-1.5 text-11 whitespace-nowrap text-secondary">
              {t(permintaan ? "persetujuan_p29.type_request" : "persetujuan_p29.type_completion")}
            </span>
            <span className="min-w-16 text-13 font-medium whitespace-nowrap text-tertiary">{tugas.nomor}</span>
          </span>
        }
        actionableItems={
          <>
            {tugas.state && tugas.state.group !== "triage" && (
              <Tooltip tooltipContent={tugas.state.name} isMobile={isMobile}>
                <span className="grid size-5 place-items-center">
                  <StateGroupIcon stateGroup={tugas.state.group} color={tugas.state.color} className="size-4" />
                </span>
              </Tooltip>
            )}
            {tugas.target_date && (
              <span className="hidden text-12 whitespace-nowrap text-tertiary md:inline">
                {t("persetujuan_p29.due", { date: renderFormattedDate(tugas.target_date) ?? "-" })}
              </span>
            )}
            {tugas.assignee_ids.length > 0 && <ButtonAvatars showTooltip={false} userIds={tugas.assignee_ids} />}
            <span className="hidden max-w-56 truncate text-12 text-tertiary lg:inline" title={diminta}>
              {diminta}
            </span>
            {permintaan ? (
              <RequestDecisionButtons workspaceSlug={workspaceSlug} baris={baris} />
            ) : (
              <ApprovalDecisionButtons
                workspaceSlug={workspaceSlug}
                projectId={baris.project.id}
                baris={{ id: baris.id, tugas: { id: tugas.id, nomor: tugas.nomor, judul: tugas.judul } }}
                variant="full"
              />
            )}
          </>
        }
      />
      {permintaan && (
        <Row className="border-b border-subtle pb-3 text-12 text-tertiary">
          {t("persetujuan_p29.from_department", { name: `${baris.asal.name} (${baris.asal.identifier})` })}
          {baris.ditunda && ` · ${t("persetujuan_p29.snoozed")}`}
          {baris.catatan && ` · ${baris.catatan}`}
        </Row>
      )}
    </div>
  );
});
