/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type React from "react";
import type { LucideIcon } from "lucide-react";
import { Bell, CircleUser, KeyRound, Link2, LockIcon, Settings2 } from "lucide-react";
// plane imports
import type { ISvgIcons } from "@plane/propel/icons";
import type { TProfileSettingsTabs } from "@plane/types";

/**
 * Dipakai sidebar setelan profil dan Power K ("Open an account setting").
 * Record ini WAJIB memuat setiap tab: tipe `Record<TProfileSettingsTabs, ...>`
 * membuat tsc menolak kalau ada yang terlewat, karena tab tanpa ikon akan tampil
 * polos tanpa satu pun pesan galat.
 */
export const PROFILE_SETTINGS_ICONS: Record<TProfileSettingsTabs, LucideIcon | React.FC<ISvgIcons>> = {
  general: CircleUser,
  security: LockIcon,
  preferences: Settings2,
  notifications: Bell,
  // Tab Connections cuma berisi Google Calendar untuk sekarang; namanya tidak
  // mengunci vendor supaya Outlook bisa menyusul di tab yang sama.
  connections: Link2,
  "api-tokens": KeyRound,
};
