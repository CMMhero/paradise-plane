/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: konteks papan seret-lepas organisasi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Dipisah dari berkas komponen supaya Fast Refresh tetap hot-swap.
 */

import { createContext, useContext } from "react";
import type { TAnggotaHierarki } from "@plane/services";
import type { TAsal, TTujuan } from "./papan-logika";

export type TPemilihTujuan = { orangId: string; asal?: TAsal; mode: "tambah" | "pindah" };

export type TKonteksPapan = {
  /** Anggota aktif (bukan akun terhapus) per id: sumber posisi lengkap tiap orang. */
  orangById: Map<string, TAnggotaHierarki>;
  /** Satu seretan / pilihan menu. `salin` = tambah walau asalnya sejenis. */
  eksekusi: (orangId: string, asal: TAsal | undefined, tujuan: TTujuan, salin: boolean) => Promise<void>;
  /** Lepas dari satu tempat saja. */
  cabut: (orangId: string, asal: TAsal) => Promise<void>;
  bukaPemilih: (p: TPemilihTujuan) => void;
  namaTempat: (asal: TAsal) => string;
};

export const KonteksPapan = createContext<TKonteksPapan | null>(null);

export function usePapan(): TKonteksPapan {
  const nilai = useContext(KonteksPapan);
  if (!nilai) throw new Error("usePapan must be used inside <KonteksPapan.Provider>");
  return nilai;
}
