/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: penjaga kunci terjemahan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vite-plus/test";
import { SUPPORTED_LANGUAGES } from "../constants/language";
import { NAMESPACES } from "../constants/namespaces";

const here = dirname(fileURLToPath(import.meta.url));
const localesDir = join(here, "..", "locales");
const repoRoot = join(here, "..", "..", "..", "..");

type Tree = { [key: string]: string | Tree };

/**
 * Meratakan satu bahasa persis seperti aplikasi memuatnya: hanya namespace di
 * NAMESPACES, `keySeparator: "."`, dan `fallbackNS` mencari kunci di semua
 * namespace. Pohon yang bentrok (`a.b` string sekaligus objek) dilaporkan.
 */
const flatten = (lng: string) => {
  const keys = new Map<string, string>();
  const collisions: string[] = [];
  const walk = (node: Tree, prefix: string, ns: string) => {
    for (const [k, v] of Object.entries(node)) {
      const path = prefix ? `${prefix}.${k}` : k;
      if (typeof v === "string") {
        if (keys.has(path)) collisions.push(`${path} (ada di ${keys.get(path)} dan ${ns})`);
        keys.set(path, ns);
      } else walk(v, path, ns);
    }
  };
  for (const ns of NAMESPACES) {
    walk(JSON.parse(readFileSync(join(localesDir, lng, `${ns}.json`), "utf8")) as Tree, "", ns);
  }
  // Kunci yang jadi string sekaligus awalan kunci lain tidak bisa dibaca i18next.
  const shadowed = [...keys.keys()].filter((k) => [...keys.keys()].some((o) => o.startsWith(`${k}.`)));
  return { keys, collisions, shadowed };
};

const SKIP_DIRS = new Set(["node_modules", "dist", ".next", ".turbo", "build", "i18n", "__tests__"]);
const walkFiles = (dir: string, out: string[] = []) => {
  for (const name of readdirSync(dir)) {
    if (SKIP_DIRS.has(name) || name.startsWith(".")) continue;
    const full = join(dir, name);
    if (statSync(full).isDirectory()) walkFiles(full, out);
    else if (/\.(ts|tsx)$/.test(name) && !/\.(test|spec|d)\.tsx?$/.test(name)) out.push(full);
  }
  return out;
};

const USAGE = /(?<![\w.$])t\(\s*(["'])([A-Za-z0-9_.-]+)\1/g;

const usedKeys = () => {
  const roots = ["apps/web", "apps/space"].map((r) => join(repoRoot, r));
  const pkgs = join(repoRoot, "packages");
  for (const name of readdirSync(pkgs)) if (name !== "i18n") roots.push(join(pkgs, name));
  const found = new Map<string, string>();
  for (const root of roots) {
    for (const file of walkFiles(root)) {
      const src = readFileSync(file, "utf8");
      for (const m of src.matchAll(USAGE)) {
        if (!found.has(m[2])) found.set(m[2], relative(repoRoot, file));
      }
    }
  }
  return found;
};

const parse = (lng: string) => {
  const out = new Set<string>();
  const walk = (n: Tree, p: string) => {
    for (const [k, v] of Object.entries(n)) {
      if (typeof v === "string") out.add(p ? `${p}.${k}` : k);
      else walk(v, p ? `${p}.${k}` : k);
    }
  };
  walk(JSON.parse(readFileSync(join(localesDir, lng, "paradise.json"), "utf8")) as Tree, "");
  return out;
};

describe("terjemahan", () => {
  it("setiap berkas bahasa terdaftar di NAMESPACES dan sebaliknya", () => {
    for (const { value } of SUPPORTED_LANGUAGES) {
      const files = readdirSync(join(localesDir, value))
        .filter((f) => f.endsWith(".json"))
        .map((f) => f.replace(/\.json$/, ""))
        .toSorted();
      expect(files, value).toEqual([...NAMESPACES].toSorted());
    }
  });

  it("en dan id tidak punya kunci yang bentrok", () => {
    for (const lng of ["en", "id"]) {
      const { collisions, shadowed } = flatten(lng);
      expect(collisions, `${lng}: kunci ganda`).toEqual([]);
      expect(shadowed, `${lng}: string sekaligus awalan`).toEqual([]);
    }
  });

  it('setiap t("...") statis di kode ada di en dan id', () => {
    const en = flatten("en").keys;
    const id = flatten("id").keys;
    const missing = [...usedKeys()]
      .filter(([key]) => !en.has(key) || !id.has(key))
      .map(([key, file]) =>
        `${key} (${file}) ${en.has(key) ? "" : "tanpa en "}${id.has(key) ? "" : "tanpa id"}`.trim()
      );
    expect(missing).toEqual([]);
  });

  it("paradise.json tiap bahasa punya semua kunci milik en", () => {
    const en = parse("en");
    for (const { value } of SUPPORTED_LANGUAGES) {
      const has = parse(value);
      const missing = [...en].filter((k) => !has.has(k));
      expect(missing, `${value}/paradise.json`).toEqual([]);
    }
  });
});
