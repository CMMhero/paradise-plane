/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: bawaan tampilan dari aturan God Mode (area C)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vite-plus/test";
import { E_SORT_ORDER, EActivityFilterType, defaultActivityFilters } from "@plane/constants";
import { sanitizePeriod } from "@/components/kinerja/kinerja";
import {
  efektifFilterAktivitas,
  pilihanTersimpanAtauAturan,
  posisiKotakKomentar,
  urutkanBalasan,
} from "@/lib/tampilan-bawaan";

describe("efektifFilterAktivitas", () => {
  it("bawaan aturan = keempat filter, sama dengan dulu", () => {
    expect(efektifFilterAktivitas(null, ["ACTIVITY", "COMMENT", "STATE", "ASSIGNEE"])).toEqual(defaultActivityFilters);
  });
  it("aturan kosong berarti keempat filter", () => {
    expect(efektifFilterAktivitas(null, [])).toBe(defaultActivityFilters);
  });
  it("nilai aturan lain dipakai selagi belum ada pilihan tersimpan", () => {
    expect(efektifFilterAktivitas(null, ["COMMENT"])).toEqual([EActivityFilterType.COMMENT]);
  });
  it("pilihan tersimpan menang atas aturan", () => {
    expect(efektifFilterAktivitas([EActivityFilterType.STATE], ["COMMENT"])).toEqual([EActivityFilterType.STATE]);
  });
  it("tersimpan rusak atau kosong dianggap belum memilih", () => {
    expect(efektifFilterAktivitas("x", ["COMMENT"])).toEqual([EActivityFilterType.COMMENT]);
    expect(efektifFilterAktivitas([], ["COMMENT"])).toEqual([EActivityFilterType.COMMENT]);
  });
});

describe("posisiKotakKomentar", () => {
  it("follow mengikuti urutan linimasa, seperti dulu", () => {
    expect(posisiKotakKomentar("follow", E_SORT_ORDER.DESC)).toBe("top");
    expect(posisiKotakKomentar("follow", E_SORT_ORDER.ASC)).toBe("bottom");
  });
  it("top dan bottom mengunci posisi", () => {
    expect(posisiKotakKomentar("top", E_SORT_ORDER.ASC)).toBe("top");
    expect(posisiKotakKomentar("bottom", E_SORT_ORDER.DESC)).toBe("bottom");
  });
});

const ids = (xs: { id: string }[]) => xs.map((x) => x.id);

describe("urutkanBalasan", () => {
  const a = { id: "a", created_at: "2026-01-01T00:00:00Z" };
  const b = { id: "b", created_at: "2026-01-02T00:00:00Z" };
  const c = { id: "c", created_at: "2026-01-03T00:00:00Z" };

  it("oldest selalu terlama dulu, apa pun urutan linimasa", () => {
    expect(ids(urutkanBalasan([c, a, b], "oldest", E_SORT_ORDER.DESC))).toEqual(["a", "b", "c"]);
    expect(ids(urutkanBalasan([c, a, b], "oldest", E_SORT_ORDER.ASC))).toEqual(["a", "b", "c"]);
  });
  it("timeline mengikuti urutan linimasa", () => {
    expect(ids(urutkanBalasan([a, c, b], "timeline", E_SORT_ORDER.DESC))).toEqual(["c", "b", "a"]);
    expect(ids(urutkanBalasan([c, a, b], "timeline", E_SORT_ORDER.ASC))).toEqual(["a", "b", "c"]);
  });
  it("tidak mengubah array masukan", () => {
    const input = [c, a];
    urutkanBalasan(input, "oldest", E_SORT_ORDER.DESC);
    expect(ids(input)).toEqual(["c", "a"]);
  });
});

describe("pilihanTersimpanAtauAturan", () => {
  const MODES = ["ringkas", "rinci", "laporan"] as const;
  it("belum ada pilihan: nilai aturan", () => {
    expect(pilihanTersimpanAtauAturan(null, MODES, "ringkas")).toBe("ringkas");
    expect(pilihanTersimpanAtauAturan(null, MODES, "rinci")).toBe("rinci");
  });
  it("pilihan tersimpan menang atas aturan", () => {
    expect(pilihanTersimpanAtauAturan("laporan", MODES, "rinci")).toBe("laporan");
  });
  it("tersimpan di luar daftar jatuh ke aturan", () => {
    expect(pilihanTersimpanAtauAturan("lain", MODES, "rinci")).toBe("rinci");
  });
});

describe("sanitizePeriod dengan bawaan aturan", () => {
  it("tanpa argumen tetap bulan ini", () => {
    expect(sanitizePeriod(null)).toEqual({ key: "this_month" });
  });
  it("belum ada pilihan: periode dari aturan", () => {
    expect(sanitizePeriod(null, "this_week")).toEqual({ key: "this_week" });
  });
  it("pilihan tersimpan menang atas aturan", () => {
    expect(sanitizePeriod({ key: "30d" }, "this_week")).toEqual({ key: "30d" });
  });
  it("rentang khusus rusak jatuh ke aturan", () => {
    expect(sanitizePeriod({ key: "custom" }, "this_quarter")).toEqual({ key: "this_quarter" });
  });
});
