/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";
import { cn } from "../utils";

export enum EPillVariant {
  DEFAULT = "default",
  PRIMARY = "primary",
  SUCCESS = "success",
  WARNING = "warning",
  ERROR = "error",
  INFO = "info",
}

export enum EPillSize {
  SM = "sm",
  MD = "md",
  LG = "lg",
  XS = "xs",
}

export enum ERadius {
  SQUARE = "square",
  CIRCLE = "circle",
}

export type TRadius = ERadius.SQUARE | ERadius.CIRCLE;

export type TPillVariant =
  | EPillVariant.DEFAULT
  | EPillVariant.PRIMARY
  | EPillVariant.SUCCESS
  | EPillVariant.WARNING
  | EPillVariant.ERROR
  | EPillVariant.INFO;
export type TPillSize = EPillSize.SM | EPillSize.MD | EPillSize.LG | EPillSize.XS;

export interface PillProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: TPillVariant;
  size?: TPillSize;
  className?: string;
  children: React.ReactNode;
  radius?: TRadius;
}

// Paradise (KEP-64): palet mentah (green-50, amber-700, blue-50) tidak ada di tema ini, diganti token.
const pillVariants = {
  [EPillVariant.DEFAULT]: "bg-layer-2 text-secondary border border-subtle-1",
  [EPillVariant.PRIMARY]: "bg-accent-subtle text-accent-primary border border-accent-subtle",
  [EPillVariant.SUCCESS]: "bg-success-subtle text-success-primary border border-success-subtle",
  [EPillVariant.WARNING]: "bg-warning-subtle text-warning-primary border border-warning-subtle",
  [EPillVariant.ERROR]: "bg-danger-subtle text-danger-primary border border-danger-subtle",
  [EPillVariant.INFO]: "bg-label-indigo-bg text-label-indigo-text border border-label-indigo-border",
};

// Paradise (KEP-64): tinggi tetap, sejajar skala Badge (16/20/24/28px).
const pillSizes = {
  [EPillSize.XS]: "h-4 px-1.5 text-caption-sm-medium",
  [EPillSize.SM]: "h-5 px-2 text-caption-sm-medium",
  [EPillSize.MD]: "h-6 px-2.5 text-caption-md-medium",
  [EPillSize.LG]: "h-7 px-3 text-body-xs-medium",
};

const pillRadius = {
  [ERadius.SQUARE]: "rounded-sm",
  [ERadius.CIRCLE]: "rounded-control",
};

const Pill = React.forwardRef(function Pill(
  {
    variant = EPillVariant.DEFAULT,
    size = EPillSize.MD,
    radius = ERadius.CIRCLE,
    className,
    children,
    ...props
  }: PillProps,
  ref: React.ForwardedRef<HTMLSpanElement>
) {
  return (
    <span
      ref={ref}
      className={cn(
        // Base styles
        "inline-flex items-center justify-center font-medium whitespace-nowrap",
        // Variant styles
        pillVariants[variant],
        // Size styles
        pillSizes[size],
        // Radius styles
        pillRadius[radius],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
});

Pill.displayName = "Pill";

export { Pill };
