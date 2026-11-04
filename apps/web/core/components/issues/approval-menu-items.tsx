/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: setujui/tolak dari menu "..." work item
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Atasan bisa memutuskan langsung dari menu titik tiga di halaman work item,
 * sebaris dengan Edit / Make a copy / Open in new tab, tanpa membuka tab
 * Persetujuan. Item menu hanya tampil kalau server bilang
 * `boleh_saya_putuskan` (server tetap memeriksa ulang saat tombol ditekan).
 * Logika keputusannya dipakai bersama papan, lihat `approval-actions.tsx`.
 */

import { useState } from "react";
import { CheckCircle2, XCircle } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import type { TIssue } from "@plane/types";
import type { TContextMenuItem } from "@plane/ui";
// local imports
import { ApprovalRejectModal, useBarisBolehSayaPutuskan, usePutuskanPersetujuan } from "./approval-actions";

export const useMenuPersetujuan = (workspaceSlug: string | undefined, issue: TIssue) => {
  const { t } = useTranslation();
  const baris = useBarisBolehSayaPutuskan(workspaceSlug, issue);
  const { putuskan, prosesId } = usePutuskanPersetujuan();
  const [modalTolak, setModalTolak] = useState(false);
  const bolehPutuskan = !!baris && !!workspaceSlug && !!issue.project_id;

  const kirim = (aksi: "setujui" | "tolak", alasan = "") =>
    baris && workspaceSlug && issue.project_id
      ? putuskan(workspaceSlug, issue.project_id, baris, aksi, alasan)
      : Promise.resolve(false);

  const menuItems: TContextMenuItem[] = [
    {
      key: "setujui",
      title: t("issue.approval.menu.approve"),
      icon: CheckCircle2,
      action: () => void kirim("setujui"),
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
    <ApprovalRejectModal
      workspaceSlug={workspaceSlug}
      projectId={issue.project_id ?? undefined}
      isOpen={modalTolak}
      isSubmitting={!!baris && prosesId === baris.id}
      onClose={() => setModalTolak(false)}
      onConfirm={async (alasan) => {
        const berhasil = await kirim("tolak", alasan);
        if (berhasil) setModalTolak(false);
        return berhasil;
      }}
    />
  );

  return { menuItems, modal };
};
