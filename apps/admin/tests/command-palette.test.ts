/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: command palette search
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
import { settingsStrings } from "@/app/i18n/godmode-settings";
import { MENU_TABS } from "@/components/common/menu-tree";
import { buildPaletteEntries, searchPalette, settingAnchor } from "@/components/command-palette/entries";
import { fuzzyScore, normalize, tokenScore } from "@/components/command-palette/fuzzy";
import { SETTINGS_LAYOUT } from "@/components/settings/layouts";

const entries = buildPaletteEntries(settingsStrings);
const topIds = (query: string, n = 3) =>
  searchPalette(entries, query)
    .slice(0, n)
    .map((m) => m.entry.id);

describe("normalize", () => {
  it("lowercases, strips accents and splits setting keys into words", () => {
    expect(normalize("  Café EMAIL_BATCH_DELAY  ")).toBe("cafe email batch delay");
  });
});

describe("tokenScore", () => {
  it("ranks whole word > word start > inside > typo > scattered letters", () => {
    const whole = tokenScore("email", "work item email");
    const start = tokenScore("ema", "work item email");
    const inside = tokenScore("mail", "work item email");
    const typo = tokenScore("emial", "work item email");
    const scattered = tokenScore("wie", "work item email");
    expect(whole).toBeGreaterThan(start);
    expect(start).toBeGreaterThan(inside);
    expect(inside).toBeGreaterThan(typo);
    expect(typo).toBeGreaterThan(scattered);
    expect(scattered).toBeGreaterThan(0);
  });

  it("returns 0 when the letters are not there in order", () => {
    expect(tokenScore("xyz", "work item email")).toBe(0);
    expect(tokenScore("", "anything")).toBe(0);
  });

  it("forgives a swapped pair of letters in longer words", () => {
    expect(tokenScore("aprpoval", "approvals")).toBeGreaterThan(0);
  });
});

describe("fuzzyScore", () => {
  it("needs every query word to land somewhere", () => {
    const fields = [
      { text: "Batch delay", weight: 1 },
      { text: "Collects work item email", weight: 0.6 },
    ];
    expect(fuzzyScore("email delay", fields)).toBeGreaterThan(0);
    expect(fuzzyScore("email zzzz", fields)).toBe(0);
  });

  it("prefers a hit in the title over the same hit in the description", () => {
    const inTitle = fuzzyScore("timezone", [
      { text: "Office timezone", weight: 1 },
      { text: "", weight: 0.6 },
    ]);
    const inHelp = fuzzyScore("timezone", [
      { text: "Office", weight: 1 },
      { text: "The timezone", weight: 0.6 },
    ]);
    expect(inTitle).toBeGreaterThan(inHelp);
  });
});

describe("buildPaletteEntries", () => {
  it("indexes every menu, every tab and every registry row once", () => {
    const tabCount = Object.values(MENU_TABS).flat().length;
    const rowCount = Object.values(SETTINGS_LAYOUT)
      .flat()
      .flatMap((s) => s.rows).length;
    expect(entries.filter((e) => e.kind === "menu")).toHaveLength(Object.keys(MENU_TABS).length);
    expect(entries.filter((e) => e.kind === "tab")).toHaveLength(tabCount);
    expect(entries.filter((e) => e.kind === "setting")).toHaveLength(rowCount);
    expect(new Set(entries.map((e) => e.id)).size).toBe(entries.length);
  });

  it("links a setting to its tab with an anchor on the row", () => {
    const entry = entries.find((e) => e.id === "setting:TASK_DELETE_RULE");
    expect(entry?.href).toBe(`/rules/#${settingAnchor("TASK_DELETE_RULE")}`);
    const t = settingsStrings;
    expect(entry?.path).toEqual([t.menus.rules.title, t.tabs.rules_approvals.title, t.sections.ownership.title]);
  });

  it("indexes the Permissions tab with one row per resource rule", () => {
    const t = settingsStrings;
    expect(entries.find((e) => e.id === "tab:rules_permissions")?.href).toBe("/rules/permissions/");
    const perms = entries.filter((e) => e.kind === "setting" && e.href.startsWith("/rules/permissions/"));
    expect(perms).toHaveLength(18);
    const comment = perms.find((e) => e.id === "setting:PERM_COMMENT_EDIT");
    expect(comment?.path).toEqual([
      t.menus.rules.title,
      t.tabs.rules_permissions.title,
      t.sections.perm_comments.title,
    ]);
    expect(comment?.keywords).toContain("Owner and their superiors");
    expect(perms.find((e) => e.id === "setting:PERM_TRASH_PURGE")?.keywords).toContain("Admins only");
  });

  it("finds a permission rule by plain words", () => {
    const ids = searchPalette(entries, "delete comment").map((m) => m.entry.id);
    expect(ids).toContain("setting:PERM_COMMENT_DELETE");
  });

  it("leaves out rows the server registry does not know", () => {
    const known = new Set(["OFFICE_TIMEZONE"]);
    const settings = buildPaletteEntries(settingsStrings, known).filter((e) => e.kind === "setting");
    expect(settings.map((e) => e.id)).toEqual(["setting:OFFICE_TIMEZONE"]);
  });
});

describe("searchPalette", () => {
  it("finds a setting by its title", () => {
    expect(topIds("office timezone", 1)).toEqual(["setting:OFFICE_TIMEZONE"]);
  });

  it("finds a setting by words that only appear in its help text", () => {
    const ids = searchPalette(entries, "sign in again").map((m) => m.entry.id);
    expect(ids).toContain("setting:SESSION_DAYS");
  });

  it("finds a setting by one of its choice labels", () => {
    const ids = searchPalette(entries, "creator super admin").map((m) => m.entry.id);
    expect(ids).toContain("setting:TASK_DELETE_RULE");
  });

  it("finds a setting by its registry key", () => {
    expect(topIds("UPLOAD_MAX_MB", 1)).toEqual(["setting:UPLOAD_MAX_MB"]);
  });

  it("survives a typo", () => {
    expect(searchPalette(entries, "invitaton").map((m) => m.entry.id)).toContain("setting:INVITE_EXPIRY_DAYS");
  });

  it("returns nothing for gibberish", () => {
    expect(searchPalette(entries, "qqzzxx")).toEqual([]);
  });

  it("caps the number of results", () => {
    expect(searchPalette(entries, "e", 5)).toHaveLength(5);
  });
});
