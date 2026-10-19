/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: relai obrolan & sinyal
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { ObrolanController } from "@/controllers/obrolan.controller";

/**
 * Yang diuji hanya keputusan SIAPA MENERIMA APA.
 *
 * Bukan "apakah soketnya menyambung", itu urusan express-ws. Yang diuji di sini
 * satu-satunya tempat di seluruh fitur ini yang bisa membocorkan sesuatu tanpa
 * gejala: sinyal panggilan yang salah alamat tidak melempar error di mana pun,
 * ia sekadar sampai ke orang yang tidak berhak, dan tidak ada yang tahu.
 */

vi.mock("@plane/logger", () => ({
  logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));
vi.mock("@/redis", () => ({ redisManager: { getClient: () => null } }));
vi.mock("@/env", () => ({ env: { API_BASE_URL: "http://api" } }));
vi.mock("@plane/decorators", () => ({
  Controller: () => () => undefined,
  WebSocket: () => () => undefined,
}));

const TERBUKA = 1;
const TERTUTUP = 3;

type SoketPalsu = { readyState: number; OPEN: number; send: ReturnType<typeof vi.fn> };

function soket(readyState = TERBUKA): SoketPalsu {
  return { readyState, OPEN: TERBUKA, send: vi.fn() };
}

describe("relai obrolan", () => {
  let controller: ObrolanController;
  // `teruskan` dan peta klien sengaja privat. Uji ini menembusnya karena yang
  // diperiksa memang keputusan internalnya, bukan permukaan publiknya.
  let panggilTeruskan: (ruang: string, muatan: string) => void;
  let pasang: (ruang: string, klien: { ws: SoketPalsu; userId: string; ruang: string }[]) => void;

  beforeEach(() => {
    controller = new ObrolanController();
    const bebas = controller as unknown as {
      teruskan: (ruang: string, muatan: string) => void;
      klien: Map<string, Set<unknown>>;
    };
    panggilTeruskan = (ruang, muatan) => bebas.teruskan(ruang, muatan);
    pasang = (ruang, daftar) => bebas.klien.set(ruang, new Set(daftar));
  });

  it("sinyal panggilan hanya sampai ke orang yang dituju", () => {
    const budi = soket();
    const citra = soket();
    pasang("R1", [
      { ws: budi, userId: "budi", ruang: "R1" },
      { ws: citra, userId: "citra", ruang: "R1" },
    ]);

    panggilTeruskan("R1", JSON.stringify({ tipe: "sinyal", dari: "aku", ke: "budi", muatan: {} }));

    expect(budi.send).toHaveBeenCalledTimes(1);
    // Kalau baris ini pernah gagal, artinya siapa pun di ruang yang sama bisa
    // menguping perkenalan panggilan orang lain.
    expect(citra.send).not.toHaveBeenCalled();
  });

  it("siaran pesan tidak digaungkan balik ke pengirimnya", () => {
    const aku = soket();
    const budi = soket();
    pasang("R1", [
      { ws: aku, userId: "aku", ruang: "R1" },
      { ws: budi, userId: "budi", ruang: "R1" },
    ]);

    panggilTeruskan("R1", JSON.stringify({ tipe: "pesan", ruang: "R1", oleh: "aku" }));

    // Pengirim sudah memperbarui layarnya sendiri saat menekan kirim; menarik
    // ulang sekali lagi membuat pesannya berkedip.
    expect(aku.send).not.toHaveBeenCalled();
    expect(budi.send).toHaveBeenCalledTimes(1);
  });

  it("siaran tanpa pengirim sampai ke semua orang di ruang itu", () => {
    const aku = soket();
    const budi = soket();
    pasang("R1", [
      { ws: aku, userId: "aku", ruang: "R1" },
      { ws: budi, userId: "budi", ruang: "R1" },
    ]);

    panggilTeruskan("R1", JSON.stringify({ tipe: "hapus", ruang: "R1", oleh: null }));

    expect(aku.send).toHaveBeenCalledTimes(1);
    expect(budi.send).toHaveBeenCalledTimes(1);
  });

  it("ruang lain tidak ikut menerima apa pun", () => {
    const diR1 = soket();
    const diR2 = soket();
    pasang("R1", [{ ws: diR1, userId: "aku", ruang: "R1" }]);
    pasang("R2", [{ ws: diR2, userId: "budi", ruang: "R2" }]);

    panggilTeruskan("R1", JSON.stringify({ tipe: "pesan", ruang: "R1", oleh: "x" }));

    expect(diR1.send).toHaveBeenCalledTimes(1);
    expect(diR2.send).not.toHaveBeenCalled();
  });

  it("soket yang sudah tertutup dilewati, bukan ditulisi", () => {
    const mati = soket(TERTUTUP);
    pasang("R1", [{ ws: mati, userId: "aku", ruang: "R1" }]);

    panggilTeruskan("R1", JSON.stringify({ tipe: "pesan", ruang: "R1", oleh: "x" }));

    // Menulis ke soket yang sudah tertutup melempar, dan lemparannya terjadi di
    // dalam handler Redis tempat tidak ada yang menangkapnya.
    expect(mati.send).not.toHaveBeenCalled();
  });

  it("muatan yang bukan JSON diabaikan tanpa menjatuhkan proses", () => {
    const aku = soket();
    pasang("R1", [{ ws: aku, userId: "aku", ruang: "R1" }]);

    expect(() => panggilTeruskan("R1", "bukan json {{{")).not.toThrow();
    expect(aku.send).not.toHaveBeenCalled();
  });

  it("ruang tanpa satu pun klien tidak menimbulkan galat", () => {
    expect(() => panggilTeruskan("kosong", JSON.stringify({ tipe: "pesan" }))).not.toThrow();
  });
});
