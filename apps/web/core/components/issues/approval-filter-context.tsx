/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: filter lokal tunggu-persetujuan 
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Toggle client-side "hanya tunggu persetujuan" per papan (KEP-25): menyaring
 * baris yang dirender berdasarkan `approval_status` yang sudah ada di payload —
 * tanpa menyentuh mesin filter Plane (store, query, backend). Sengaja lokal:
 * filter penuh butuh dimensi baru di seluruh mesin filter upstream.
 *
 * Yang ditolak (`ditolak`) tidak ikut disaring di sini: sejak keputusan
 * 2026-10-16 tugas ditolak kembali ke draft tak-terlihat (`is_draft=True`)
 * dan memang tidak ada di papan sama sekali — hanya di antrean persetujuan.
 */

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

type TApprovalFilter = {
  hanyaMenunggu: boolean;
  toggle: () => void;
};

const ApprovalFilterContext = createContext<TApprovalFilter>({ hanyaMenunggu: false, toggle: () => {} });

export function ApprovalFilterProvider({ children }: { children: ReactNode }) {
  const [hanyaMenunggu, setHanyaMenunggu] = useState(false);
  // Nilai di-memo: objek inline di `value` membuat SELURUH konsumen render
  // ulang tiap render provider (aturan jsx-no-constructed-context-values).
  const nilai = useMemo<TApprovalFilter>(
    () => ({ hanyaMenunggu, toggle: () => setHanyaMenunggu((v) => !v) }),
    [hanyaMenunggu]
  );
  return <ApprovalFilterContext.Provider value={nilai}>{children}</ApprovalFilterContext.Provider>;
}

export const useApprovalFilter = (): TApprovalFilter => useContext(ApprovalFilterContext);

/** True kalau kartu/baris ini boleh tampil dalam keadaan filter aktif. */
export const lolosFilterApproval = (approvalStatus: string | null | undefined, hanyaMenunggu: boolean): boolean =>
  !hanyaMenunggu || approvalStatus === "menunggu";
