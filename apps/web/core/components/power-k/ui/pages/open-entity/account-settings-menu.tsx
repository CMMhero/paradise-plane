/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tab setelan akun di Power K
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { GROUPED_PROFILE_SETTINGS, PROFILE_SETTINGS_CATEGORIES } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TProfileSettingsTabs } from "@plane/types";
// components
import { PowerKSettingsMenu } from "@/components/power-k/menus/settings";
import { PROFILE_SETTINGS_ICONS } from "@/components/settings/profile/sidebar/item-icon";
// hooks
import { useInstance } from "@/hooks/store/use-instance";
// lib
import { isProfileTabAvailable } from "@/lib/profile-tabs";

type Props = {
  handleSelect: (tab: TProfileSettingsTabs) => void;
};

/**
 * Sumbernya daftar yang sama dengan sidebar modal setelan profil, termasuk aturan
 * `isProfileTabAvailable` (Connections hilang selama Google Calendar belum
 * dikonfigurasi di God Mode). Tab baru otomatis ikut muncul di sini.
 */
export const PowerKOpenAccountSettingsMenu = observer(function PowerKOpenAccountSettingsMenu(props: Props) {
  const { handleSelect } = props;
  const { t } = useTranslation();
  const { config } = useInstance();

  const settings = PROFILE_SETTINGS_CATEGORIES.flatMap((category) => GROUPED_PROFILE_SETTINGS[category])
    .filter((setting) => isProfileTabAvailable(config, setting.key))
    .map((setting) => ({
      key: setting.key,
      label: t(setting.i18n_label),
      icon: PROFILE_SETTINGS_ICONS[setting.key],
      // PowerKSettingsMenu memakai bentuk { href }; di sini isinya kunci tab, bukan URL.
      href: setting.key,
    }));

  return (
    <PowerKSettingsMenu settings={settings} onSelect={(setting) => handleSelect(setting.key as TProfileSettingsTabs)} />
  );
});
