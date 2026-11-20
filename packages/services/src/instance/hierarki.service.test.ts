/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: hierarki jabatan God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vite-plus/test";
import {
  TINGKAT_CABANG,
  TINGKAT_DIREKTUR,
  TINGKAT_MANAGER,
  TINGKAT_MEMBER,
  TINGKAT_SEKRETARIS,
  isDirektur,
} from "./hierarki.service";

describe("isDirektur", () => {
  it("true bila ada penempatan jenjang direktur", () => {
    expect(isDirektur([{ tingkat: TINGKAT_MEMBER }, { tingkat: TINGKAT_DIREKTUR }])).toBe(true);
  });

  it("false untuk jenjang di bawahnya, termasuk sekretaris dan direktur cabang", () => {
    expect(isDirektur([{ tingkat: TINGKAT_MANAGER }])).toBe(false);
    expect(isDirektur([{ tingkat: TINGKAT_CABANG }])).toBe(false);
    expect(isDirektur([{ tingkat: TINGKAT_SEKRETARIS }])).toBe(false);
  });

  it("false bila penempatan kosong atau belum dimuat", () => {
    expect(isDirektur([])).toBe(false);
    expect(isDirektur(undefined)).toBe(false);
    expect(isDirektur(null)).toBe(false);
  });
});
