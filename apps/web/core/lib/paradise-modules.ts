/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: modul yang dimatikan dari God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Super Admin menyalakan/mematikan menu sidebar utama, menu workspace, tab
 * project, dan fitur di dalam work item lewat God Mode > Features
 * (`paradise_modules` di /api/instances/). Fungsi di sini murni supaya bisa
 * diuji tanpa store: peta kunci menu dan pola URL ke modulnya. Data dan endpoint
 * tidak pernah disentuh saklar ini.
 */

import { PARADISE_MODULE_DEFAULTS, PARADISE_REMOVED, type TParadiseGate } from "@plane/constants";
import type { IInstanceConfig, TParadiseModule } from "@plane/types";

/**
 * Kunci item menu (sidebar, nav project) yang namanya BUKAN nama modul.
 * Kunci lain yang kebetulan sama dengan nama modul (mis. `stickies`, `modules`)
 * langsung dipetakan ke modul itu.
 */
/** Tab Materials project departemen (KEP-97): materi Wiki, jadi ikut modul Wiki. */
export const WIKI_MATERIALS_NAV_KEY = "wiki_materials";

const MODUL_PER_KUNCI_MENU: Record<string, TParadiseGate> = {
  dashboard_divisi: "dashboards",
  persetujuan: "approvals",
  [WIKI_MATERIALS_NAV_KEY]: "wiki",
  // Dicabut (KEP-53): menunya tak pernah tampil lagi.
  cycles: PARADISE_REMOVED,
};

const PROJECT = String.raw`projects\/[^/]+`;
const SETELAN_PROJECT = String.raw`settings\/projects\/[^/]+`;
const pola = (segmen: string) => new RegExp(String.raw`^\/[^/]+\/${segmen}(\/|$)`);

/** Pola path (sesudah slug workspace) -> modul. Dicek berurutan, yang pertama cocok menang. */
const MODUL_PER_PATH: [RegExp, TParadiseModule][] = [
  // Sidebar utama
  [pola("notifications"), "inbox"],
  [pola("profile"), "your_work"],
  [pola("stickies"), "stickies"],
  [pola("drafts"), "drafts"],
  [pola("quick-links"), "quick_links"],
  // Menu workspace
  [pola("(dashboard-divisi|dashboards)"), "dashboards"],
  [pola("initiatives"), "initiatives"],
  [pola("workspace-views"), "views"],
  [pola("analytics"), "analytics"],
  [pola("chat"), "chat"],
  [pola("wiki"), "wiki"],
  // `projects/archives` didaftarkan SEBELUM pola project: kata `archives` di sana
  // bukan id project.
  [pola("projects/archives"), "archives"],
  // Tab project
  [pola(`${PROJECT}/archives`), "archives"],
  [pola(`${PROJECT}/issues`), "work_items"],
  [pola("browse"), "work_items"],
  [pola(`${PROJECT}/modules`), "modules"],
  [pola(`${PROJECT}/views`), "views"],
  [pola(`${PROJECT}/pages`), "pages"],
  [pola(`${PROJECT}/(intake|inbox)`), "intake"],
  [pola(`${PROJECT}/persetujuan`), "approvals"],
  [pola(`${PROJECT}/materials`), "wiki"],
  // Setelan project milik modul yang sama
  [pola(`${SETELAN_PROJECT}/features/modules`), "modules"],
  [pola(`${SETELAN_PROJECT}/features/views`), "views"],
  [pola(`${SETELAN_PROJECT}/features/pages`), "pages"],
  [pola(`${SETELAN_PROJECT}/features/intake`), "intake"],
  [pola(`${SETELAN_PROJECT}/estimates`), "estimates"],
];

const isParadiseModule = (key: string): key is TParadiseModule => Object.hasOwn(PARADISE_MODULE_DEFAULTS, key);

export const isParadiseModuleEnabled = (config: IInstanceConfig | undefined, module: TParadiseModule): boolean =>
  config?.paradise_modules?.[module] ?? PARADISE_MODULE_DEFAULTS[module];

/** Modul pemilik kunci menu, atau undefined bila menu itu tidak bisa dimatikan. */
export const moduleForNavKey = (key: string): TParadiseGate | undefined =>
  // Object.hasOwn, bukan `MODUL_PER_KUNCI_MENU[key]`: kunci seperti `toString`
  // akan terbaca dari prototype.
  Object.hasOwn(MODUL_PER_KUNCI_MENU, key) ? MODUL_PER_KUNCI_MENU[key] : isParadiseModule(key) ? key : undefined;

/** Modul pemilik halaman di `pathname`, atau undefined bila halaman itu selalu terbuka. */
export const moduleForPath = (pathname: string): TParadiseModule | undefined =>
  MODUL_PER_PATH.find(([p]) => p.test(pathname))?.[1];

export const isNavKeyEnabled = (config: IInstanceConfig | undefined, key: string): boolean => {
  const module = moduleForNavKey(key);
  if (module === undefined) return true;
  return module === PARADISE_REMOVED ? false : isParadiseModuleEnabled(config, module);
};
