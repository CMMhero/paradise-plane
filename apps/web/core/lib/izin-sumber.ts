/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: izin per sumber (KEP-85)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observable, runInAction } from "mobx";
import type { TIzinSaya, TKunciIzinIsi, TKunciIzinStruktur } from "@/services/izin-sumber.service";

/** Nilai aturan isi; cermin `IZIN_*` di `apps/api/plane/utils/saklar_instance.py`. */
export const IZIN_PEMILIK_ATASAN = 0;
export const IZIN_PEMILIK_SAJA = 1;
export const IZIN_SEMUA_ANGGOTA = 2;

export type TSumberIzin = {
  /** Pembuat / owner sumber. null = tanpa pemilik (pembuatnya dihapus). */
  pemilikId?: string | null;
  /** Orang yang ditugaskan di dalamnya (lead & anggota module). */
  terlibatIds?: (string | null | undefined)[] | null;
};

/**
 * Nilai satu aturan ISI di klien, cermin PERSIS `PenilaiIzin.boleh` di
 * `apps/api/plane/utils/izin_sumber.py`. Server tetap penegaknya; ini hanya
 * supaya tombol yang pasti ditolak tidak tampil.
 *
 * `adaProject` = false untuk sumber tingkat workspace (view workspace): atasan
 * di sana dihitung server saja, jadi aturan 0 di klien = admin atau pemilik.
 * Atasan yang sebenarnya boleh mungkin tidak melihat tombolnya; itu disengaja.
 */
export const nilaiIzinIsi = (
  izin: TIzinSaya | undefined | null,
  kunci: TKunciIzinIsi,
  sumber: TSumberIzin,
  idSaya: string | undefined | null,
  adaProject: boolean
): boolean => {
  if (!idSaya) return false;
  if (sumber.pemilikId === idSaya || (sumber.terlibatIds ?? []).includes(idSaya)) return true;
  // Belum dimuat: pemilik lolos di atas, selainnya tertutup dulu.
  if (!izin) return false;
  if (izin.admin) return true;
  const aturan = izin.aturan[kunci] ?? IZIN_PEMILIK_ATASAN;
  if (aturan === IZIN_PEMILIK_SAJA) return false;
  if (aturan === IZIN_SEMUA_ANGGOTA) return !adaProject || izin.anggota;
  if (!adaProject) return false;
  if (!sumber.pemilikId) return !!izin.mengawasi_project;
  return izin.bawahan_ids.includes(sumber.pemilikId);
};

/** Aturan struktur: server sudah menjawab per kunci. Belum dimuat = tertutup. */
export const nilaiIzinStruktur = (izin: TIzinSaya | undefined | null, kunci: TKunciIzinStruktur): boolean =>
  !!izin && (izin.admin || !!izin.struktur[kunci]);

export const kunciIzinSumber = (workspaceSlug: string, projectId?: string | null) =>
  `IZIN_SAYA:${workspaceSlug}:${projectId ?? "-"}`;

/**
 * Salinan reaktif balasan `izin-saya/` per (workspace, project), untuk store
 * MobX yang tidak bisa memanggil hook (page). Diisi oleh `useIzinSumber`.
 */
const simpananIzin = observable.map<string, TIzinSaya>({}, { deep: false });

export const simpanIzinSumber = (kunci: string, izin: TIzinSaya) =>
  runInAction(() => {
    simpananIzin.set(kunci, izin);
  });

export const bacaIzinSumber = (workspaceSlug: string | undefined | null, projectId?: string | null) =>
  workspaceSlug ? simpananIzin.get(kunciIzinSumber(workspaceSlug, projectId)) : undefined;
