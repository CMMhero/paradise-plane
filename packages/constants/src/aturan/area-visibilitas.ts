/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: cermin web aturan area A (apa yang dilihat tiap jenjang)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Cermin apps/api/plane/utils/aturan/area_visibilitas.py. Hanya aturan tampilan;
 * aturan cakupan data area A dijaga API dan tidak dikirim ke web.
 */

import { pilihanWeb } from "./jenis";

export const DIRECTOR_SIDEBAR_HIDES_CHOICES = ["none", "archives", "archives_your_work"] as const;
export type TDirectorSidebarHides = (typeof DIRECTOR_SIDEBAR_HIDES_CHOICES)[number];

/** Kunci menu sidebar yang disembunyikan dari Direktur untuk setiap pilihan. */
export const DIRECTOR_SIDEBAR_HIDDEN_KEYS: Record<TDirectorSidebarHides, readonly string[]> = {
  none: [],
  archives: ["archives"],
  archives_your_work: ["archives", "your_work"],
};

/** Siapa "direktur" bagi aturan menu: jenjang 40 saja, atau 35 ke atas (sekretaris ikut). */
export const DIRECTOR_MENUS_APPLY_TO_CHOICES = ["director", "org_wide"] as const;
export type TDirectorMenusApplyTo = (typeof DIRECTOR_MENUS_APPLY_TO_CHOICES)[number];

/** Siapa yang melihat tab Analitik dan Dasbor Divisi di halaman KPI. Tampilan saja. */
export const KPI_EXTRA_TABS_CHOICES = ["admins_except_directors", "admins", "nobody"] as const;
export type TKpiExtraTabs = (typeof KPI_EXTRA_TABS_CHOICES)[number];

/**
 * True bila aturan menutup tab ekstra KPI bagi penonton ini, termasuk lewat URL
 * langsung. Admin workspace tetap syarat terpisah untuk MELIHAT tabnya.
 */
export const kpiExtraTabsDitutup = (pilihan: TKpiExtraTabs, isDirektur: boolean): boolean =>
  pilihan === "nobody" || (pilihan === "admins_except_directors" && isDirektur);

export const ATURAN_WEB_VISIBILITAS = {
  DIRECTOR_SIDEBAR_HIDES: pilihanWeb(DIRECTOR_SIDEBAR_HIDES_CHOICES, "archives"),
  DIRECTOR_MENUS_APPLY_TO: pilihanWeb(DIRECTOR_MENUS_APPLY_TO_CHOICES, "director"),
  KPI_EXTRA_TABS: pilihanWeb(KPI_EXTRA_TABS_CHOICES, "admins_except_directors"),
};
