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
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TIssue } from "@plane/types";
import type { TContextMenuItem } from "@plane/ui";
import { EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
// hooks
import { terkunciPersetujuan, useSetelStatusPersetujuan } from "@/hooks/use-aturan-tugas";
// services
import { PersetujuanService } from "@/services/persetujuan.service";

const persetujuanService = new PersetujuanService();

const pesanGagal = (err: unknown, fallback: string): string => {
  const pesan = (err as { error?: string } | undefined)?.error;
  return typeof pesan === "string" && pesan.length > 0 ? pesan : fallback;
};

export const useMenuPersetujuan = (workspaceSlug: string | undefined, issue: TIssue) => {
  const setelStatus = useSetelStatusPersetujuan();
  const [modalTolak, setModalTolak] = useState(false);
  const [alasan, setAlasan] = useState("");
  const [isWorking, setIsWorking] = useState(false);

  const kunci =
    workspaceSlug && issue.project_id && terkunciPersetujuan(issue)
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
        title: aksi === "setujui" ? "Disetujui" : "Ditolak",
        message: aksi === "setujui" ? "Tugas disetujui dan tidak lagi terkunci." : "Tugas kembali ke draft pemohon.",
      });
    } catch (err) {
      setToast({ type: TOAST_TYPE.ERROR, title: "Gagal menyimpan", message: pesanGagal(err, "Gagal menyimpan keputusan.") });
    } finally {
      setIsWorking(false);
    }
  };

  const menuItems: TContextMenuItem[] = [
    {
      key: "setujui",
      title: "Setujui",
      icon: CheckCircle2,
      action: () => void putuskan("setujui"),
      shouldRender: bolehPutuskan,
    },
    {
      key: "tolak",
      title: "Tolak…",
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
        <h3 className="text-18 font-medium">Tolak tugas ini?</h3>
        <p className="text-13 text-secondary">
          Tugas kembali ke draft pemohon. Tulis alasannya supaya ia tahu apa yang harus diperbaiki.
        </p>
        <textarea
          value={alasan}
          rows={3}
          maxLength={2000}
          onChange={(e) => setAlasan(e.target.value)}
          placeholder="Alasan penolakan (wajib)"
          className="rounded border border-subtle bg-layer-1 px-2 py-1 text-13 outline-none focus:border-accent"
        />
        <div className="flex justify-end gap-2">
          <Button variant="secondary" size="lg" onClick={() => setModalTolak(false)}>
            Batal
          </Button>
          <Button
            variant="error-fill"
            size="lg"
            loading={isWorking}
            disabled={!alasan.trim()}
            onClick={() => void putuskan("tolak")}
          >
            Tolak
          </Button>
        </div>
      </div>
    </ModalCore>
  );

  return { menuItems, modal };
};
