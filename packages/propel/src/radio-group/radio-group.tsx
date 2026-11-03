/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";
import { Radio as BaseRadio } from "@base-ui-components/react/radio";
import { RadioGroup as BaseRadioGroup } from "@base-ui-components/react/radio-group";
import { cn } from "../utils/classname";

export type TRadioGroupProps = {
  /** `null` = controlled with nothing selected. */
  value: string | null;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
  name?: string;
  disabled?: boolean;
  orientation?: "vertical" | "horizontal";
  className?: string;
  "aria-label"?: string;
  "aria-labelledby"?: string;
};

export type TRadioGroupItemProps = {
  value: string;
  label: React.ReactNode;
  description?: React.ReactNode;
  disabled?: boolean;
  /** Applied to the clickable row. The row exposes `has-data-checked:` for selected styling. */
  className?: string;
};

/**
 * Single-choice group with roving focus: Tab enters the group once, arrow keys
 * move and select. Every option row is a label, so the whole row is clickable.
 */
function RadioGroupRoot({
  value,
  onValueChange,
  children,
  name,
  disabled,
  orientation = "vertical",
  className,
  ...aria
}: TRadioGroupProps) {
  return (
    <BaseRadioGroup
      value={value}
      onValueChange={(next) => onValueChange(String(next))}
      name={name}
      disabled={disabled}
      className={cn(orientation === "vertical" ? "flex flex-col gap-1" : "flex flex-wrap gap-2", className)}
      {...aria}
    >
      {children}
    </BaseRadioGroup>
  );
}

function RadioGroupItem({ value, label, description, disabled, className }: TRadioGroupItemProps) {
  return (
    <label
      className={cn(
        "group/radio flex cursor-pointer gap-2 rounded-item px-2 py-1.5 transition-colors hover:bg-layer-transparent-hover",
        { "items-start": description, "items-center": !description },
        { "cursor-not-allowed opacity-60 hover:bg-transparent": disabled },
        className
      )}
    >
      <BaseRadio.Root
        value={value}
        disabled={disabled}
        className={cn(
          "grid size-4 shrink-0 place-items-center rounded-control border border-strong bg-surface-1 transition-colors outline-none",
          "group-hover/radio:border-strong-1 focus-visible:outline-1 focus-visible:outline-offset-2 focus-visible:outline-accent-strong",
          "data-[checked]:border-accent-strong data-[checked]:bg-accent-primary",
          "data-[disabled]:border-subtle data-[disabled]:bg-layer-1",
          { "mt-0.5": description }
        )}
      >
        <BaseRadio.Indicator className="size-1.5 rounded-[2px] bg-current text-on-color data-[unchecked]:hidden" />
      </BaseRadio.Root>
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="text-13 text-primary">{label}</span>
        {description && <span className="text-11 text-secondary">{description}</span>}
      </span>
    </label>
  );
}

const RadioGroup = Object.assign(RadioGroupRoot, { Item: RadioGroupItem });

export { RadioGroup };
