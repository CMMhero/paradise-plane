/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pesan galat dari server untuk toast
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

type TGalatServer = { error?: unknown; detail?: unknown; assignee_ids?: unknown };

const teks = (nilai: unknown): string | undefined => {
  if (typeof nilai === "string" && nilai.trim()) return nilai;
  if (Array.isArray(nilai) && typeof nilai[0] === "string") return nilai[0];
  return undefined;
};

/**
 * Pesan yang dikirim server untuk penolakan (403/400), atau undefined kalau tidak ada.
 *
 * Server menjelaskan sebabnya ("Staf hanya boleh mengajak rekan ..."), tapi toast
 * generik "update failed" membuangnya, dan orang tidak tahu apa yang harus diubah.
 * Dipakai di toast gagal-ubah work item; selain itu toast tetap generik.
 */
export const pesanGalatServer = (galat: unknown): string | undefined => {
  if (!galat || typeof galat !== "object") return undefined;
  const g = galat as TGalatServer;
  return teks(g.error) ?? teks(g.detail) ?? teks(g.assignee_ids);
};
