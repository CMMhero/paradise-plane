/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: matematika zoom/cubit kanvas bagan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vite-plus/test";
import { tampilanCubit, zoomDiTitik, ZOOM_MAKS, ZOOM_MIN } from "@/app/(all)/(dashboard)/organisasi/kanvas";

describe("zoomDiTitik", () => {
  it("keeps the anchor point fixed on screen", () => {
    const t = { x: 40, y: 10, k: 1 };
    const z = zoomDiTitik(t, 1.5, 200, 100);
    // content point under (200,100) before and after
    expect((200 - t.x) / t.k).toBeCloseTo((200 - z.x) / z.k);
    expect((100 - t.y) / t.k).toBeCloseTo((100 - z.y) / z.k);
  });

  it("clamps to the zoom limits", () => {
    expect(zoomDiTitik({ x: 0, y: 0, k: 1.9 }, 5, 0, 0).k).toBe(ZOOM_MAKS);
    expect(zoomDiTitik({ x: 0, y: 0, k: 0.3 }, 0.1, 0, 0).k).toBe(ZOOM_MIN);
  });
});

describe("tampilanCubit", () => {
  const awal = { x: 20, y: 30, k: 1 };
  it("scales by the change in finger distance around the midpoint", () => {
    const tengah = { x: 100, y: 100 };
    const t = tampilanCubit(awal, 100, tengah, 200, tengah);
    expect(t.k).toBe(2);
    expect((tengah.x - awal.x) / awal.k).toBeCloseTo((tengah.x - t.x) / t.k);
  });

  it("pans when the midpoint moves and the distance is unchanged", () => {
    const t = tampilanCubit(awal, 100, { x: 100, y: 100 }, 100, { x: 130, y: 90 });
    expect(t).toEqual({ k: 1, x: 50, y: 20 });
  });

  it("respects the limits and a zero start distance", () => {
    expect(tampilanCubit(awal, 10, { x: 0, y: 0 }, 1000, { x: 0, y: 0 }).k).toBe(ZOOM_MAKS);
    expect(tampilanCubit(awal, 1000, { x: 0, y: 0 }, 1, { x: 0, y: 0 }).k).toBe(ZOOM_MIN);
    expect(tampilanCubit(awal, 0, { x: 0, y: 0 }, 50, { x: 0, y: 0 }).k).toBe(1);
  });
});
