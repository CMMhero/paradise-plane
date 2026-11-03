/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: antrean persetujuan per divisi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Aturan yang ditampilkan (diputuskan user 2026-10-15, disederhanakan 2026-10-16):
 * - Yang butuh persetujuan HANYA staf (member) yang menugaskan ke dirinya sendiri.
 * - Yang menyetujui adalah atasan pembuat di divisinya: supervisor, manager, atau direktur.
 * - Tugas yang ditolak KEMBALI ke draft tak-terlihat; staf mengajukan ulang dari sini.
 * - Penolakan WAJIB beralasan; pembuat tidak boleh menyetujui tugasnya sendiri.
 *
 * Bentuknya sengaja meniru daftar Pages: header sekunder bertab (tab = `?tab=`
 * di URL, jadi bisa dibagikan), lalu `ListLayout` berisi `ListItem` selebar
 * halaman. Tidak ada kartu, lebar maksimum, atau gaya buatan sendiri.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Banner } from "@plane/propel/banner";
import { Button } from "@plane/propel/button";
import { EmptyStateCompact } from "@plane/propel/empty-state";
import { EHeaderVariant, Header } from "@plane/ui";
import { cn } from "@plane/utils";
// components
import { ListLayout } from "@/components/core/list";
import { ViewListLoader } from "@/components/ui/loader/view-list-loader";
// services
import { PersetujuanService } from "@/services/persetujuan.service";
// local imports
import { kunciAntreanProject, pesanGagalPersetujuan, useAntreanPenyetuju } from "./approval-actions";
import { ApprovalQueueRow } from "./approval-queue-row";

const persetujuanService = new PersetujuanService();

type TTabAntrean = "decide" | "mine";

const bacaTab = (nilai: string | null): TTabAntrean => (nilai === "mine" ? "mine" : "decide");

type TApprovalTabNavigationProps = {
  workspaceSlug: string;
  projectId: string;
  tab: TTabAntrean;
  jumlahMenunggu: number | undefined;
};

/** Tab bergaris bawah, sama persis dengan `PageTabNavigation`. */
function ApprovalTabNavigation(props: TApprovalTabNavigationProps) {
  const { workspaceSlug, projectId, tab, jumlahMenunggu } = props;
  const { t } = useTranslation();
  const tabs: { key: TTabAntrean; label: string; jumlah?: number }[] = [
    { key: "decide", label: t("issue.approval.queue.needs_decision"), jumlah: jumlahMenunggu },
    { key: "mine", label: t("issue.approval.queue.my_requests") },
  ];

  return (
    <div className="relative flex h-full items-center">
      {tabs.map((item) => (
        <Link
          key={item.key}
          href={`/${workspaceSlug}/projects/${projectId}/persetujuan?tab=${item.key}`}
          onClick={(e) => {
            if (item.key === tab) e.preventDefault();
          }}
          className="flex h-full flex-col"
        >
          <div
            className={cn("flex flex-1 items-center justify-center gap-1.5 px-4 text-13 font-medium transition-all", {
              "text-accent-primary": item.key === tab,
            })}
          >
            {item.label}
            {!!item.jumlah && (
              <span className="rounded-control bg-layer-3 px-1.5 text-11 text-secondary">{item.jumlah}</span>
            )}
          </div>
          <div
            className={cn("w-full rounded-t border-t-2 border-transparent transition-all", {
              "border-accent-strong": item.key === tab,
            })}
          />
        </Link>
      ))}
    </div>
  );
}

export type TAntreanPersetujuanProps = {
  workspaceSlug: string;
  projectId: string;
};

export const AntreanPersetujuan = observer(function AntreanPersetujuan(props: TAntreanPersetujuanProps) {
  const { workspaceSlug, projectId } = props;
  const { t } = useTranslation();
  const searchParams = useSearchParams();
  const tab = bacaTab(searchParams.get("tab"));

  // Antrean penyetuju selalu diambil: angkanya tampil di tab walau sedang di
  // "Pengajuan saya", dan kuncinya sama dengan yang dipakai papan.
  const penyetuju = useAntreanPenyetuju(workspaceSlug, projectId);
  const pemohon = useSWR(tab === "mine" ? kunciAntreanProject(workspaceSlug, projectId, "pemohon") : null, () =>
    persetujuanService.daftar(workspaceSlug, projectId, { peran: "pemohon" })
  );
  const aktif = tab === "mine" ? pemohon : penyetuju;
  const baris = aktif.data?.hasil ?? [];
  const jumlahMenunggu = penyetuju.data?.hasil.filter((b) => b.status === "menunggu").length;
  const gerbangMati = aktif.data ? !aktif.data.gerbang_aktif : false;

  const isi = () => {
    if (aktif.error)
      return (
        <div className="px-page-x py-4">
          <Banner
            variant="error"
            title={pesanGagalPersetujuan(aktif.error, t("issue.approval.queue.load_failed"))}
            action={
              <Button variant="secondary" size="base" onClick={() => void aktif.mutate()}>
                {t("issue.approval.actions.retry")}
              </Button>
            }
          />
        </div>
      );
    if (!aktif.data) return <ViewListLoader />;
    if (baris.length === 0)
      return (
        <div className="grid h-full w-full place-items-center">
          <EmptyStateCompact
            assetKey="intake"
            title={
              tab === "decide"
                ? t("issue.approval.queue.empty_decision_title")
                : t("issue.approval.queue.empty_mine_title")
            }
            description={
              tab === "decide"
                ? t("issue.approval.queue.empty_decision_description")
                : t("issue.approval.queue.empty_mine_description")
            }
          />
        </div>
      );
    return (
      <ListLayout>
        {baris.map((item) => (
          <ApprovalQueueRow key={item.id} workspaceSlug={workspaceSlug} projectId={projectId} baris={item} />
        ))}
      </ListLayout>
    );
  };

  return (
    <div className="relative flex h-full w-full flex-col overflow-hidden">
      <Header variant={EHeaderVariant.SECONDARY}>
        <Header.LeftItem>
          <ApprovalTabNavigation
            workspaceSlug={workspaceSlug}
            projectId={projectId}
            tab={tab}
            jumlahMenunggu={jumlahMenunggu}
          />
        </Header.LeftItem>
      </Header>
      {gerbangMati && (
        <div className="px-page-x pt-4">
          <Banner variant="warning" title={t("issue.approval.queue.gate_off")} />
        </div>
      )}
      <div className="relative h-full w-full overflow-hidden">{isi()}</div>
    </div>
  );
});
