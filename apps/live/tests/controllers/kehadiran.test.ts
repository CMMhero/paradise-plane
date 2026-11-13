/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: indikator kehadiran obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vite-plus/test";
import { BATAS_DETAK_MS, PenyimpanMemori, ringkasKehadiran } from "@/controllers/kehadiran";

describe("ringkas kehadiran", () => {
  const sekarang = 1_000_000;

  it("status orang = status terbaik dari tab-tabnya yang masih berdetak", () => {
    const { peta } = ringkasKehadiran(
      {
        "budi:tab1": `away:${sekarang - 1000}`,
        "budi:tab2": `online:${sekarang - 2000}`,
        "citra:tab1": `away:${sekarang}`,
      },
      sekarang
    );
    expect(peta).toEqual({ budi: "online", citra: "away" });
  });

  it("tab yang berhenti berdetak dianggap pergi dan ditandai basi", () => {
    const { peta, basi } = ringkasKehadiran(
      {
        "budi:tab1": `online:${sekarang - BATAS_DETAK_MS - 1}`,
        "citra:tab1": `online:${sekarang}`,
      },
      sekarang
    );
    // Tanpa ini, tab yang ditutup paksa membuat orangnya "online" selamanya.
    expect(peta).toEqual({ citra: "online" });
    expect(basi).toEqual(["budi:tab1"]);
  });

  it("nilai rusak dibuang, bukan dipercaya", () => {
    const { peta, basi } = ringkasKehadiran(
      { "budi:tab1": "hadir:abc", "tanpa-tab": `online:${sekarang}`, "citra:t": `sibuk:${sekarang}` },
      sekarang
    );
    expect(peta).toEqual({});
    expect(basi).toHaveLength(3);
  });

  it("penyimpan memori menghapus workspace kosong", async () => {
    const simpan = new PenyimpanMemori();
    await simpan.catat("ws", "budi:t1", `online:${sekarang}`);
    expect(await simpan.semua("ws")).toEqual({ "budi:t1": `online:${sekarang}` });
    await simpan.hapus("ws", "budi:t1");
    expect(await simpan.semua("ws")).toEqual({});
  });
});
