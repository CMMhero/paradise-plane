/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { forwardRef } from "react";
import { getIconButtonStyling } from "@plane/propel/icon-button";
import type { IconButtonProps } from "@plane/propel/icon-button";
import { cn } from "@plane/utils";

type MenuTriggerIconProps = {
  icon: React.FC<{ className?: string }>;
  variant?: NonNullable<IconButtonProps["variant"]>;
  size?: NonNullable<IconButtonProps["size"]>;
  className?: string;
  iconClassName?: string;
};

const ICON_SIZE: Record<NonNullable<IconButtonProps["size"]>, string> = {
  sm: "size-3.5",
  base: "size-4",
  lg: "size-4",
  xl: "size-5",
};

/**
 * Tampilan IconButton untuk `customButton` milik CustomMenu.
 *
 * CustomMenu SELALU membungkus `customButton` dengan <button> miliknya sendiri. Kalau isinya IconButton,
 * hasilnya tombol di dalam tombol: pembaca layar membaca dua kontrol, tombol luar tidak bernama, dan Tab
 * berhenti dua kali (axe nested-interactive + button-name). Komponen ini merender <span> dengan gaya yang
 * sama persis; nama aksesibelnya diberikan lewat `ariaLabel` di CustomMenu.
 */
export const MenuTriggerIcon = forwardRef<HTMLSpanElement, MenuTriggerIconProps>(function MenuTriggerIcon(
  { icon: Icon, variant = "ghost", size = "base", className, iconClassName },
  ref
) {
  return (
    <span ref={ref} className={cn(getIconButtonStyling(variant, size), className)}>
      <Icon className={cn(ICON_SIZE[size], iconClassName)} />
    </span>
  );
});
