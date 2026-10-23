/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: setujui/tolak dari menu "..." work item
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Atasan bisa memutuskan langsung dari menu titik tiga di halaman work item,
 * sebaris dengan Edit / Make a copy / Open in new tab, tanpa membuka tab
 * Persetujuan. Barisnya hanya diambil kalau tugasnya MENUNGGU, dan item menu
 * hanya tampil kalau server bilang `boleh_saya_putuskan` (server tetap
 * memeriksa ulang saat tombol ditekan).
 */

import { useState } from "react";
import { CheckCircle2, XCircle } from "lucide-react";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TIssue } from "@plane/types";
import type { TContextMenuItem } from "@plane/ui";
import { EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
// hooks
import { useSetelStatusPersetujuan } from "@/hooks/use-aturan-tugas";
// services
import { PersetujuanService } from "@/services/persetujuan.service";

const persetujuanService = new PersetujuanService();

const pesanGagal = (err: unknown, fallback: string): string => {
  const pesan = (err as { error?: string } | undefined)?.error;
  return typeof pesan === "string" && pesan.length > 0 ? pesan : fallback;
};

export const useMenuPersetujuan = (workspaceSlug: string | undefined, issue: TIssue) => {
  const { t } = useTranslation();
  const setelStatus = useSetelStatusPersetujuan();
  const [modalTolak, setModalTolak] = useState(false);
  const [alasan, setAlasan] = useState("");
  const [isWorking, setIsWorking] = useState(false);

  // Antrean tampil selama statusnya menunggu (bukan kunci: tugasnya bebas
  // dipindah/diubah; yang dijaga server hanya MASUK status selesai).
  const kunci =
    workspaceSlug && issue.project_id && issue?.approval_status === "menunggu"
      ? `PERSETUJUAN_TUGAS:${workspaceSlug}:${issue.id}`
      : null;
  const { data: baris, mutate } = useSWR(kunci, () =>
    persetujuanService
      .daftar(workspaceSlug as string, issue.project_id as string, { tugas: issue.id })
      .then((res) => (res?.hasil ?? []).find((b) => b.status === "menunggu") ?? null)
  );
  const bolehPutuskan = !!kunci && !!baris?.boleh_saya_putuskan;

  const putuskan = async (aksi: "setujui" | "tolak") => {
    if (!baris || !issue.project_id || !workspaceSlug) return;
    setIsWorking(true);
    try {
      await persetujuanService.putuskan(workspaceSlug, issue.project_id, baris.id, aksi, alasan.trim());
      setelStatus(issue.id, aksi === "setujui" ? "disetujui" : "ditolak");
      void mutate(null, { revalidate: false });
      setModalTolak(false);
      setAlasan("");
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: aksi === "setujui" ? t("issue.approval.toast.approved_title") : t("issue.approval.toast.rejected_title"),
        message:
          aksi === "setujui"
            ? t("issue.approval.toast.approved_message")
            : t("issue.approval.toast.rejected_message"),
      });
    } catch (err) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("issue.approval.toast.save_failed_title"),
        message: pesanGagal(err, t("issue.approval.toast.save_failed_message")),
      });
    } finally {
      setIsWorking(false);
    }
  };

  const menuItems: TContextMenuItem[] = [
    {
      key: "setujui",
      title: t("issue.approval.menu.approve"),
      icon: CheckCircle2,
      action: () => void putuskan("setujui"),
      shouldRender: bolehPutuskan,
    },
    {
      key: "tolak",
      title: t("issue.approval.menu.reject"),
      icon: XCircle,
      action: () => setModalTolak(true),
      shouldRender: bolehPutuskan,
    },
  ];

  const modal = (
    <ModalCore
      isOpen={modalTolak}
      handleClose={() => setModalTolak(false)}
      position={EModalPosition.CENTER}
      width={EModalWidth.LG}
    >
      <div className="flex flex-col gap-3 px-5 py-4">
        <h3 className="text-18 font-medium">{t("issue.approval.modal.reject_title")}</h3>
        <p className="text-13 text-secondary">{t("issue.approval.modal.reject_description")}</p>
        <textarea
          value={alasan}
          rows={3}
          maxLength={2000}
          onChange={(e) => setAlasan(e.target.value)}
          placeholder={t("issue.approval.modal.reason_placeholder")}
          aria-label={t("issue.approval.modal.reason_placeholder")}
          className="rounded border border-subtle bg-layer-1 px-2 py-1 text-13 outline-none focus:border-accent"
        />
        <div className="flex justify-end gap-2">
          <Button variant="secondary" size="lg" onClick={() => setModalTolak(false)}>
            {t("issue.approval.actions.cancel")}
          </Button>
          <Button
            variant="error-fill"
            size="lg"
            loading={isWorking}
            disabled={!alasan.trim()}
            onClick={() => void putuskan("tolak")}
          >
            {t("issue.approval.actions.reject")}
          </Button>
        </div>
      </div>
    </ModalCore>
  );

  return { menuItems, modal };
};
