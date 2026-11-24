/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: perubahan lokal untuk kartu "Needs attention"
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Fungsi murni atas balasan server, dipakai sebagai `optimisticData` SWR:
 * kartu berubah saat tombol ditekan, lalu balasan server menimpanya.
 */

import type { TAttention, TAttentionGroupKey, TAttentionItem } from "@/services/attention.service";

export type TAttentionPatch = (data: TAttention) => TAttention;

/** Kartu hilang dari kelompoknya; jumlah kelompok dan total ikut turun. */
export const removeItem =
  (groupKey: TAttentionGroupKey, key: string): TAttentionPatch =>
  (data) => ({
    ...data,
    total: Math.max(0, data.total - 1),
    groups: data.groups.map((g) =>
      g.key === groupKey ? { ...g, count: Math.max(0, g.count - 1), items: g.items.filter((i) => i.key !== key) } : g
    ),
  });

/** Banyak kartu hilang sekaligus ("Dismiss all"); jumlah kelompok dan total ikut turun. */
export const removeItems =
  (targets: { group: TAttentionGroupKey; key: string }[]): TAttentionPatch =>
  (data) => {
    const dibuang = new Set(targets.map((t) => `${t.group}:${t.key}`));
    let berkurang = 0;
    const groups = data.groups.map((g) => {
      const items = g.items.filter((i) => !dibuang.has(`${g.key}:${i.key}`));
      const hilang = g.items.length - items.length;
      berkurang += hilang;
      return hilang ? { ...g, count: Math.max(0, g.count - hilang), items } : g;
    });
    return { ...data, total: Math.max(0, data.total - berkurang), groups };
  };

export const updateItem =
  (groupKey: TAttentionGroupKey, key: string, changes: Partial<TAttentionItem>): TAttentionPatch =>
  (data) => ({
    ...data,
    groups: data.groups.map((g) =>
      g.key === groupKey ? { ...g, items: g.items.map((i) => (i.key === key ? { ...i, ...changes } : i)) } : g
    ),
  });
