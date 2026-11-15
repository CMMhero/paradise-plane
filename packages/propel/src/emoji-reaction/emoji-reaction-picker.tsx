/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React, { useMemo, useCallback, useRef } from "react";
import { EmojiRoot } from "../emoji-icon-picker/emoji/emoji";
import { emojiToString } from "../emoji-icon-picker/helper";
import { Popover } from "../popover";
import { cn } from "../utils/classname";
import { convertPlacementToSideAndAlign } from "../utils/placement";
import type { TPlacement, TSide, TAlign } from "../utils/placement";

export interface EmojiReactionPickerProps {
  isOpen: boolean;
  handleToggle: (value: boolean) => void;
  buttonClassName?: string;
  closeOnSelect?: boolean;
  disabled?: boolean;
  dropdownClassName?: string;
  label: React.ReactNode;
  /**
   * `button` (bawaan): `label` dibungkus tombol pemicu.
   * `anchor`: `label` sudah berisi tombol sendiri (mis. EmojiReactionGroup dengan tombol tambah), jadi tidak
   * dibungkus tombol lagi (tombol di dalam tombol, axe nested-interactive); picker hanya menempel padanya dan
   * dibuka lewat `isOpen`.
   */
  triggerMode?: "button" | "anchor";
  onChange: (emoji: string) => void;
  placement?: TPlacement;
  searchDisabled?: boolean;
  searchPlaceholder?: string;
  side?: TSide;
  align?: TAlign;
}

export function EmojiReactionPicker(props: EmojiReactionPickerProps) {
  const {
    isOpen,
    handleToggle,
    buttonClassName,
    closeOnSelect = true,
    disabled = false,
    dropdownClassName,
    label,
    onChange,
    placement = "bottom-start",
    searchDisabled = false,
    searchPlaceholder = "Search",
    side = "bottom",
    align = "start",
    triggerMode = "button",
  } = props;
  const anchorRef = useRef<HTMLDivElement>(null);

  // side and align calculations
  const { finalSide, finalAlign } = useMemo(() => {
    if (placement) {
      const converted = convertPlacementToSideAndAlign(placement);
      return { finalSide: converted.side, finalAlign: converted.align };
    }
    return { finalSide: side, finalAlign: align };
  }, [placement, side, align]);

  const handleEmojiChange = useCallback(
    (value: string) => {
      const emoji = emojiToString(value);
      onChange(emoji);
      if (closeOnSelect) handleToggle(false);
    },
    [onChange, closeOnSelect, handleToggle]
  );

  return (
    <Popover open={isOpen} onOpenChange={handleToggle}>
      {triggerMode === "anchor" ? (
        <div ref={anchorRef} className={buttonClassName}>
          {label}
        </div>
      ) : (
        <Popover.Button className={cn("outline-none", buttonClassName)} disabled={disabled}>
          {label}
        </Popover.Button>
      )}
      <Popover.Panel
        anchor={triggerMode === "anchor" ? anchorRef : undefined}
        positionerClassName="z-50"
        className={cn(
          "w-80 overflow-hidden rounded-popover border-[0.5px] border-strong bg-surface-1",
          dropdownClassName
        )}
        side={finalSide}
        align={finalAlign}
        sideOffset={8}
        data-prevent-outside-click="true"
      >
        <div className="h-80 overflow-hidden overflow-y-auto">
          <EmojiRoot
            onChange={handleEmojiChange}
            searchPlaceholder={searchPlaceholder}
            searchDisabled={searchDisabled}
          />
        </div>
      </Popover.Panel>
    </Popover>
  );
}
