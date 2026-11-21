/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: bentuk cermin web aturan God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Cermin web untuk aturan `web=True` di apps/api/plane/utils/aturan. Bawaannya
 * HARUS sama dengan `default=` Python (aturan.test.ts mencocokkannya), karena web
 * memakainya sebelum /api/instances/ menjawab dan saat server lama tidak mengirimnya.
 */

/** `T` = bentuk nilai, `C` = satu butir pilihan (sama dengan `T`, kecuali untuk daftar). */
export type TAturanWebDef<T, C = T> = {
  default: T;
  /** Nilai yang sah. Nilai server di luar daftar ini diabaikan (pakai `default`). */
  choices?: readonly C[];
};

export const boolWeb = (bawaan: boolean): TAturanWebDef<boolean> => ({ default: bawaan });

export const angkaWeb = (bawaan: number): TAturanWebDef<number> => ({ default: bawaan });

export const teksWeb = (bawaan: string): TAturanWebDef<string> => ({ default: bawaan });

export const pilihanWeb = <T extends string | number>(choices: readonly T[], bawaan: T): TAturanWebDef<T> => ({
  default: bawaan,
  choices,
});

export const daftarWeb = <T extends string>(
  choices: readonly T[],
  bawaan: readonly T[]
): TAturanWebDef<readonly T[], T> => ({
  default: bawaan,
  choices,
});
