/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";
import type { ChangeEvent } from "react";
import type { DropdownProps } from "react-day-picker";
import { Combobox } from "../combobox";
import { CheckIcon, ChevronDownIcon } from "../icons";
import { cn } from "../utils";

/**
 * Month/year picker for the calendar caption. Replaces react-day-picker's
 * native `<select>`, whose OS-drawn option list ignores the design system.
 */
export function CalendarCaptionDropdown(props: DropdownProps) {
  const { options = [], value, onChange, disabled, "aria-label": ariaLabel } = props;
  const [isOpen, setIsOpen] = React.useState(false);
  const popupClass = `rdp-caption-popup-${React.useId().replace(/[^a-zA-Z0-9]/g, "")}`;

  const selected = options.find((option) => option.value === Number(value));

  const handleValueChange = (next: string | string[]) => {
    if (Array.isArray(next) || next === "") return;
    // react-day-picker's month/year handlers only read `e.target.value`.
    onChange?.({ target: { value: next } } as ChangeEvent<HTMLSelectElement>);
    setIsOpen(false);
  };

  // A long year list opens with the selected year scrolled into view.
  React.useEffect(() => {
    if (!isOpen) return;
    const frame = requestAnimationFrame(() => {
      document.querySelector(`.${popupClass} [data-selected]`)?.scrollIntoView({ block: "nearest" });
    });
    return () => cancelAnimationFrame(frame);
  }, [isOpen, popupClass]);

  return (
    <Combobox
      value={value === undefined ? undefined : String(value)}
      onValueChange={handleValueChange}
      open={isOpen}
      onOpenChange={setIsOpen}
      disabled={disabled}
    >
      <Combobox.Button
        disabled={disabled}
        className={cn(
          "flex items-center gap-1 rounded-item px-1.5 py-0.5 text-13 font-semibold text-primary capitalize outline-none",
          "hover:bg-layer-transparent-hover focus-visible:bg-layer-transparent-hover",
          { "bg-layer-transparent-active": isOpen, "cursor-not-allowed text-disabled": disabled }
        )}
      >
        <span aria-label={ariaLabel}>{selected?.label}</span>
        <ChevronDownIcon className={cn("size-3.5 text-tertiary transition-transform", { "rotate-180": isOpen })} />
      </Combobox.Button>
      <Combobox.Options
        maxHeight="md"
        dataPreventOutsideClick
        positionerClassName={cn("z-110", popupClass)}
        className="min-w-28"
      >
        {options.map((option) => {
          const isSelected = option.value === selected?.value;
          return (
            <Combobox.Option
              key={option.value}
              value={String(option.value)}
              disabled={option.disabled}
              className={cn(
                "flex items-center justify-between gap-2 text-secondary capitalize",
                "hover:bg-layer-transparent-hover data-[highlighted]:bg-layer-transparent-hover",
                {
                  "text-primary": isSelected,
                  "cursor-not-allowed text-disabled hover:bg-transparent": option.disabled,
                }
              )}
            >
              <span>{option.label}</span>
              {isSelected && <CheckIcon className="size-3.5 text-accent-primary" />}
            </Combobox.Option>
          );
        })}
      </Combobox.Options>
    </Combobox>
  );
}
