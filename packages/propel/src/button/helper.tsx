/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { VariantProps } from "class-variance-authority";
import { cva } from "class-variance-authority";

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-1 whitespace-nowrap transition-[color,background-color,border-color,box-shadow,transform] focus-visible:outline-none disabled:pointer-events-none disabled:shadow-none",
  {
    variants: {
      variant: {
        primary:
          "bg-accent-primary text-on-color hover:bg-accent-primary-hover active:bg-accent-primary-active disabled:bg-layer-disabled disabled:text-on-color-disabled",
        "error-fill":
          "bg-danger-primary text-on-color hover:bg-danger-primary-hover active:bg-danger-primary-active disabled:bg-layer-disabled disabled:text-disabled",
        "error-outline":
          "border border-danger-strong bg-layer-2 text-danger-secondary hover:bg-danger-subtle active:bg-danger-subtle-hover disabled:border-subtle-1 disabled:bg-layer-2 disabled:text-disabled",
        secondary:
          "border border-strong bg-layer-2 text-secondary hover:bg-layer-2-hover active:bg-layer-2-active disabled:border-subtle-1 disabled:bg-layer-transparent disabled:text-disabled",
        tertiary:
          "bg-layer-3 text-secondary hover:bg-layer-3-hover active:bg-layer-3-active disabled:bg-layer-transparent disabled:text-disabled",
        ghost:
          "bg-layer-transparent text-secondary hover:bg-layer-transparent-hover focus:bg-layer-transparent-active active:bg-layer-transparent-active disabled:bg-layer-transparent disabled:text-disabled",
        link: "px-0 text-link-primary underline hover:text-link-primary-hover focus:text-link-primary-hover active:text-link-primary-hover disabled:text-disabled",
      },
      size: {
        // Paradise (KEP-64): "no more small button", lalu "button is too large".
        // Hasil akhirnya setengah langkah di atas Plane: 24/28/32/36px.
        // Chip properti work item (status, prioritas, penerima, modul, label): kecil dan
        // ringkas seperti chip Plane asli, bersudut tombol biasa (bukan pil).
        chip: "h-5 px-1.5 text-caption-sm-medium",
        sm: "h-6 px-2.5 text-body-xs-medium",
        base: "h-7 px-3 text-body-xs-medium",
        lg: "h-8 px-3.5 text-body-sm-medium",
        xl: "h-9 px-4 text-body-sm-medium",
      },
      // Paradise (KEP-64): tombol biasa bersudut rounded-button; "pill" untuk chip yang
      // bisa diklik (label work item, chip properti), supaya pemanggil tidak menulis radius sendiri.
      shape: {
        rectangle: "rounded-button",
        pill: "rounded-control",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "base",
      shape: "rectangle",
    },
  }
);

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    appendIcon?: React.ReactElement;
    loading?: boolean;
    prependIcon?: React.ReactElement;
  };

export type TButtonVariant = NonNullable<ButtonProps["variant"]>;
export type TButtonSize = NonNullable<ButtonProps["size"]>;

const buttonIconStyling: Record<TButtonSize, string> = {
  chip: "size-3",
  sm: "size-3.5",
  base: "size-3.5",
  lg: "size-4",
  xl: "size-4",
};

export function getIconStyling(size: TButtonSize): string {
  return buttonIconStyling[size];
}

export function getButtonStyling(variant: TButtonVariant, size: TButtonSize): string {
  return buttonVariants({ variant, size });
}
