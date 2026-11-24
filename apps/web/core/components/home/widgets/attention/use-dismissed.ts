/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu "Needs attention" yang disembunyikan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * "Sembunyikan" menyimpan tanda tangan keadaan kartu (status, tenggat, waktu
 * kejadian). Kartu muncul lagi begitu tanda tangannya berubah, jadi yang
 * disembunyikan tidak pernah menutupi perubahan baru. Disimpan di
 * localStorage per akun dan workspace: murni preferensi tampilan, tidak perlu
 * migrasi atau endpoint, dan ikut hilang di perangkat lain tanpa merugikan
 * siapa pun karena sumber kebenarannya tetap server. Entri yang lebih tua dari
 * batas hari dibuang saat dibaca; batasnya aturan God Mode ATTENTION_DISMISS_DAYS
 * (bawaan 30).
 */

import { useCallback, useState } from "react";
import { useAturan } from "@/hooks/use-aturan";
import type { TAttentionGroupKey, TAttentionItem } from "@/services/attention.service";

type TEntri = { sig: string; at: number };
type TPeta = Record<string, TEntri>;

const kunciPenyimpanan = (slug: string, userId: string) => `paradise:attention-dismissed:${slug}:${userId}`;
const kunciKartu = (group: TAttentionGroupKey, item: TAttentionItem) => `${group}:${item.key}`;
const tandaTangan = (item: TAttentionItem) =>
  [item.state_id, item.target_date, item.requested_at ?? item.decided_at ?? item.mentioned_at ?? ""].join("|");

const baca = (kunci: string, batasHari: number): TPeta => {
  try {
    const mentah = JSON.parse(window.localStorage.getItem(kunci) ?? "{}") as TPeta;
    const batas = Date.now() - batasHari * 86_400_000;
    return Object.fromEntries(Object.entries(mentah).filter(([, e]) => e.at > batas));
  } catch {
    return {};
  }
};

export const useAttentionDismissed = (workspaceSlug: string, userId: string | undefined) => {
  const kunci = kunciPenyimpanan(workspaceSlug, userId ?? "");
  const { get } = useAturan();
  const [peta, setPeta] = useState<TPeta>(() => (userId ? baca(kunci, get("ATTENTION_DISMISS_DAYS")) : {}));

  const isDismissed = useCallback(
    (group: TAttentionGroupKey, item: TAttentionItem) => peta[kunciKartu(group, item)]?.sig === tandaTangan(item),
    [peta]
  );

  const simpan = useCallback(
    (baru: TPeta) => {
      setPeta(baru);
      try {
        window.localStorage.setItem(kunci, JSON.stringify(baru));
      } catch {
        // Penyimpanan penuh atau diblokir: kartu tetap tersembunyi sampai muat ulang.
      }
    },
    [kunci]
  );

  const dismissMany = useCallback(
    (targets: { group: TAttentionGroupKey; item: TAttentionItem }[]) => {
      if (targets.length === 0) return;
      const at = Date.now();
      const tambahan = Object.fromEntries(
        targets.map(({ group, item }) => [kunciKartu(group, item), { sig: tandaTangan(item), at }])
      );
      simpan({ ...peta, ...tambahan });
    },
    [peta, simpan]
  );

  const dismiss = useCallback(
    (group: TAttentionGroupKey, item: TAttentionItem) => dismissMany([{ group, item }]),
    [dismissMany]
  );

  return { isDismissed, dismiss, dismissMany };
};
