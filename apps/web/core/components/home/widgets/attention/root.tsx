/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: widget "Needs attention" di Home
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Ringkasan singkat pekerjaan yang perlu perhatian: per kelompok jumlah dan
 * paling banyak lima tugas teratas, tiap tugas satu kartu dengan aksi satu klik
 * sesuai kelompoknya (`card.tsx`, `actions.tsx`). Kelompok kosong tidak tampil;
 * kalau semuanya kosong, satu kalimat tenang. Satu panggilan server (lihat
 * `plane/utils/perhatian.py`).
 */

import { observer } from "mobx-react";
import Link from "next/link";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import type { THomeWidgetProps } from "@plane/types";
import { Loader } from "@plane/ui";
import { cn } from "@plane/utils";
// hooks
import { useUser } from "@/hooks/store/user";
// services
import { AttentionService } from "@/services/attention.service";
import type { TAttention, TAttentionGroup } from "@/services/attention.service";
// local
import type { TOnAct } from "./actions";
import { AttentionCard, ALERT_GROUPS } from "./card";
import type { TAttentionPatch } from "./data";
import { useAttentionDismissed } from "./use-dismissed";

const attentionService = new AttentionService();

/** Jendela `due_soon` bawaan, untuk server lama yang belum mengirim `lookahead_days`. */
const DEFAULT_LOOKAHEAD_DAYS = 7;
/** Tinggi satu kartu kelompok yang penuh: judul 40px + 5 kartu (BATAS_ITEM di
 * server) x ~100px (judul, alasan, baris tombol) + kaki "View all" 34px. Kerangka setinggi ini, bukan separuhnya,
 * karena kartu yang penuh adalah kasus biasa; kerangka yang lebih pendek membuat
 * Quick links dan widget di bawahnya terdorong ~400px saat datanya tiba. */
const KERANGKA_KARTU = "574px";

export const AttentionWidget = observer(function AttentionWidget(props: THomeWidgetProps) {
  const { workspaceSlug } = props;
  const { t } = useTranslation();
  const { data: currentUser } = useUser();
  const { data, error, mutate } = useSWR(
    `HOME_ATTENTION_${workspaceSlug}`,
    () => attentionService.getAttention(workspaceSlug),
    {
      revalidateOnFocus: true,
      revalidateIfStale: true,
      dedupingInterval: 30_000,
    }
  );

  // Belum ada data: kerangka setinggi widget supaya Home tidak melompat saat datanya tiba.
  // Gagal memuat: satu baris pesan dengan tombol coba lagi, bukan widget yang menghilang.
  const { isDismissed, dismiss } = useAttentionDismissed(workspaceSlug, currentUser?.id);
  // Kartu yang saya sembunyikan keluar dari daftar dan dari jumlahnya; yang
  // tidak terkirim (lewat batas lima) tetap dihitung server.
  const groups = (data?.groups ?? []).flatMap((group) => {
    const items = group.items.filter((item) => !isDismissed(group.key, item));
    const count = group.count - (group.items.length - items.length);
    return count > 0 ? [Object.assign({}, group, { items, count })] : [];
  });

  // Jalankan aksi dengan pembaruan optimistis: kartu berubah dulu, balasan server
  // menimpanya, dan gagal berarti kembali ke keadaan semula (galat sudah di-toast).
  const handleAct: TOnAct = async (patch, run) => {
    let berhasil = false;
    try {
      await mutate(
        async () => {
          berhasil = await run();
          if (!berhasil) throw new Error("aksi gagal");
          return undefined;
        },
        {
          optimisticData: patch && data ? (patch as TAttentionPatch)(data as TAttention) : undefined,
          rollbackOnError: true,
          populateCache: false,
          revalidate: true,
        }
      );
    } catch {
      // `run` sudah menampilkan pesan galatnya.
    }
    return berhasil;
  };

  const viewAllHref = (group: TAttentionGroup): string | null => {
    if (group.key === "decide")
      return group.top_project_id ? `/${workspaceSlug}/projects/${group.top_project_id}/persetujuan` : null;
    if (["overdue_mine", "due_soon", "rejected", "waiting_mine"].includes(group.key) && currentUser)
      return `/${workspaceSlug}/profile/${currentUser.id}/assigned`;
    return null;
  };

  return (
    <section aria-labelledby="home-attention-title" className="flex flex-col gap-3">
      <h2 id="home-attention-title" className="text-14 font-semibold text-primary">
        {t("attention_ui.title")}
      </h2>
      {!data ? (
        error ? (
          <div
            role="alert"
            className="flex flex-wrap items-center justify-between gap-2 rounded-card border border-subtle px-4 py-3 text-13 text-tertiary"
          >
            <span>{t("attention_ui.load_failed")}</span>
            <Button variant="secondary" size="base" onClick={() => void mutate()}>
              {t("common.retry")}
            </Button>
          </div>
        ) : (
          <Loader className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <span className="sr-only">{t("common.loading")}</span>
            <Loader.Item height={KERANGKA_KARTU} />
            <Loader.Item height={KERANGKA_KARTU} />
          </Loader>
        )
      ) : groups.length === 0 ? (
        <p className="rounded-card border border-subtle px-4 py-3 text-13 text-tertiary">{t("attention_ui.empty")}</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {groups.map((group) => (
            <AttentionGroup
              key={group.key}
              group={group}
              workspaceSlug={workspaceSlug}
              viewAllHref={viewAllHref(group)}
              lookaheadDays={data?.lookahead_days ?? DEFAULT_LOOKAHEAD_DAYS}
              onAct={handleAct}
              onDismiss={dismiss}
            />
          ))}
        </div>
      )}
    </section>
  );
});

type TGroupProps = {
  group: TAttentionGroup;
  workspaceSlug: string;
  viewAllHref: string | null;
  lookaheadDays: number;
  onAct: TOnAct;
  onDismiss: ReturnType<typeof useAttentionDismissed>["dismiss"];
};

function AttentionGroup({ group, workspaceSlug, viewAllHref, lookaheadDays, onAct, onDismiss }: TGroupProps) {
  const { t } = useTranslation();
  const isAlert = ALERT_GROUPS.has(group.key);
  const hidden = group.count - group.items.length;

  return (
    <div className="flex min-w-0 flex-col rounded-card border border-subtle bg-layer-1">
      <div className="flex items-center justify-between gap-2 px-4 py-2.5">
        <h3 className="min-w-0 truncate text-13 font-semibold text-primary">
          {t(`attention_ui.group_${group.key}`, { days: lookaheadDays })}
        </h3>
        <span className={cn("text-13 font-semibold", isAlert ? "text-danger-primary" : "text-secondary")}>
          {group.count}
        </span>
      </div>
      <ul className="divide-y divide-subtle border-t border-subtle">
        {group.items.map((item) => (
          <AttentionCard
            key={item.key}
            item={item}
            workspaceSlug={workspaceSlug}
            groupKey={group.key}
            onAct={onAct}
            onDismiss={() => onDismiss(group.key, item)}
          />
        ))}
      </ul>
      {(viewAllHref || hidden > 0) && (
        <div className="flex items-center justify-between gap-2 border-t border-subtle px-4 py-2 text-12 text-tertiary">
          <span>{hidden > 0 ? t("attention_ui.more", { count: hidden }) : ""}</span>
          {viewAllHref && (
            <Link href={viewAllHref} className="font-medium text-accent-primary hover:underline">
              {t("attention_ui.view_all")}
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
