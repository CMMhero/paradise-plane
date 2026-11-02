/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: keputusan persetujuan satu klik
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu tempat untuk memutuskan persetujuan, dipakai papan (list/kanban/
 * spreadsheet), menu "..." work item, dan halaman Persetujuan:
 *
 * - Setujui = SATU klik (alasan opsional, jadi tak perlu dialog).
 * - Tolak = dialog alasan, karena server menolak penolakan tanpa alasan.
 *
 * Papan tidak meminta baris persetujuan per kartu. Satu `GET ?peran=penyetuju`
 * per project (kunci SWR bersama) menjawab "baris mana yang boleh SAYA
 * putuskan" untuk seluruh kartu, dan hanya diambil kalau ada kartu yang
 * memang menunggu. Server tetap memeriksa ulang saat tombol ditekan.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Check, X } from "lucide-react";
import useSWR, { useSWRConfig } from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { IconButton } from "@plane/propel/icon-button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Tooltip } from "@plane/propel/tooltip";
import type { TIssue } from "@plane/types";
import { EModalPosition, EModalWidth, ModalCore, TextArea } from "@plane/ui";
// hooks
import { useSetelStatusPersetujuan } from "@/hooks/use-aturan-tugas";
import { usePlatformOS } from "@/hooks/use-platform-os";
// services
import { PersetujuanService, type TPersetujuanPenugasan } from "@/services/persetujuan.service";

const persetujuanService = new PersetujuanService();

/** Semua kunci SWR persetujuan berawalan ini, supaya satu keputusan menyegarkan semuanya. */
export const AWALAN_KUNCI_PERSETUJUAN = "PERSETUJUAN";

export const kunciAntreanProject = (workspaceSlug: string, projectId: string, peran: "penyetuju" | "pemohon") =>
  `${AWALAN_KUNCI_PERSETUJUAN}:${peran}:${workspaceSlug}:${projectId}`;

export const pesanGagalPersetujuan = (err: unknown, fallback: string): string => {
  const pesan = (err as { error?: string } | undefined)?.error;
  return typeof pesan === "string" && pesan.length > 0 ? pesan : fallback;
};

/** Antrean yang menunggu keputusan di satu project (null = jangan ambil). */
export const useAntreanPenyetuju = (workspaceSlug: string | undefined, projectId: string | null | undefined) =>
  useSWR(workspaceSlug && projectId ? kunciAntreanProject(workspaceSlug, projectId, "penyetuju") : null, () =>
    persetujuanService.daftar(workspaceSlug as string, projectId as string, { peran: "penyetuju" })
  );

/**
 * Baris menunggu milik `issue` yang boleh SAYA putuskan, atau null.
 * Tidak memicu request kalau tugasnya tidak sedang menunggu.
 */
export const useBarisBolehSayaPutuskan = (
  workspaceSlug: string | undefined,
  issue: Pick<TIssue, "id" | "project_id" | "approval_status"> | undefined
): TPersetujuanPenugasan | null => {
  const menunggu = issue?.approval_status === "menunggu";
  const { data } = useAntreanPenyetuju(menunggu ? workspaceSlug : undefined, issue?.project_id);
  if (!menunggu || !issue) return null;
  return (data?.hasil ?? []).find((b) => b.tugas.id === issue.id && b.boleh_saya_putuskan) ?? null;
};

export type TAksiKeputusan = "setujui" | "tolak" | "ajukan-ulang";

/** Kirim keputusan, samakan badge di store, segarkan semua antrean, beri toast. */
export const usePutuskanPersetujuan = () => {
  const { t } = useTranslation();
  const { mutate } = useSWRConfig();
  const setelStatus = useSetelStatusPersetujuan();
  const [prosesId, setProsesId] = useState<string | null>(null);

  const putuskan = async (
    workspaceSlug: string,
    projectId: string,
    baris: Pick<TPersetujuanPenugasan, "id" | "tugas">,
    aksi: TAksiKeputusan,
    alasan = ""
  ): Promise<boolean> => {
    setProsesId(baris.id);
    try {
      const hasil = await persetujuanService.putuskan(workspaceSlug, projectId, baris.id, aksi, alasan.trim());
      const statusBaru =
        aksi === "setujui" ? "disetujui" : aksi === "tolak" ? "ditolak" : (hasil?.status ?? "menunggu");
      setelStatus(baris.tugas.id, statusBaru);
      void mutate((key) => typeof key === "string" && key.startsWith(AWALAN_KUNCI_PERSETUJUAN));
      const judul = {
        setujui: t("issue.approval.toast.approved_title"),
        tolak: t("issue.approval.toast.rejected_title"),
        "ajukan-ulang": t("issue.approval.toast.resubmitted_title"),
      }[aksi];
      const pesan = {
        setujui: t("issue.approval.toast.approved_message"),
        tolak: t("issue.approval.toast.rejected_message"),
        "ajukan-ulang": t("issue.approval.toast.resubmitted_message", { number: baris.tugas.nomor ?? "" }),
      }[aksi];
      setToast({ type: TOAST_TYPE.SUCCESS, title: judul, message: pesan });
      return true;
    } catch (err) {
      // Pesan dari API ditampilkan apa adanya (mis. "Anda bukan atasan pembuat
      // di divisi ini"): kegagalan senyap adalah kelas bug termahal di sini.
      const cadangan =
        aksi === "ajukan-ulang"
          ? t("issue.approval.toast.resubmit_failed_message")
          : t("issue.approval.toast.save_failed_message");
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("issue.approval.toast.save_failed_title"),
        message: pesanGagalPersetujuan(err, cadangan),
      });
      return false;
    } finally {
      setProsesId(null);
    }
  };

  return { putuskan, prosesId };
};

type TApprovalRejectModalProps = {
  isOpen: boolean;
  isSubmitting: boolean;
  onClose: () => void;
  /** Kembalikan true kalau berhasil, supaya isian dibersihkan. */
  onConfirm: (alasan: string) => Promise<boolean>;
};

export function ApprovalRejectModal(props: TApprovalRejectModalProps) {
  const { isOpen, isSubmitting, onClose, onConfirm } = props;
  const { t } = useTranslation();
  const [alasan, setAlasan] = useState("");

  const handleClose = () => {
    setAlasan("");
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!alasan.trim()) return;
    if (await onConfirm(alasan)) setAlasan("");
  };

  return (
    <ModalCore isOpen={isOpen} handleClose={handleClose} position={EModalPosition.CENTER} width={EModalWidth.XL}>
      <form onSubmit={(e) => void handleSubmit(e)}>
        <div className="space-y-5 p-5">
          <div className="space-y-1">
            <h3 className="text-18 font-medium text-primary">{t("issue.approval.modal.reject_title")}</h3>
            <p className="text-13 text-secondary">{t("issue.approval.modal.reject_description")}</p>
          </div>
          <TextArea
            value={alasan}
            onChange={(e) => setAlasan(e.target.value)}
            maxLength={2000}
            placeholder={t("issue.approval.modal.reason_placeholder")}
            aria-label={t("issue.approval.modal.reason_placeholder")}
            className="min-h-24 w-full resize-none text-13"
          />
        </div>
        <div className="flex items-center justify-end gap-2 border-t-[0.5px] border-subtle px-5 py-4">
          <Button variant="secondary" size="lg" onClick={handleClose}>
            {t("issue.approval.actions.cancel")}
          </Button>
          <Button variant="error-fill" size="lg" type="submit" loading={isSubmitting} disabled={!alasan.trim()}>
            {t("issue.approval.actions.reject")}
          </Button>
        </div>
      </form>
    </ModalCore>
  );
}

/** Tombol yang menumpang di dalam kartu/baris (ControlLink): jangan ikut membukanya. */
const tahan = (e: React.MouseEvent) => {
  e.preventDefault();
  e.stopPropagation();
};

type TApprovalDecisionButtonsProps = {
  workspaceSlug: string;
  projectId: string;
  baris: Pick<TPersetujuanPenugasan, "id" | "tugas">;
  /** `compact` = ikon saja (baris papan); `full` = tombol berlabel (halaman Persetujuan). */
  variant?: "compact" | "full";
};

/**
 * Tombol Setujui (satu klik) + Tolak (dialog alasan). Klik ditahan supaya
 * tidak ikut membuka kartu/baris tempat tombol ini menumpang.
 */
export const ApprovalDecisionButtons = observer(function ApprovalDecisionButtons(props: TApprovalDecisionButtonsProps) {
  const { workspaceSlug, projectId, baris, variant = "compact" } = props;
  const { t } = useTranslation();
  const { isMobile } = usePlatformOS();
  const { putuskan, prosesId } = usePutuskanPersetujuan();
  const [modalTolak, setModalTolak] = useState(false);
  const sedangProses = prosesId === baris.id;

  const setujui = (e: React.MouseEvent) => {
    tahan(e);
    void putuskan(workspaceSlug, projectId, baris, "setujui");
  };
  const bukaTolak = (e: React.MouseEvent) => {
    tahan(e);
    setModalTolak(true);
  };

  return (
    // Pembungkus memutus rambatan klik ke kartu/baris induk (ControlLink),
    // TERMASUK klik di dalam dialog: portal tetap merambat lewat pohon React.
    // Hanya stopPropagation, supaya tombol submit dialog tetap jalan.
    <span
      className="flex shrink-0 items-center gap-1"
      onClick={(e) => {
        e.stopPropagation();
        if (e.target === e.currentTarget) e.preventDefault();
      }}
      role="presentation"
    >
      {variant === "full" ? (
        <>
          <Button
            variant="primary"
            size="base"
            loading={sedangProses}
            onClick={setujui}
            prependIcon={<Check className="size-3.5" aria-hidden />}
          >
            {t("issue.approval.actions.approve")}
          </Button>
          <Button
            variant="error-outline"
            size="base"
            disabled={sedangProses}
            onClick={bukaTolak}
            prependIcon={<X className="size-3.5" aria-hidden />}
          >
            {t("issue.approval.actions.reject")}
          </Button>
        </>
      ) : (
        <>
          <Tooltip tooltipContent={t("issue.approval.actions.approve")} isMobile={isMobile}>
            <IconButton
              variant="primary"
              size="sm"
              icon={Check}
              loading={sedangProses}
              onClick={setujui}
              aria-label={t("issue.approval.actions.approve")}
            />
          </Tooltip>
          <Tooltip tooltipContent={t("issue.approval.menu.reject")} isMobile={isMobile}>
            <IconButton
              variant="error-outline"
              size="sm"
              icon={X}
              disabled={sedangProses}
              onClick={bukaTolak}
              aria-label={t("issue.approval.menu.reject")}
            />
          </Tooltip>
        </>
      )}
      <ApprovalRejectModal
        isOpen={modalTolak}
        isSubmitting={sedangProses}
        onClose={() => setModalTolak(false)}
        onConfirm={async (alasan) => {
          const berhasil = await putuskan(workspaceSlug, projectId, baris, "tolak", alasan);
          if (berhasil) setModalTolak(false);
          return berhasil;
        }}
      />
    </span>
  );
});
