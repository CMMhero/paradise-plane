/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: aturan God Mode yang dibaca web
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { nilaiAturanWeb } from "@plane/constants";
import type { TKunciAturanWeb, TNilaiAturanWeb } from "@plane/constants";
import { useInstance } from "@/hooks/store/use-instance";

/**
 * Nilai aturan God Mode `web=True` (`paradise_rules` di /api/instances/), bertipe.
 * Sebelum config datang, atau dari server lama, nilainya bawaan yang sama dengan
 * server (cermin di @plane/constants). Panggil dari komponen `observer`.
 *
 * Hanya untuk tampilan. Izin selalu dijaga API; web tidak menghitung ulang izin
 * dari nilai aturan.
 */
export function useAturan() {
  const { config } = useInstance();
  return {
    get: <K extends TKunciAturanWeb>(kunci: K): TNilaiAturanWeb<K> => nilaiAturanWeb(config?.paradise_rules, kunci),
  };
}
