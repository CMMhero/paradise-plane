/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: cermin web aturan God Mode tetap seirama dengan API
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Registri aturan ditulis Python, jadi dibaca dari sumbernya (seperti
 * paradise-navigation.test.ts). Aturannya: setiap `Rule(` dengan `web=True` di
 * apps/api/plane/utils/aturan/area_<nama>.py punya cermin di area-<nama>.ts
 * dengan bawaan dan pilihan yang sama, dan sebaliknya. Python menjaga sisi lain:
 * test_aturan_registri.py memastikan `default=` aturan web berupa literal satu baris.
 */

import { readFileSync, readdirSync } from "node:fs";
import { describe, expect, it } from "vite-plus/test";
import {
  WORKSPACE_SIDEBAR_DYNAMIC_NAVIGATION_ITEMS_LINKS,
  WORKSPACE_SIDEBAR_STATIC_NAVIGATION_ITEMS,
} from "../workspace";
import { ATURAN_WEB, DIRECTOR_SIDEBAR_HIDDEN_KEYS, DIRECTOR_SIDEBAR_HIDES_CHOICES, nilaiAturanWeb } from "./index";
import type { TKunciAturanWeb } from "./index";

const ROOT = new URL("../../../../", import.meta.url);
const DIR_API = "apps/api/plane/utils/aturan/";
const baca = (path: string): string => readFileSync(new URL(path, ROOT), "utf8");

type TAturanPython = { key: string; area: string; default: unknown; choices: unknown[] | null };

/** Literal Python sederhana -> JS: True/False, bilangan bulat, "teks", tuple/list teks atau angka. */
const literal = (teks: string): unknown => {
  const t = teks.trim();
  if (t === "True") return true;
  if (t === "False") return false;
  if (/^-?\d+$/.test(t)) return Number(t);
  if (/^"[^"]*"$/.test(t)) return t.slice(1, -1);
  if (/^[([]/.test(t)) {
    const isi = t.slice(1, -1).trim();
    return isi === ""
      ? []
      : isi
          .split(",")
          .filter((b) => b.trim() !== "")
          .map((b) => literal(b));
  }
  throw new Error(`Literal Python tidak dikenal: ${t}`);
};

const aturanWebPython = (): TAturanPython[] =>
  readdirSync(new URL(DIR_API, ROOT))
    .filter((f) => /^area_[a-z_]+\.py$/.test(f))
    .flatMap((berkas) => {
      const sumber = baca(`${DIR_API}${berkas}`);
      const konstanta = Object.fromEntries(
        [...sumber.matchAll(/^([A-Z][A-Z0-9_]*) = "([A-Z0-9_]+)"$/gm)].map((m) => [m[1], m[2]])
      );
      return sumber
        .split("Rule(")
        .slice(1)
        .filter((blok) => /^\s*web=True,\s*$/m.test(blok))
        .map((blok) => {
          const kunci = /^\s*key=(?:"([A-Z0-9_]+)"|([A-Z][A-Z0-9_]*)),\s*$/m.exec(blok);
          const bawaan = /^\s*default=(.+),\s*$/m.exec(blok);
          if (!kunci || !bawaan) throw new Error(`${berkas}: aturan web tanpa key= atau default= satu baris`);
          // `choices=(20, 30),` di satu baris, atau satu pasangan (nilai, "Label") per baris.
          const sebaris = /^\s*choices=\((.+)\),\s*$/m.exec(blok);
          const berbaris = sebaris ? null : /^\s*choices=\(\s*$([\s\S]*?)^\s*\),\s*$/m.exec(blok);
          return {
            key: kunci[1] ?? konstanta[kunci[2]],
            area: berkas.slice("area_".length, -".py".length),
            default: literal(bawaan[1]),
            choices: sebaris
              ? (literal(`(${sebaris[1]})`) as unknown[])
              : berbaris
                ? [...berbaris[1].matchAll(/^\s*\(\s*("[^"]*"|-?\d+)\s*,/gm)].map((m) => literal(m[1]))
                : null,
          };
        });
    });

describe("cermin web aturan God Mode", () => {
  const python = aturanWebPython();

  it("membaca aturan web dari Python (pembaca tidak buta)", () => {
    expect(python.map((a) => a.key)).toContain("DIRECTOR_SIDEBAR_HIDES");
  });

  it("kunci aturan web sama persis di kedua sisi", () => {
    expect(new Set(Object.keys(ATURAN_WEB))).toEqual(new Set(python.map((a) => a.key)));
  });

  it("bawaan dan pilihan sama dengan Python", () => {
    for (const a of python) {
      const web = ATURAN_WEB[a.key as TKunciAturanWeb] as { default: unknown; choices?: readonly unknown[] };
      expect(web.default, a.key).toEqual(a.default);
      if (a.choices) expect([...(web.choices ?? [])], a.key).toEqual(a.choices);
    }
  });

  it("setiap aturan web tinggal di berkas area yang sama namanya", () => {
    for (const a of python) {
      expect(baca(`packages/constants/src/aturan/area-${a.area.replaceAll("_", "-")}.ts`), a.key).toContain(a.key);
    }
  });
});

describe("nilaiAturanWeb", () => {
  it("memakai nilai server yang sah", () => {
    expect(nilaiAturanWeb({ DIRECTOR_SIDEBAR_HIDES: "none" }, "DIRECTOR_SIDEBAR_HIDES")).toBe("none");
  });

  it("jatuh ke bawaan untuk nilai hilang, salah jenis, atau di luar pilihan", () => {
    expect(nilaiAturanWeb(undefined, "DIRECTOR_SIDEBAR_HIDES")).toBe("archives");
    expect(nilaiAturanWeb({ DIRECTOR_SIDEBAR_HIDES: 1 }, "DIRECTOR_SIDEBAR_HIDES")).toBe("archives");
    expect(nilaiAturanWeb({ DIRECTOR_SIDEBAR_HIDES: "everything" }, "DIRECTOR_SIDEBAR_HIDES")).toBe("archives");
  });
});

describe("DIRECTOR_SIDEBAR_HIDES", () => {
  it("bawaan = perilaku sebelum aturannya ada: hanya Arsip", () => {
    expect(DIRECTOR_SIDEBAR_HIDDEN_KEYS[ATURAN_WEB.DIRECTOR_SIDEBAR_HIDES.default]).toEqual(["archives"]);
  });

  it("setiap pilihan menyembunyikan kunci menu sidebar yang memang ada", () => {
    const kunciMenu = new Set([
      ...WORKSPACE_SIDEBAR_DYNAMIC_NAVIGATION_ITEMS_LINKS.map((i) => i.key),
      ...Object.values(WORKSPACE_SIDEBAR_STATIC_NAVIGATION_ITEMS).map((i) => i.key),
    ]);
    for (const pilihan of DIRECTOR_SIDEBAR_HIDES_CHOICES) {
      for (const kunci of DIRECTOR_SIDEBAR_HIDDEN_KEYS[pilihan])
        expect(kunciMenu, `${pilihan}: ${kunci}`).toContain(kunci);
    }
  });
});
