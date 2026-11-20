/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: penjaga data hidup
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { useKehadiranDiaktifkan, useKehadiranTersambung } from "@/hooks/use-kehadiran";
import { jendelaAktif, pasangPenjagaData, SELANG_CADANGAN_MS, segarkanSenyap } from "@/lib/data-live";

/**
 * Dipasang sekali di lapisan workspace. Dua tugasnya:
 * - memasang pendengar dokumen (tab kembali terlihat, fokus lepas dari isian);
 * - saat soket live yang SUDAH dinyalakan putus, menyegarkan senyap tiap
 *   `SELANG_CADANGAN_MS`, hanya selama jendela terlihat dan berfokus. Dengan soket
 *   tersambung, atau realtime tidak pernah dinyalakan, tidak ada jam sama sekali.
 */
export function PenyegarLangsung() {
  const tersambung = useKehadiranTersambung();
  const diaktifkan = useKehadiranDiaktifkan();

  useEffect(() => pasangPenjagaData(), []);

  useEffect(() => {
    if (!diaktifkan || tersambung) return;
    const jam = setInterval(() => {
      if (jendelaAktif()) void segarkanSenyap();
    }, SELANG_CADANGAN_MS);
    return () => clearInterval(jam);
  }, [diaktifkan, tersambung]);

  return null;
}
