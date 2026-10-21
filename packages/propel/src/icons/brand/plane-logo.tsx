/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import * as React from "react";

import type { ISvgIcons } from "../type";
import { PARADISE_LOGO_SRC } from "./paradise-logo-src";

export function PlaneLogo({ width = "52", height = "52", className }: ISvgIcons) {
  return (
    <img
      src={PARADISE_LOGO_SRC}
      width={width}
      height={height}
      alt="Paradise Perkasa"
      className={className}
      style={{ objectFit: "contain" }}
    />
  );
}
