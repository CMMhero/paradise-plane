/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: what the God Mode command palette can find
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * The index is built from the same sources the pages use, so it never drifts:
 * menus and tabs from the menu tree, settings from SETTINGS_LAYOUT plus their
 * help strings. Nothing here is typed in twice.
 */

import type { TGodmodeStrings } from "@/app/i18n/godmode";
import { MENU_TABS } from "@/components/common/menu-tree";
import type { TMenuId, TTabId } from "@/components/common/menu-tree";
import { SETTINGS_LAYOUT } from "@/components/settings/layouts";
import type { TSettingsTabId } from "@/components/settings/layouts";
import { describeField } from "@/components/settings/setting-utils";
import { fuzzyScore } from "./fuzzy";

type TSettingStrings = TGodmodeStrings["settings"];

export type TPaletteEntryKind = "menu" | "tab" | "setting";

export type TPaletteEntry = {
  id: string;
  kind: TPaletteEntryKind;
  menu: TMenuId;
  title: string;
  description: string;
  /** Where it lives, outermost first: menu, tab, section. */
  path: string[];
  /** Searchable but not shown: setting key, choice labels, unit, section hint. */
  keywords: string[];
  href: string;
};

/** DOM id of a registry setting row; the palette links to `<tab>#<anchor>`. */
export const settingAnchor = (key: string): string => `setting-${key}`;

/** Field weights: a hit in the title beats one in the help text. */
const WEIGHT = { title: 1, keywords: 0.8, description: 0.65, path: 0.55 } as const;

const tabOf = (layoutId: TSettingsTabId): { menu: TMenuId; id: TTabId; href: string } | undefined => {
  for (const menu of Object.keys(MENU_TABS) as TMenuId[]) {
    const tab = MENU_TABS[menu].find((t) => t.id === layoutId);
    if (tab) return { menu, ...tab };
  }
  return undefined;
};

/**
 * Every menu, tab and registry setting. When `knownKeys` is given (the server
 * registry has loaded), rows the server does not know are left out, the same
 * rule the settings tabs follow.
 */
export function buildPaletteEntries(t: TSettingStrings, knownKeys?: ReadonlySet<string>): TPaletteEntry[] {
  const entries: TPaletteEntry[] = [];

  for (const menu of Object.keys(MENU_TABS) as TMenuId[]) {
    const menuStrings = t.menus[menu];
    const tabs = MENU_TABS[menu];
    entries.push({
      id: `menu:${menu}`,
      kind: "menu",
      menu,
      title: menuStrings.title,
      description: menuStrings.description,
      path: [],
      keywords: tabs.map((tab) => t.tabs[tab.id].title),
      href: tabs[0].href,
    });
    for (const tab of tabs) {
      const tabStrings = t.tabs[tab.id];
      entries.push({
        id: `tab:${tab.id}`,
        kind: "tab",
        menu,
        title: tabStrings.title,
        description: tabStrings.description,
        path: [menuStrings.title],
        keywords: [],
        href: tab.href,
      });
    }
  }

  for (const layoutId of Object.keys(SETTINGS_LAYOUT) as TSettingsTabId[]) {
    const tab = tabOf(layoutId);
    if (!tab) continue;
    for (const section of SETTINGS_LAYOUT[layoutId]) {
      const sectionStrings = t.sections[section.id] as { title: string; hint?: string };
      for (const row of section.rows) {
        if (knownKeys && !knownKeys.has(row.key)) continue;
        const { name, help } = describeField(t, row.key);
        const choices = Object.values(t.choices[row.key] ?? {});
        const unit = row.unit ? t.units[row.unit] : undefined;
        entries.push({
          id: `setting:${row.key}`,
          kind: "setting",
          menu: tab.menu,
          title: name,
          description: help,
          path: [t.menus[tab.menu].title, t.tabs[tab.id].title, sectionStrings.title],
          keywords: [
            row.key,
            ...choices,
            ...(unit ? [unit] : []),
            ...(sectionStrings.hint ? [sectionStrings.hint] : []),
          ],
          href: `${tab.href}#${settingAnchor(row.key)}`,
        });
      }
    }
  }

  return entries;
}

export type TPaletteMatch = { entry: TPaletteEntry; score: number };

/** Entries matching `query`, best first. Ties keep index order (menus, tabs, settings). */
export function searchPalette(entries: TPaletteEntry[], query: string, limit = 50): TPaletteMatch[] {
  const matches: TPaletteMatch[] = [];
  for (const entry of entries) {
    const score = fuzzyScore(query, [
      { text: entry.title, weight: WEIGHT.title },
      { text: entry.keywords.join(" · "), weight: WEIGHT.keywords },
      { text: entry.description, weight: WEIGHT.description },
      { text: entry.path.join(" · "), weight: WEIGHT.path },
    ]);
    if (score > 0) matches.push({ entry, score });
  }
  return (
    matches
      // oxlint-disable-next-line unicorn/no-array-sort -- lib ES2022 has no toSorted; array is already a local copy
      .sort((a, b) => b.score - a.score)
      .slice(0, limit)
  );
}
