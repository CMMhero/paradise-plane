/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: penjaga data hidup
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { useKehadiranTersambung } from "@/hooks/use-kehadiran";
import { pasangPenjagaData, SELANG_CADANGAN_MS, segarkanSemua } from "@/lib/data-live";

/**
 * Dipasang sekali di lapisan workspace. Dua tugasnya:
 * - memasang pendengar dokumen (tab kembali terlihat, fokus lepas dari isian);
 * - saat soket live putus, menyegarkan berkala sebagai jaring pengaman. Dengan
 *   soket tersambung tidak ada jam sama sekali: kabar datang sendiri.
 */
export function PenyegarLangsung() {
  const tersambung = useKehadiranTersambung();

  useEffect(() => pasangPenjagaData(), []);

  useEffect(() => {
    if (tersambung) return;
    const jam = setInterval(() => {
      if (document.visibilityState === "visible") void segarkanSemua();
    }, SELANG_CADANGAN_MS);
    return () => clearInterval(jam);
  }, [tersambung]);

  return null;
}
