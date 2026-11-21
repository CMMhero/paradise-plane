/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: registri menu tetap seirama dengan API dan locale
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * API ditulis Python dan tidak bisa mengimpor registri ini, jadi daftarnya
 * dicocokkan dengan membaca sumbernya. Tes gagal begitu satu sisi menambah
 * atau membuang kunci tanpa sisi lain.
 */

import { readFileSync, readdirSync } from "node:fs";
import { describe, expect, it } from "vite-plus/test";
import { PARADISE_MODULE_DEFAULTS } from "./paradise-features";
import { PARADISE_MODULES, PARADISE_NAV_ITEMS, PARADISE_NAV_PREFERENCE_KEYS } from "./paradise-navigation";
import { WORKSPACE_SIDEBAR_DYNAMIC_NAVIGATION_ITEMS_LINKS } from "./workspace";

const ROOT = new URL("../../../", import.meta.url);
const baca = (path: string): string => readFileSync(new URL(path, ROOT), "utf8");

/** Isi blok Python sesudah `pembuka` sampai `penutup` pertama. */
const blokPython = (sumber: string, pembuka: string, penutup: RegExp): string => {
  const awal = sumber.indexOf(pembuka);
  if (awal < 0) throw new Error(`${pembuka} tidak ditemukan`);
  const isi = sumber.slice(awal + pembuka.length);
  return isi.slice(0, isi.search(penutup));
};
const stringDi = (blok: string): string[] => [...blok.matchAll(/"([a-z_]+)"/g)].map((m) => m[1]);

/** Semua berkas JSON satu locale. Namespace yang sama bisa tersebar di beberapa berkas. */
const kamus = (locale: string): Record<string, unknown>[] => {
  const dir = `packages/i18n/src/locales/${locale}/`;
  return readdirSync(new URL(dir, ROOT))
    .filter((f) => f.endsWith(".json"))
    .map((f) => JSON.parse(baca(`${dir}${f}`)) as Record<string, unknown>);
};
const adaDi = (berkas: Record<string, unknown>, kunci: string): boolean => {
  let isi: unknown = berkas;
  for (const bagian of kunci.split(".")) {
    if (typeof isi !== "object" || isi === null || !(bagian in isi)) return false;
    isi = (isi as Record<string, unknown>)[bagian];
  }
  return typeof isi === "string" && isi.length > 0;
};
const ada = (semua: Record<string, unknown>[], kunci: string): boolean => semua.some((b) => adaDi(b, kunci));

describe("PARADISE_MODULES", () => {
  it("sama dengan _MODUL_BAWAAN di API, kunci dan bawaannya", () => {
    const blok = blokPython(baca("apps/api/plane/utils/saklar_instance.py"), "_MODUL_BAWAAN = {", /\n\}/);
    const api = Object.fromEntries([...blok.matchAll(/^\s*"([a-z_]+)": "([01])"/gm)].map((m) => [m[1], m[2] === "1"]));
    expect(api).toEqual(PARADISE_MODULE_DEFAULTS);
    expect(Object.keys(api)).toEqual(Object.keys(PARADISE_MODULES));
  });
});

describe("PARADISE_NAV_PREFERENCE_KEYS", () => {
  it("sama dengan NAV_PRIBADI dan NAV_WORKSPACE di API, urutannya juga", () => {
    const sumber = baca("apps/api/plane/utils/bawaan_member.py");
    expect(stringDi(blokPython(sumber, "NAV_PRIBADI = (", /\)/))).toEqual([...PARADISE_NAV_PREFERENCE_KEYS.personal]);
    expect(stringDi(blokPython(sumber, "NAV_WORKSPACE = (", /\)/))).toEqual([
      ...PARADISE_NAV_PREFERENCE_KEYS.workspace,
    ]);
  });

  it("punya baris WorkspaceUserPreference, kalau tidak menyematkannya diam-diam gagal", () => {
    const blok = blokPython(
      baca("apps/api/plane/db/models/workspace.py"),
      "class UserPreferenceKeys(models.TextChoices):",
      /\n\n/
    );
    const kunci = new Set([...blok.matchAll(/= "([a-z_]+)", "/g)].map((m) => m[1]));
    for (const k of [...PARADISE_NAV_PREFERENCE_KEYS.personal, ...PARADISE_NAV_PREFERENCE_KEYS.workspace]) {
      expect(kunci, k).toContain(k);
    }
  });
});

describe("PARADISE_NAV_ITEMS", () => {
  it("tiap menu Paradise ada di sidebar workspace, sekali, urutan registri", () => {
    const sidebar = WORKSPACE_SIDEBAR_DYNAMIC_NAVIGATION_ITEMS_LINKS.map((i) => i.key);
    const paradise = sidebar.filter((k) => PARADISE_NAV_ITEMS.some((i) => i.key === k));
    expect(paradise).toEqual(PARADISE_NAV_ITEMS.map((i) => i.key));
  });

  it("id perintah Power K unik", () => {
    const ids = PARADISE_NAV_ITEMS.flatMap((i) => ("palette" in i ? [i.palette.id] : []));
    expect(new Set(ids).size).toBe(ids.length);
  });

  it.each(["en", "id"])("label dan judul perintah ada di locale %s", (locale) => {
    const k = kamus(locale);
    for (const item of PARADISE_NAV_ITEMS) {
      expect(ada(k, item.labelTranslationKey), `${item.key}: ${item.labelTranslationKey}`).toBe(true);
      if (!("palette" in item)) continue;
      const judul =
        "titleKey" in item.palette ? item.palette.titleKey : `power_k.navigation_actions.${item.palette.id}`;
      expect(ada(k, judul), `${item.palette.id}: ${judul}`).toBe(true);
    }
  });
});
