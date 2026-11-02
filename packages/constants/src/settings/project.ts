/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { EUserProjectRoles } from "@plane/types";
import type { TParadiseModule, TProjectSettingsItem, TProjectSettingsTabs } from "@plane/types";
import { isParadiseModuleActive } from "../paradise-features";

export enum PROJECT_SETTINGS_CATEGORY {
  GENERAL = "general",
  FEATURES = "features",
  WORK_STRUCTURE = "work-structure",
  EXECUTION = "execution",
}

export const PROJECT_SETTINGS_CATEGORIES: PROJECT_SETTINGS_CATEGORY[] = [
  PROJECT_SETTINGS_CATEGORY.GENERAL,
  PROJECT_SETTINGS_CATEGORY.FEATURES,
  PROJECT_SETTINGS_CATEGORY.WORK_STRUCTURE,
  PROJECT_SETTINGS_CATEGORY.EXECUTION,
];

export const PROJECT_SETTINGS_CATEGORY_LABELS: Record<PROJECT_SETTINGS_CATEGORY, string> = {
  [PROJECT_SETTINGS_CATEGORY.GENERAL]: "common.general",
  [PROJECT_SETTINGS_CATEGORY.FEATURES]: "common.features",
  [PROJECT_SETTINGS_CATEGORY.WORK_STRUCTURE]: "common.work_structure",
  [PROJECT_SETTINGS_CATEGORY.EXECUTION]: "common.execution",
};

export const PROJECT_SETTINGS: Record<TProjectSettingsTabs, TProjectSettingsItem> = {
  general: {
    key: "general",
    i18n_label: "common.general",
    href: ``,
    access: [EUserProjectRoles.ADMIN, EUserProjectRoles.MEMBER, EUserProjectRoles.GUEST],
    highlight: (pathname: string, baseUrl: string) => pathname === `${baseUrl}/`,
  },
  members: {
    key: "members",
    i18n_label: "common.members",
    href: `/members`,
    access: [EUserProjectRoles.ADMIN, EUserProjectRoles.MEMBER, EUserProjectRoles.GUEST],
    highlight: (pathname: string, baseUrl: string) => pathname === `${baseUrl}/members/`,
  },
  features_modules: {
    key: "features_modules",
    i18n_label: "project_settings.features.modules.short_title",
    href: `/features/modules`,
    access: [EUserProjectRoles.ADMIN],
    highlight: (pathname: string, baseUrl: string) => pathname === `${baseUrl}/features/modules/`,
  },
  features_views: {
    key: "features_views",
    i18n_label: "project_settings.features.views.short_title",
    href: `/features/views`,
    access: [EUserProjectRoles.ADMIN],
    highlight: (pathname: string, baseUrl: string) => pathname === `${baseUrl}/features/views/`,
  },
  features_pages: {
    key: "features_pages",
    i18n_label: "project_settings.features.pages.short_title",
    href: `/features/pages`,
    access: [EUserProjectRoles.ADMIN],
    highlight: (pathname: string, baseUrl: string) => pathname === `${baseUrl}/features/pages/`,
  },
  features_intake: {
    key: "features_intake",
    i18n_label: "project_settings.features.intake.short_title",
    href: `/features/intake`,
    access: [EUserProjectRoles.ADMIN],
    highlight: (pathname: string, baseUrl: string) => pathname === `${baseUrl}/features/intake/`,
  },
  states: {
    key: "states",
    i18n_label: "common.states",
    href: `/states`,
    access: [EUserProjectRoles.ADMIN, EUserProjectRoles.MEMBER],
    highlight: (pathname: string, baseUrl: string) => pathname === `${baseUrl}/states/`,
  },
  labels: {
    key: "labels",
    i18n_label: "common.labels",
    href: `/labels`,
    access: [EUserProjectRoles.ADMIN, EUserProjectRoles.MEMBER],
    highlight: (pathname: string, baseUrl: string) => pathname === `${baseUrl}/labels/`,
  },
  estimates: {
    key: "estimates",
    i18n_label: "common.estimates",
    href: `/estimates`,
    access: [EUserProjectRoles.ADMIN],
    highlight: (pathname: string, baseUrl: string) => pathname === `${baseUrl}/estimates/`,
  },
  // Kustomisasi Paradise, Trashbin per project. Khusus admin project:
  // memulihkan & membuang permanen bukan wewenang anggota biasa.
  trash: {
    key: "trash",
    i18n_label: "project_settings.trash.heading",
    href: `/trash`,
    access: [EUserProjectRoles.ADMIN],
    highlight: (pathname: string, baseUrl: string) => pathname === `${baseUrl}/trash/`,
  },
  automations: {
    key: "automations",
    i18n_label: "project_settings.automations.label",
    href: `/automations`,
    access: [EUserProjectRoles.ADMIN],
    highlight: (pathname: string, baseUrl: string) => pathname === `${baseUrl}/automations/`,
  },
};

export const PROJECT_SETTINGS_FLAT_MAP: TProjectSettingsItem[] = Object.values(PROJECT_SETTINGS);

/** Tab setelan milik modul God Mode. Tab yang tak terdaftar selalu tampil. */
const MODUL_PER_TAB: Partial<Record<TProjectSettingsTabs, TParadiseModule>> = {
  features_modules: "modules",
  features_views: "views",
  features_pages: "pages",
  features_intake: "intake",
  estimates: "estimates",
};

const isProjectSettingVisible = (key: TProjectSettingsTabs): boolean => {
  const module = MODUL_PER_TAB[key];
  return module ? isParadiseModuleActive(module) : true;
};

const visible = (keys: TProjectSettingsTabs[]): TProjectSettingsItem[] =>
  keys.filter(isProjectSettingVisible).map((key) => PROJECT_SETTINGS[key]);

/**
 * Fungsi, bukan konstanta: modulnya diatur di God Mode saat aplikasi berjalan,
 * sedangkan konstanta tingkat modul dihitung sekali saat diimpor, sebelum
 * /api/instances/ menjawab.
 */
export const getGroupedProjectSettings = (): Record<PROJECT_SETTINGS_CATEGORY, TProjectSettingsItem[]> => ({
  [PROJECT_SETTINGS_CATEGORY.GENERAL]: visible(["general", "members"]),
  [PROJECT_SETTINGS_CATEGORY.FEATURES]: visible([
    "features_modules",
    "features_views",
    "features_pages",
    "features_intake",
  ]),
  [PROJECT_SETTINGS_CATEGORY.WORK_STRUCTURE]: visible(["states", "labels", "estimates"]),
  [PROJECT_SETTINGS_CATEGORY.EXECUTION]: visible(["trash", "automations"]),
});
