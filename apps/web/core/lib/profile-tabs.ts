/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tab setelan profil yang bergantung setelan instance
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tab Connections hanya berisi Google Calendar. Tanpa client ID + secret di
 * God Mode, tombol Connect-nya mati dan orang tak bisa berbuat apa-apa, jadi
 * tabnya disembunyikan dan URL-nya dialihkan. Murni supaya sidebar, halaman,
 * dan modal setelan memakai satu aturan yang sama.
 */

import type { IInstanceConfig, TProfileSettingsTabs } from "@plane/types";

/** Tab cadangan ketika tab yang diminta tidak tersedia. */
export const PROFILE_TAB_FALLBACK: TProfileSettingsTabs = "general";

export const isProfileTabAvailable = (config: IInstanceConfig | undefined, tab: TProfileSettingsTabs): boolean => {
  // Server lama tidak mengirim bidangnya: anggap tersedia, perilaku lama tetap.
  if (tab === "connections") return config?.has_google_calendar_configured !== false;
  return true;
};
