/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";

import type { ISvgIcons } from "../type";

export function PlaneWordmark({ height = "44", className, color = "currentColor" }: ISvgIcons) {
  const size = Number(height) || 44;
  return (
    <span
      className={className}
      style={{
        color,
        fontSize: size * 0.55,
        fontWeight: 700,
        letterSpacing: "0.02em",
        lineHeight: 1,
        whiteSpace: "nowrap",
      }}
    >
      Paradise Perkasa
    </span>
  );
}
