/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: izin per sumber (KEP-85)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import useSWR, { type SWRConfiguration } from "swr";
// hooks
import { useUser } from "@/hooks/store/user";
// lib
import {
  kunciIzinSumber,
  nilaiIzinIsi,
  nilaiIzinStruktur,
  simpanIzinSumber,
  type TSumberIzin,
} from "@/lib/izin-sumber";
// services
import { IzinSumberService, type TKunciIzinIsi, type TKunciIzinStruktur } from "@/services/izin-sumber.service";

const izinSumberService = new IzinSumberService();

/**
 * Satu kunci per (workspace, project), dipakai bersama oleh semua baris yang
 * memanggilnya. Fokus tab SENGAJA memicu ambil ulang: data ini membawa bendera
 * izin, dan setelan God Mode bisa berubah selama tab terbuka.
 */
const OPSI_IZIN: SWRConfiguration = {
  revalidateIfStale: false,
  revalidateOnFocus: true,
};

export type TIzinSumber = {
  memuat: boolean;
  /** Boleh menjalankan aksi isi `kunci` atas sumber ini? (module, page, view, komentar) */
  boleh: (kunci: TKunciIzinIsi, sumber: TSumberIzin) => boolean;
  /** Boleh menjalankan aksi struktur project `kunci`? (state/label, setelan, arsip, trash) */
  struktur: (kunci: TKunciIzinStruktur) => boolean;
};

/**
 * Izin saya atas sumber selain work item (KEP-85), dibaca dari
 * `GET workspaces/<slug>/izin-saya/?project_id=`. Penegaknya server
 * (`plane/utils/izin_sumber.py`); hook ini hanya menyembunyikan aksi yang pasti
 * ditolak. Selama memuat: pemilik/terlibat lolos, selainnya tertutup.
 *
 * Tanpa `projectId` = sumber tingkat workspace (view workspace).
 */
export const useIzinSumber = (workspaceSlug: string | undefined | null, projectId?: string | null): TIzinSumber => {
  const { data: currentUser } = useUser();
  const kunci = workspaceSlug ? kunciIzinSumber(workspaceSlug, projectId) : null;
  const { data, isLoading } = useSWR(
    kunci,
    async () => {
      const izin = await izinSumberService.izinSaya(workspaceSlug as string, projectId);
      simpanIzinSumber(kunci as string, izin);
      return izin;
    },
    OPSI_IZIN
  );
  const adaProject = !!projectId;
  return {
    memuat: !kunci || isLoading,
    boleh: (kunciIzin, sumber) => nilaiIzinIsi(data, kunciIzin, sumber, currentUser?.id, adaProject),
    struktur: (kunciIzin) => nilaiIzinStruktur(data, kunciIzin),
  };
};
