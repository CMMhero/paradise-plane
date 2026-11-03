/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import type { Control } from "react-hook-form";
import { Controller } from "react-hook-form";
// plane imports
import type { IUserTheme } from "@plane/types";
import { RadioGroup } from "@plane/propel/radio-group";

const MODE_OPTION_CLASS =
  "border border-subtle-1 bg-layer-2 px-3 py-2 hover:bg-layer-2-hover has-[[data-checked]]:border-accent-strong";

type Props = {
  control: Control<IUserTheme>;
};

export const CustomThemeModeSelector = observer(function CustomThemeModeSelector(props: Props) {
  const { control } = props;

  return (
    <div>
      <h6 className="text-h6-medium">
        Choose color mode<span className="text-danger-primary">*</span>
      </h6>
      <Controller
        control={control}
        name="darkPalette"
        render={({ field: { value, onChange } }) => (
          <RadioGroup
            name="darkPalette"
            aria-label="Choose color mode"
            orientation="horizontal"
            className="mt-2 gap-3"
            value={value === undefined ? null : String(value)}
            onValueChange={(next) => onChange(next === "true")}
          >
            <RadioGroup.Item value="false" label="Light mode" className={MODE_OPTION_CLASS} />
            <RadioGroup.Item value="true" label="Dark mode" className={MODE_OPTION_CLASS} />
          </RadioGroup>
        )}
      />
    </div>
  );
});
