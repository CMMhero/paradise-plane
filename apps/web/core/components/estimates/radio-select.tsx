/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import { RadioGroup } from "@plane/propel/radio-group";
import { cn } from "@plane/utils";

type RadioInputProps = {
  name?: string;
  label?: string | React.ReactNode;
  wrapperClassName?: string;
  fieldClassName?: string;
  labelClassName?: string;
  ariaLabel?: string;
  options: { label: string | React.ReactNode; value: string; disabled?: boolean }[];
  vertical?: boolean;
  selected: string;
  onChange: (value: string) => void;
  className?: string;
};

export function RadioInput({
  name = "radio-input",
  label: inputLabel,
  labelClassName: inputLabelClassName = "",
  wrapperClassName: inputWrapperClassName = "",
  fieldClassName: inputFieldClassName = "",
  options,
  vertical,
  selected,
  ariaLabel,
  onChange,
  className,
}: RadioInputProps) {
  const labelId = `${name}-label`;

  return (
    <div className={className}>
      {inputLabel && (
        <div id={labelId} className={cn("mb-2", inputLabelClassName)}>
          {inputLabel}
        </div>
      )}
      <RadioGroup
        name={name}
        aria-label={ariaLabel}
        aria-labelledby={!ariaLabel && inputLabel ? labelId : undefined}
        orientation={vertical ? "vertical" : "horizontal"}
        className={inputWrapperClassName}
        value={selected}
        onValueChange={onChange}
      >
        {options.map(({ value, label, disabled }) => (
          <RadioGroup.Item
            key={value}
            value={value}
            label={label}
            disabled={disabled}
            className={inputFieldClassName}
          />
        ))}
      </RadioGroup>
    </div>
  );
}
