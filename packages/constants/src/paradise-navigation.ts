/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: satu sumber untuk modul dan menu Paradise
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Dari sini diturunkan: bawaan modul di web (`PARADISE_MODULE_DEFAULTS`), baris
 * God Mode > Modules > Visibility, item sidebar workspace milik Paradise,
 * peta kunci menu -> modul di web, perintah "Go to" Power K beserta gerbang
 * modulnya, dan daftar menu yang bisa disematkan di God Mode > People.
 *
 * Sisi API ditulis Python, jadi tidak bisa membaca berkas ini. Cerminnya
 * (`_MODUL_BAWAAN` di plane/utils/saklar_instance.py, `NAV_PRIBADI`/`NAV_WORKSPACE`
 * di plane/utils/bawaan_member.py, `UserPreferenceKeys` di db/models/workspace.py)
 * dicocokkan oleh tests/paradise-navigation.test.ts.
 *
 * Menu bawaan Plane (Home, Inbox, Views, Archives, ...) TIDAK dipindah ke sini.
 */

import { EUserWorkspaceRoles } from "@plane/types";
import type { TParadiseModule } from "@plane/types";

export type TParadiseModuleGroup = "sidebar" | "workspace" | "project" | "work_item";

/**
 * Semua modul God Mode, urutan tampil di Visibility. `defaultEnabled` dipakai
 * sebelum server menjawab atau bila server lama tak mengirim modulnya.
 * Time tracking dan estimates mati (keputusan user 30 Okt 2026); initiatives
 * memang tersembunyi sejak awal.
 */
export const PARADISE_MODULES: Record<TParadiseModule, { group: TParadiseModuleGroup; defaultEnabled: boolean }> = {
  inbox: { group: "sidebar", defaultEnabled: true },
  your_work: { group: "sidebar", defaultEnabled: true },
  stickies: { group: "sidebar", defaultEnabled: true },
  drafts: { group: "sidebar", defaultEnabled: true },
  quick_links: { group: "sidebar", defaultEnabled: true },
  // Bagian "Projects" di sidebar (daftar departemen per divisi), bukan menu berupa tautan.
  departments: { group: "sidebar", defaultEnabled: true },
  dashboards: { group: "workspace", defaultEnabled: true },
  initiatives: { group: "workspace", defaultEnabled: false },
  views: { group: "workspace", defaultEnabled: true },
  analytics: { group: "workspace", defaultEnabled: true },
  chat: { group: "workspace", defaultEnabled: true },
  wiki: { group: "workspace", defaultEnabled: true },
  archives: { group: "workspace", defaultEnabled: true },
  work_items: { group: "project", defaultEnabled: true },
  modules: { group: "project", defaultEnabled: true },
  pages: { group: "project", defaultEnabled: true },
  intake: { group: "project", defaultEnabled: true },
  approvals: { group: "project", defaultEnabled: true },
  time_tracking: { group: "work_item", defaultEnabled: false },
  estimates: { group: "work_item", defaultEnabled: false },
};

/** Modul satu kelompok, urutan registri. */
export const paradiseModulesInGroup = (group: TParadiseModuleGroup): TParadiseModule[] =>
  (Object.keys(PARADISE_MODULES) as TParadiseModule[]).filter((m) => PARADISE_MODULES[m].group === group);

const ANGGOTA = [EUserWorkspaceRoles.ADMIN, EUserWorkspaceRoles.MEMBER];

/**
 * Menu workspace milik Paradise, urutan sidebar. Semuanya selalu tampil bagi
 * yang lolos `access` dan modulnya menyala, tersemat atau tidak: orang tak akan
 * menyematkan fitur yang belum ia tahu ada.
 *
 * - `module`: saklar God Mode yang menyembunyikan menu, halaman, dan perintahnya.
 * - `palette`: perintah "Go to" di Power K. `titleKey` default
 *   `power_k.navigation_actions.<id>`.
 */
export const PARADISE_NAV_ITEMS = [
  // KPI (Paradise 2.9): isinya dibatasi server menurut jenjang. Analitik dan
  // Dasbor Divisi adalah tab di halaman ini.
  {
    key: "kinerja",
    module: "dashboards",
    labelTranslationKey: "kinerja.nav",
    href: "/kinerja/",
    access: ANGGOTA,
    palette: { id: "nav_kinerja", titleKey: "kinerja.go_to" },
  },
  {
    key: "initiatives",
    module: "initiatives",
    // `common.initiatives`: kunci ini hanya ada di bawah `common.` di locale.
    labelTranslationKey: "common.initiatives",
    href: "/initiatives/",
    access: ANGGOTA,
    palette: { id: "nav_initiatives" },
  },
  // Hanya tampil bagi yang punya wewenang memutuskan (aturan tambahan di web).
  {
    key: "persetujuan",
    module: "approvals",
    labelTranslationKey: "persetujuan_p29.nav",
    href: "/persetujuan/",
    access: ANGGOTA,
    palette: { id: "nav_workspace_approvals", titleKey: "persetujuan_p29.power_k_title" },
  },
  // Permintaan masuk Intake departemen tujuan.
  {
    key: "tugas_lintas_divisi",
    module: "intake",
    labelTranslationKey: "persetujuan_p29.nav_requests",
    href: "/tugas-lintas-divisi/",
    access: ANGGOTA,
  },
  // "chat_nav"/"wiki_nav", bukan "chat"/"wiki": kunci daun itu bentrok dengan
  // namespace `chat.*`/`wiki.*` di sync:check.
  {
    key: "chat",
    module: "chat",
    labelTranslationKey: "chat_nav",
    href: "/chat/",
    access: ANGGOTA,
    palette: { id: "nav_chat", keySequence: "gc" },
  },
  // Pengumuman = kanal sistem Obrolan, jadi ikut modul Chat.
  {
    key: "pengumuman",
    module: "chat",
    labelTranslationKey: "pengumuman_ui.nav",
    href: "/pengumuman/",
    access: ANGGOTA,
    palette: { id: "nav_pengumuman", titleKey: "pengumuman_ui.nav" },
  },
  // href statis: halaman itu meresolusi project ber-identifier WIKI.
  {
    key: "wiki",
    module: "wiki",
    labelTranslationKey: "wiki_nav",
    href: "/wiki/",
    access: ANGGOTA,
    palette: { id: "nav_wiki", keySequence: "gw" },
  },
] as const satisfies readonly {
  key: string;
  module: TParadiseModule;
  labelTranslationKey: string;
  href: string;
  access: readonly EUserWorkspaceRoles[];
  palette?: { id: string; titleKey?: string; keySequence?: string };
}[];

export type TParadiseNavItem = (typeof PARADISE_NAV_ITEMS)[number];
export type TParadiseNavKey = TParadiseNavItem["key"];
export type TParadiseNavPaletteId = NonNullable<Extract<TParadiseNavItem, { palette: unknown }>["palette"]>["id"];

/**
 * Menu yang bisa disematkan per orang (baris `WorkspaceUserPreference`), dan
 * yang diatur Super Admin di God Mode > People > New member defaults.
 * `dashboard_divisi` dan `analytics` tidak lagi punya menu sendiri (tab KPI),
 * tapi barisnya tetap ada supaya pilihan lama tidak hilang.
 */
export const PARADISE_NAV_PREFERENCE_KEYS = {
  // `departments` bukan menu: barisnya menyimpan tampil/sembunyi bagian daftar departemen.
  personal: ["your_work", "stickies", "drafts", "quick_links", "departments"],
  workspace: [
    "views",
    "analytics",
    "dashboard_divisi",
    "kinerja",
    "initiatives",
    "persetujuan",
    "tugas_lintas_divisi",
    "chat",
    "pengumuman",
    "wiki",
    "archives",
  ],
} as const;

export type TParadiseNavPreferenceKey =
  | (typeof PARADISE_NAV_PREFERENCE_KEYS.personal)[number]
  | (typeof PARADISE_NAV_PREFERENCE_KEYS.workspace)[number];
