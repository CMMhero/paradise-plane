/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: the God Mode menu tree, routes, rows and strings agree
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * routes.ts cannot import the menu tree (it is read while the router is being
 * built, see alamat-lama-map.ts), so the two are checked here instead.
 */

import { describe, expect, it } from "vite-plus/test";
import { PARADISE_MODULES } from "@plane/constants";
import { settingsStrings } from "@/app/i18n/godmode-settings";
import routes from "@/app/routes";
import { buildPaletteEntries } from "@/components/command-palette/entries";
import { MENU_TABS } from "@/components/common/menu-tree";
import { SETTINGS_LAYOUT } from "@/components/settings/layouts";
import type { TSettingsTabId } from "@/components/settings/layouts";
import { describeField } from "@/components/settings/setting-utils";
import { coreSidebarMenuLinks } from "@/hooks/use-sidebar-menu/core";

type TRoute = { path?: string; file: string; children?: TRoute[] };
const flatten = (list: TRoute[]): TRoute[] => list.flatMap((r) => [r, ...flatten(r.children ?? [])]);
const allRoutes = flatten(routes as TRoute[]);
const fileOf = (href: string) => allRoutes.find((r) => r.path === href.replace(/^\/|\/$/g, ""))?.file;

const tabs = Object.values(MENU_TABS).flat();
const SETTINGS_TAB_FILE = "./(all)/(dashboard)/settings-tab/page.tsx";

describe("God Mode menu tree", () => {
  it("every tab has a route", () => {
    for (const tab of tabs) expect(fileOf(tab.href), tab.href).toBeDefined();
  });

  it("the generic settings page serves exactly the tabs that have a registry layout", () => {
    const served = allRoutes.filter((r) => r.file === SETTINGS_TAB_FILE).map((r) => `/${r.path}/`);
    const withLayout = tabs.filter((t) => fileOf(t.href) === SETTINGS_TAB_FILE).map((t) => t.href);
    expect(new Set(served)).toEqual(new Set(withLayout));
    expect(served).toHaveLength(withLayout.length);
    for (const href of served) {
      const tab = tabs.find((t) => t.href === href);
      expect(tab && Object.hasOwn(SETTINGS_LAYOUT, tab.id), href).toBe(true);
    }
  });

  it("every layout belongs to a tab", () => {
    const ids = new Set<string>(tabs.map((t) => t.id));
    for (const id of Object.keys(SETTINGS_LAYOUT) as TSettingsTabId[]) expect(ids, id).toContain(id);
  });

  it("every tab and menu has a palette entry and the sidebar opens the first tab", () => {
    const ids = new Set(buildPaletteEntries(settingsStrings).map((e) => e.id));
    for (const menu of Object.keys(MENU_TABS) as (keyof typeof MENU_TABS)[]) {
      expect(ids).toContain(`menu:${menu}`);
      expect(coreSidebarMenuLinks[menu].href).toBe(MENU_TABS[menu][0].href);
      expect(coreSidebarMenuLinks[menu].name).toBe(settingsStrings.menus[menu].title);
    }
    for (const tab of tabs) expect(ids).toContain(`tab:${tab.id}`);
  });
});

describe("God Mode setting rows", () => {
  const rows = Object.values(SETTINGS_LAYOUT)
    .flat()
    .flatMap((s) => s.rows);

  it("every row has a name and help text", () => {
    for (const { key } of rows) {
      const { name, help } = describeField(settingsStrings, key);
      expect(name, key).not.toBe(key);
      expect(help, key).not.toBe("");
    }
  });

  it("Visibility lists every module exactly once", () => {
    const visibility = SETTINGS_LAYOUT.modules_visibility.flatMap((s) => s.rows.map((r) => r.key));
    expect(visibility).toEqual(Object.keys(PARADISE_MODULES).map((m) => `ENABLE_${m.toUpperCase()}`));
  });
});
