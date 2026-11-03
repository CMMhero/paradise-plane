/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: volume suara pemberitahuan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Volume (0..100) dan bisu disimpan per akun di `profile.theme`, sama seperti
 * preferensi tampilan KEP-64, jadi ikut ke perangkat lain. Bawaan akun baru
 * diatur di God Mode > Members > Defaults. Cermin `SUARA_PABRIK` di
 * plane/utils/bawaan_member.py.
 */

import type { IUserTheme } from "@plane/types";

export type TSuara = { volume: number; bisu: boolean };

export const SUARA_PABRIK: TSuara = { volume: 80, bisu: false };

const volumeSah = (v: unknown): v is number => typeof v === "number" && Number.isInteger(v) && v >= 0 && v <= 100;

/**
 * Baca setelan suara dari profil. Kosong atau rusak = pabrik.
 *
 * `bisuLama` adalah saklar lama per peramban (localStorage), dipakai HANYA kalau
 * profil belum pernah menyimpan `suara_bisu`. Tanpa itu orang yang dulu
 * mematikan bunyi tiba-tiba mendengarnya lagi sesudah pembaruan ini.
 */
export function bacaSuara(theme: Partial<IUserTheme> | undefined, bisuLama?: boolean): TSuara {
  const bisu = typeof theme?.suara_bisu === "boolean" ? theme.suara_bisu : (bisuLama ?? SUARA_PABRIK.bisu);
  return {
    volume: volumeSah(theme?.volume_suara) ? theme.volume_suara : SUARA_PABRIK.volume,
    bisu,
  };
}

/** Volume elemen audio (0..1). Bisu atau volume 0 = tidak berbunyi sama sekali. */
export const volumeAudio = (suara: TSuara): number => (suara.bisu ? 0 : suara.volume / 100);
