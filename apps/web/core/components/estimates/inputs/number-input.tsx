/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import { Input } from "@plane/ui";
type TEstimateNumberInputProps = {
  value?: number;
  handleEstimateInputValue: (value: string) => void;
};

export function EstimateNumberInput(props: TEstimateNumberInputProps) {
  const { value, handleEstimateInputValue } = props;

  // i18n
  const { t } = useTranslation();

  return (
    <Input
      value={value}
      onChange={(e) => handleEstimateInputValue(e.target.value)}
      mode="true-transparent"
      className="w-full px-2 focus:border-0 focus:ring-0"
      placeholder={t("project_settings.estimates.create.enter_estimate_point")}
      autoFocus
      step="any"
    />
  );
}
