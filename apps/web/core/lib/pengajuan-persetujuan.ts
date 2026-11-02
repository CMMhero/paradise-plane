/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pengajuan persetujuan (KEP-55)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Saat staf menggeser tugasnya ke selesai, server MENAHAN perpindahan itu dan
 * membuat pengajuan. Store (bukan komponen) yang pertama tahu, lewat balasan
 * PATCH, tapi store tidak punya `t` untuk toast. Jadi store memancarkan event
 * ini, dan `PendengarPengajuanPersetujuan` di lapisan workspace yang menampilkan
 * toast-nya. Semua jalur (seret kanban, dropdown status, detail, peek) lewat
 * store yang sama, jadi satu pendengar menutup semuanya.
 */

export const EVENT_PENGAJUAN_PERSETUJUAN = "paradise:pengajuan-persetujuan";

export type TDetailPengajuanPersetujuan = { issueId: string };

export const pancarkanPengajuanPersetujuan = (issueId: string) => {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<TDetailPengajuanPersetujuan>(EVENT_PENGAJUAN_PERSETUJUAN, { detail: { issueId } })
  );
};
