/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useMemo } from "react";
import { observer } from "mobx-react";
import { useTheme } from "next-themes";
// plane imports
import type { I_THEME_OPTION } from "@plane/constants";
import { THEME_OPTIONS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { applyCustomTheme } from "@plane/utils";
// components
import { CustomThemeSelector } from "@/components/core/theme/custom-theme-selector";
import { ThemeSwitch } from "@/components/core/theme/theme-switch";
import { SettingsControlItem } from "@/components/settings/control-item";
// hooks
import { useUserProfile } from "@/hooks/store/user";

export const ThemeSwitcher = observer(function ThemeSwitcher(props: {
  option: {
    id: string;
    title: string;
    description: string;
  };
}) {
  // store hooks
  const { data: userProfile, updateUserTheme } = useUserProfile();
  // theme
  const { setTheme } = useTheme();
  // translation
  const { t } = useTranslation();
  // derived values
  const currentTheme = useMemo(() => {
    const userThemeOption = THEME_OPTIONS.find((option) => option.value === userProfile?.theme?.theme);
    return userThemeOption || null;
  }, [userProfile?.theme?.theme]);

  const handleThemeChange = useCallback(
    async (themeOption: I_THEME_OPTION) => {
      const previousTheme = userProfile?.theme?.theme;
      // Optimistic: apply in place right away (no reload), persist in the background.
      setTheme(themeOption.value);

      // If switching to custom theme and user has saved custom colors, apply them immediately
      if (
        themeOption.value === "custom" &&
        userProfile?.theme?.primary &&
        userProfile?.theme?.background &&
        userProfile?.theme?.darkPalette !== undefined
      ) {
        applyCustomTheme(
          userProfile.theme.primary,
          userProfile.theme.background,
          userProfile.theme.darkPalette ? "dark" : "light"
        );
      }

      try {
        await updateUserTheme({ theme: themeOption.value });
      } catch (error) {
        console.error("Error updating theme:", error);
        // The store already reverted its value; revert the live theme too.
        setTheme(previousTheme || "system");
        setToast({
          type: TOAST_TYPE.ERROR,
          title: "Error!",
          message: "Failed to update theme. Please try again.",
        });
      }
    },
    [setTheme, updateUserTheme, userProfile]
  );

  if (!userProfile) return null;

  return (
    <>
      <SettingsControlItem
        title={t(props.option.title)}
        description={t(props.option.description)}
        control={
          <ThemeSwitch
            value={currentTheme}
            onChange={(themeOption) => {
              void handleThemeChange(themeOption);
            }}
          />
        }
      />
      {userProfile.theme?.theme === "custom" && <CustomThemeSelector />}
    </>
  );
});
