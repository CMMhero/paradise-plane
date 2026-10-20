/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: indikator persetujuan penugasan 
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Indikator "belum disetujui" di sidebar work item (keputusan user 2026-10-15:
 * tugas TETAP MUNCUL, baris persetujuan itulah indikatornya). Dibaca lewat
 * `GET .../persetujuan-penugasan/?tugas=<id>` supaya tidak mengunduh seluruh
 * antrean project hanya untuk satu tugas.
 *
 * Kalau atasan yang sedang membuka juga boleh memutuskan, tombol Setujui/Tolak
 * tampil di sini — penolakan wajib beralasan, sesuai endpointnya.
 */

import { useCallback, useEffect, useState } from "react";
import { observer } from "mobx-react";
import { CheckCircle2, Clock, XCircle } from "lucide-react";
// plane imports
import { Button } from "@plane/propel/button";
import { EPillSize, EPillVariant, Pill } from "@plane/propel/pill";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
// services
import { PersetujuanService, type TPersetujuanPenugasan } from "@/services/persetujuan.service";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useSetelStatusPersetujuan } from "@/hooks/use-aturan-tugas";

type TApprovalSidebarProps = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
};

const persetujuanService = new PersetujuanService();

const inputClass = "rounded border border-subtle bg-layer-1 px-2 py-1 text-xs outline-none focus:border-accent";

const pesanGagal = (err: unknown, fallback: string): string => {
  const pesan = (err as { error?: string } | undefined)?.error;
  return typeof pesan === "string" && pesan.length > 0 ? pesan : fallback;
};

export const ApprovalSidebarInfo = observer(function ApprovalSidebarInfo(props: TApprovalSidebarProps) {
  const { workspaceSlug, projectId, issueId } = props;
  const [baris, setBaris] = useState<TPersetujuanPenugasan | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [alasan, setAlasan] = useState("");
  const [isWorking, setIsWorking] = useState(false);
  const [gagal, setGagal] = useState<string | null>(null);
  const setelStatus = useSetelStatusPersetujuan();
  const {
    issue: { getIssueById },
  } = useIssueDetail();
  const statusDiStore = getIssueById(issueId)?.approval_status;

  const muat = useCallback(async () => {
    if (!workspaceSlug || !projectId || !issueId) return;
    setIsLoading(true);
    try {
      const res = await persetujuanService.daftar(workspaceSlug, projectId, { tugas: issueId });
      // Yang menunggu menang; sisanya urutan server. TANPA `sort` — alasan sama
      // seperti halaman antrean (lib pra-ES2023, aturan lint). Satu tugas
      // praktis cuma punya satu baris menunggu (constraint parsial), jadi
      // partisi dua `find` ini cukup.
      const hasil = res?.hasil ?? [];
      const menunggu = hasil.find((b) => b.status === "menunggu");
      const terbaru = hasil.find((b) => b.status !== "menunggu");
      setBaris(menunggu ?? terbaru ?? null);
    } catch {
      // Senyap seperti worklog: sidebar tak boleh crash kalau gagal muat.
      // Bedanya dengan halaman antrean: di sini tidak ada pesan gagal, karena
      // satu baris yang hilang lebih murah daripada sidebar yang berteriak.
      setBaris(null);
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug, projectId, issueId]);

  useEffect(() => {
    void muat();
  }, [muat, statusDiStore]);

  if (isLoading || !baris) return <></>;

  const putuskan = async (aksi: "setujui" | "tolak") => {
    setGagal(null);
    if (aksi === "tolak" && !alasan.trim()) {
      setGagal("Alasan penolakan wajib diisi supaya pemohon tahu apa yang harus diperbaiki.");
      return;
    }
    setIsWorking(true);
    try {
      await persetujuanService.putuskan(workspaceSlug, projectId, baris.id, aksi, alasan.trim());
      setelStatus(issueId, aksi === "setujui" ? "disetujui" : "ditolak");
      await muat();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: aksi === "setujui" ? "Disetujui" : "Ditolak",
        message: aksi === "setujui" ? "Penugasan disetujui." : "Penugasan ditolak dengan alasan.",
      });
    } catch (err) {
      const pesan = pesanGagal(err, "Gagal menyimpan keputusan.");
      setGagal(pesan);
      setToast({ type: TOAST_TYPE.ERROR, title: "Gagal menyimpan", message: pesan });
    } finally {
      setIsWorking(false);
    }
  };

  if (baris.status === "disetujui") {
    return (
      <Pill variant={EPillVariant.SUCCESS} size={EPillSize.XS}>
        <CheckCircle2 className="size-3 shrink-0" />
        Penugasan disetujui
      </Pill>
    );
  }

  if (baris.status === "ditolak") {
    return (
      <Pill variant={EPillVariant.ERROR} size={EPillSize.XS}>
        <XCircle className="size-3 shrink-0" />
        Penugasan ditolak{baris.alasan ? `: ${baris.alasan}` : ""}
      </Pill>
    );
  }

  return (
    <div className="flex w-full flex-col gap-2">
      <Pill variant={EPillVariant.WARNING} size={EPillSize.XS}>
        <Clock className="size-3 shrink-0" />
        Menunggu persetujuan atasan
      </Pill>
      <span className="text-[11px] text-tertiary">
        Diajukan oleh {baris.pemohon.nama ?? baris.pemohon.email ?? "—"}. Tugas ini terkunci: belum bisa diubah,
        dipindah status, atau dikerjakan sampai disetujui. Komentar tetap bisa.
      </span>
      {baris.boleh_saya_putuskan && (
        <div className="flex flex-col gap-1.5">
          <textarea
            value={alasan}
            rows={2}
            maxLength={2000}
            onChange={(e) => setAlasan(e.target.value)}
            placeholder="Alasan (wajib kalau menolak)"
            className={inputClass}
          />
          {gagal && (
            <p className="border-red-500/30 bg-red-500/5 text-xs text-red-600 rounded border px-2 py-1">{gagal}</p>
          )}
          <div className="flex items-center gap-1.5">
            <Button variant="primary" size="sm" loading={isWorking} onClick={() => void putuskan("setujui")}>
              Setujui
            </Button>
            <Button variant="error-outline" size="sm" loading={isWorking} onClick={() => void putuskan("tolak")}>
              Tolak
            </Button>
          </div>
        </div>
      )}
    </div>
  );
});
