/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: ukuran sasaran sentuh tombol
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vite-plus/test";
import { getIconButtonStyling } from "../icon-button/helper";
import { getButtonStyling } from "./helper";
import type { TButtonSize } from "./helper";

// Tailwind spacing unit = 4px, jadi `min-h-10` = 40px.
const sentuhPx = (classes: string, prop: "min-h" | "min-w" | "size"): number => {
  const m = classes.match(new RegExp(`(?:^|\\s)sentuh:${prop}-(\\d+)(?:\\s|$)`));
  return m ? Number(m[1]) * 4 : 0;
};

describe("Button di layar sentuh", () => {
  const sizes: TButtonSize[] = ["sm", "base", "lg", "xl"];

  it.each(sizes)("ukuran %s minimal 40x40px di pointer kasar", (size) => {
    const classes = getButtonStyling("primary", size);
    expect(sentuhPx(classes, "min-h")).toBeGreaterThanOrEqual(40);
    expect(sentuhPx(classes, "min-w")).toBeGreaterThanOrEqual(40);
  });

  it("lg dan xl, tombol aksi utama, mencapai 44px", () => {
    expect(sentuhPx(getButtonStyling("primary", "lg"), "min-h")).toBe(44);
    expect(sentuhPx(getButtonStyling("primary", "xl"), "min-h")).toBe(44);
  });

  it("chip tetap ringkas karena hidup di baris padat", () => {
    expect(sentuhPx(getButtonStyling("secondary", "chip"), "min-h")).toBe(0);
  });

  it("ukuran desktop tidak berubah", () => {
    expect(getButtonStyling("primary", "base")).toMatch(/(^|\s)h-7(\s|$)/);
    expect(getButtonStyling("primary", "xl")).toMatch(/(^|\s)h-9(\s|$)/);
  });
});

describe("IconButton di layar sentuh", () => {
  it.each(["sm", "base", "lg", "xl"] as const)("ukuran %s minimal 40px", (size) => {
    expect(sentuhPx(getIconButtonStyling("ghost", size), "size")).toBeGreaterThanOrEqual(40);
  });
});
