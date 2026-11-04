/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: sinyal panggilan di soket kehadiran
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { ObrolanController } from "@/controllers/obrolan.controller";

vi.mock("@plane/logger", () => ({
  logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}));
vi.mock("@/redis", () => ({ redisManager: { getClient: () => null } }));
vi.mock("@/env", () => ({ env: { API_BASE_URL: "http://api" } }));
vi.mock("@plane/decorators", () => ({
  Controller: () => () => undefined,
  WebSocket: () => () => undefined,
}));

const RUANG = "11111111-1111-4111-8111-111111111111";
const SLUG = "pt-paradise";

type Soket = { readyState: number; OPEN: number; send: ReturnType<typeof vi.fn> };
type Tab = { ws: Soket; userId: string; slug: string; tab: string; status: string; cookie: string; sinyal: number[] };

const soket = (): Soket => ({ readyState: 1, OPEN: 1, send: vi.fn() });
const tab = (userId: string, id: string): Tab => ({
  ws: soket(),
  userId,
  slug: SLUG,
  tab: id,
  status: "online",
  cookie: "sid=x",
  sinyal: [],
});

const panggil = (ke = "budi", muatan: unknown = { jenis: "panggil", id: "c1", video: true }) => ({
  tipe: "panggilan",
  ke,
  ruang: RUANG,
  muatan,
});

describe("sinyal panggilan di soket kehadiran", () => {
  let controller: ObrolanController;
  let aku1: Tab, aku2: Tab, budi1: Tab, budi2: Tab, citra: Tab;
  let kirim: (dari: Tab, pesan: unknown) => Promise<void>;
  let anggotaApi: string[] | null;
  let fetchPalsu: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    anggotaApi = ["aku", "budi"];
    fetchPalsu = vi.fn(async () => ({
      ok: anggotaApi !== null,
      json: async () => anggotaApi,
    }));
    vi.stubGlobal("fetch", fetchPalsu);

    controller = new ObrolanController();
    aku1 = tab("aku", "a1");
    aku2 = tab("aku", "a2");
    budi1 = tab("budi", "b1");
    budi2 = tab("budi", "b2");
    citra = tab("citra", "c1");
    const bebas = controller as unknown as {
      klienHadir: Map<string, Set<Tab>>;
      terimaDetak: (k: Tab, d: Buffer) => Promise<void>;
    };
    bebas.klienHadir.set(SLUG, new Set([aku1, aku2, budi1, budi2, citra]));
    kirim = (dari, pesan) => bebas.terimaDetak(dari, Buffer.from(JSON.stringify(pesan)));
  });

  it("sampai ke semua tab tujuan dan tab LAIN pengirim, bukan tab pengirim", async () => {
    await kirim(aku1, panggil());

    const diharapkan = {
      tipe: "panggilan",
      dari: "aku",
      ke: "budi",
      ruang: RUANG,
      muatan: { jenis: "panggil", id: "c1", video: true },
    };
    expect(budi1.ws.send).toHaveBeenCalledTimes(1);
    expect(budi2.ws.send).toHaveBeenCalledTimes(1);
    expect(aku2.ws.send).toHaveBeenCalledTimes(1);
    expect(JSON.parse(budi1.ws.send.mock.calls[0][0])).toEqual(diharapkan);
    expect(aku1.ws.send).not.toHaveBeenCalled();
    expect(citra.ws.send).not.toHaveBeenCalled();
  });

  it("`_tab` tidak bocor ke peramban", async () => {
    await kirim(aku1, panggil());
    expect(budi1.ws.send.mock.calls[0][0]).not.toContain("_tab");
  });

  it("`dari` kiriman peramban diabaikan, server memakai identitas sendiri", async () => {
    await kirim(aku1, { ...panggil(), dari: "citra", muatan: { jenis: "panggil", id: "c1", dari: "citra" } });

    const diterima = JSON.parse(budi1.ws.send.mock.calls[0][0]);
    expect(diterima.dari).toBe("aku");
    expect(diterima.muatan).toEqual({ jenis: "panggil", id: "c1" });
  });

  it("ditolak kalau pengirim bukan anggota ruang", async () => {
    anggotaApi = null; // API menjawab 404
    await kirim(aku1, panggil());
    expect(budi1.ws.send).not.toHaveBeenCalled();
    expect(aku2.ws.send).not.toHaveBeenCalled();
  });

  it("ditolak kalau tujuan bukan anggota ruang", async () => {
    await kirim(aku1, panggil("citra"));
    expect(citra.ws.send).not.toHaveBeenCalled();
    expect(aku2.ws.send).not.toHaveBeenCalled();
  });

  it("jenis di luar daftar dan bentuk tak sah dibuang tanpa menyentuh API", async () => {
    await kirim(aku1, panggil("budi", { jenis: "retas", id: "c1" }));
    await kirim(aku1, panggil("budi", { jenis: "panggil" }));
    await kirim(aku1, panggil("budi", { jenis: "panggil", id: "x".repeat(65) }));
    await kirim(aku1, panggil("budi", { jenis: "panggil", id: "c1", video: "ya" }));
    await kirim(aku1, { ...panggil(), ruang: "bukan-uuid" });
    await kirim(aku1, panggil(""));

    expect(budi1.ws.send).not.toHaveBeenCalled();
    expect(fetchPalsu).not.toHaveBeenCalled();
  });

  it("keanggotaan di-cache: banyak sinyal hanya satu panggilan API", async () => {
    await kirim(aku1, panggil());
    await kirim(aku1, panggil("budi", { jenis: "batal", id: "c1" }));
    expect(fetchPalsu).toHaveBeenCalledTimes(1);
    expect(budi1.ws.send).toHaveBeenCalledTimes(2);
  });

  it("dibatasi 20 sinyal per 10 detik per tab", async () => {
    await Promise.all(Array.from({ length: 25 }, () => kirim(aku1, panggil())));
    expect(budi1.ws.send).toHaveBeenCalledTimes(20);
    // Tab lain tidak ikut terkena batas.
    await kirim(aku2, panggil());
    expect(budi1.ws.send).toHaveBeenCalledTimes(21);
  });
});
