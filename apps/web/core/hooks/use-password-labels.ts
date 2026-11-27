/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: teks kolom password mengikuti bahasa pengguna
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo } from "react";
// plane imports
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
        criteriaLabels: {
          length: t("onboarding_ui.pw_min_length"),
        },
      },
    }),
    [t]
  );
}
