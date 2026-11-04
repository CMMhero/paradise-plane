/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: undangan kedaluwarsa (KEP-83)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { TOAST_TYPE, setToast } from "@plane/propel/toast";

/** Kode galat 400 dari server saat menerima undangan yang sudah lewat masa berlakunya. */
export const KODE_UNDANGAN_KEDALUWARSA = "INVITE_EXPIRED";

/**
 * True kalau galat dari layanan (bentuk `response.data`, lihat `workspace.service.ts`)
 * adalah undangan kedaluwarsa. Dicocokkan lewat `error_code`, bukan teks pesannya.
 */
export const adalahUndanganKedaluwarsa = (err: unknown): boolean =>
  (err as { error_code?: string } | null | undefined)?.error_code === KODE_UNDANGAN_KEDALUWARSA;

/** Toast baku untuk undangan kedaluwarsa. `t` dari `useTranslation()`. */
export const tampilkanUndanganKedaluwarsa = (t: (key: string) => string): void => {
  setToast({
    type: TOAST_TYPE.ERROR,
    title: t("aturan_tugas_ui.invite_expired_title"),
    message: t("aturan_tugas_ui.invite_expired_message"),
  });
};
