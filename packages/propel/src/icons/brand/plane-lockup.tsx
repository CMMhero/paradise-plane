/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";

import type { ISvgIcons } from "../type";
import { PARADISE_LOGO_SRC } from "./paradise-logo-src";

export function PlaneLockup({ height = "53", className, color = "currentColor" }: ISvgIcons) {
  const size = Number(height) || 53;
  return (
    <span className={className} style={{ display: "inline-flex", alignItems: "center", gap: size * 0.3, color }}>
      <img src={PARADISE_LOGO_SRC} alt="" style={{ height: size, width: "auto", objectFit: "contain" }} />
      <span
        style={{
          fontSize: size * 0.55,
          fontWeight: 700,
          letterSpacing: "0.02em",
          lineHeight: 1,
          whiteSpace: "nowrap",
        }}
      >
        Paradise Perkasa
      </span>
    </span>
  );
}
