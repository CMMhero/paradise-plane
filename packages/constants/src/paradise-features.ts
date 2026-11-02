/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: modul yang dinyalakan/dimatikan di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type {
  IIssueDisplayProperties,
  TIssueGroupByOptions,
  TIssueOrderByOptions,
  TParadiseModule,
} from "@plane/types";

/**
 * Nilai bawaan tiap modul, dipakai sebelum server menjawab atau bila server lama
 * tak mengirim modulnya. Cermin `_MODUL_BAWAAN` di
 * apps/api/plane/utils/saklar_instance.py.
 *
 * Time tracking dan estimates bawaannya mati (keputusan user 30 Okt 2026).
 * Cycles, work item types, dan templates DICABUT 2 Nov 2026 (KEP-53): bukan modul
 * lagi, tak bisa dinyalakan dari God Mode. Lihat `PARADISE_REMOVED`.
 */
export const PARADISE_MODULE_DEFAULTS: Record<TParadiseModule, boolean> = {
  // Sidebar utama
  inbox: true,
  your_work: true,
  stickies: true,
  drafts: true,
  quick_links: true,
  // Menu workspace
  dashboards: true,
  initiatives: false,
  views: true,
  analytics: true,
  chat: true,
  wiki: true,
  archives: true,
  // Tab project
  work_items: true,
  modules: true,
  pages: true,
  intake: true,
  approvals: true,
  // Fitur di dalam work item & setelan project
  time_tracking: false,
  estimates: false,
};

/**
 * Salinan `paradise_modules` dari /api/instances/, untuk pemanggil di luar React
 * (helper, store, konstanta) yang tak bisa memakai hook instance. Diisi
 * `setParadiseFeatureState` saat instance store menerima config, dan
 * InstanceWrapper menahan render sampai itu terjadi, jadi halaman tidak pernah
 * membaca nilai sebelum server menjawab. Komponen React tetap memakai
 * `useParadiseModules` supaya ikut berubah lewat MobX.
 */
let modulDariServer: Partial<Record<TParadiseModule, boolean>> = {};

/** Dipanggil instance store tiap kali `paradise_modules` diterima. */
export const setParadiseFeatureState = (modules: Partial<Record<TParadiseModule, boolean>> | undefined): void => {
  modulDariServer = { ...modules };
};

export const isParadiseModuleActive = (module: TParadiseModule): boolean =>
  modulDariServer[module] ?? PARADISE_MODULE_DEFAULTS[module];

/**
 * Penanda fitur yang dicabut (KEP-53, 2 Nov 2026: cycles, work item types,
 * templates). Di peta gerbang mana pun nilai ini berarti "selalu mati", apa pun
 * isi God Mode. Data lama di server tidak dihapus, hanya tak punya pintu lagi.
 */
export const PARADISE_REMOVED = false;

/** Modul pemilik sesuatu, atau `PARADISE_REMOVED` bila fiturnya sudah dicabut. */
export type TParadiseGate = TParadiseModule | typeof PARADISE_REMOVED;

export const isParadiseGateActive = (gate: TParadiseGate): boolean =>
  gate === PARADISE_REMOVED ? false : isParadiseModuleActive(gate);

/** Nama lama fitur (camelCase) yang masih dipakai pemanggil -> modul God Mode. */
const MODUL_PER_FITUR = {
  timeTracking: "time_tracking",
  estimates: "estimates",
} as const satisfies Record<string, TParadiseModule>;

export type TParadiseFeature = keyof typeof MODUL_PER_FITUR;

export const isParadiseFeatureEnabled = (feature: TParadiseFeature): boolean =>
  isParadiseModuleActive(MODUL_PER_FITUR[feature]);

/**
 * Properti tampilan work item (Display properties, kolom spreadsheet, chip di
 * list/kanban) milik modul yang bisa dimatikan. Modul mati = propertinya hilang
 * dari semua layout, termasuk nilai lama yang masih tersimpan di filter user.
 */
const MODUL_PER_PROPERTI_TAMPILAN: Partial<Record<keyof IIssueDisplayProperties, TParadiseGate>> = {
  estimate: "estimates",
  cycle: PARADISE_REMOVED,
  modules: "modules",
  issue_type: PARADISE_REMOVED,
};

const MODUL_PER_GROUP_BY: Partial<Record<NonNullable<TIssueGroupByOptions>, TParadiseGate>> = {
  cycle: PARADISE_REMOVED,
  module: "modules",
};

const MODUL_PER_ORDER_BY: Partial<Record<TIssueOrderByOptions, TParadiseGate>> = {
  estimate_point__key: "estimates",
  "-estimate_point__key": "estimates",
  issue_cycle__cycle__name: PARADISE_REMOVED,
  "-issue_cycle__cycle__name": PARADISE_REMOVED,
  issue_module__module__name: "modules",
  "-issue_module__module__name": "modules",
};

const modulAktifUntuk = <K extends string>(peta: Partial<Record<K, TParadiseGate>>, key: K | null | undefined) => {
  if (!key || !Object.hasOwn(peta, key)) return true;
  const gate = peta[key];
  return gate === undefined ? true : isParadiseGateActive(gate);
};

export const isDisplayPropertyAvailable = (key: keyof IIssueDisplayProperties): boolean =>
  modulAktifUntuk(MODUL_PER_PROPERTI_TAMPILAN, key);

export const isGroupByAvailable = (key: TIssueGroupByOptions | undefined): boolean =>
  modulAktifUntuk(MODUL_PER_GROUP_BY, key);

export const isOrderByAvailable = (key: TIssueOrderByOptions | undefined): boolean =>
  modulAktifUntuk(MODUL_PER_ORDER_BY, key);

/**
 * Kunci analytics (sumbu X/grup chart `ChartXAxisProperty`, kartu ringkasan
 * `total_*`) milik modul yang bisa dimatikan.
 */
const MODUL_PER_KUNCI_ANALYTICS: Partial<Record<string, TParadiseGate>> = {
  ESTIMATE_POINTS: "estimates",
  CYCLES: PARADISE_REMOVED,
  MODULES: "modules",
  total_cycles: PARADISE_REMOVED,
  total_intake: "intake",
};

export const isAnalyticsKeyAvailable = (key: string): boolean => modulAktifUntuk(MODUL_PER_KUNCI_ANALYTICS, key);
