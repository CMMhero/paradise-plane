/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: teks kolom password mengikuti bahasa pengguna
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo } from "react";
// plane imports
import { E_PASSWORD_STRENGTH } from "@plane/constants";
import { useTranslation } from "@plane/i18n";

/**
 * Teks terjemahan untuk `PasswordInput` dan `PasswordStrengthIndicator`
 * (packages/ui tidak punya i18n sendiri, jadi teksnya diteruskan lewat props).
 *
 * Pemakaian:
 *   const { input, indicator } = usePasswordLabels();
 *   <PasswordInput {...input} />
 *   <PasswordStrengthIndicator password={value} {...indicator} />
 */
export function usePasswordLabels() {
  const { t } = useTranslation();

  return useMemo(
    () => ({
      input: {
        showLabel: t("onboarding_ui.pw_show"),
        hideLabel: t("onboarding_ui.pw_hide"),
      },
      indicator: {
        messages: {
          [E_PASSWORD_STRENGTH.EMPTY]: t("auth.common.password.errors.empty"),
          [E_PASSWORD_STRENGTH.LENGTH_NOT_VALID]: t("onboarding_ui.pw_too_short"),
          [E_PASSWORD_STRENGTH.STRENGTH_NOT_VALID]: t("auth.common.password.errors.strength.weak"),
          [E_PASSWORD_STRENGTH.STRENGTH_VALID]: t("auth.common.password.errors.strength.strong"),
        },
        criteriaLabels: {
          length: t("onboarding_ui.pw_min_length"),
          uppercase: t("onboarding_ui.pw_upper"),
          lowercase: t("onboarding_ui.pw_lower"),
          number: t("onboarding_ui.pw_number"),
          special: t("onboarding_ui.pw_special"),
        },
      },
    }),
    [t]
  );
}
