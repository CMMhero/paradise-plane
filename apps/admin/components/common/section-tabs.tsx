/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tabs for grouped God Mode menus
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * One sidebar entry, several pages. The menu tree (KEP-83) is the single list
 * below: sidebar, tabs, page titles and the old-URL redirects all read it.
 */

import { useGodmodeStrings } from "@/app/i18n/godmode";
import { MENU_TABS } from "./menu-tree";
import type { TMenuId, TTabId } from "./menu-tree";
import { PageTabs } from "./paradise";

export { MENU_TABS } from "./menu-tree";
export type { TMenuId, TTabId } from "./menu-tree";

export function MenuTabs({ menu }: { menu: TMenuId }) {
  const { s } = useGodmodeStrings();
  return <PageTabs tabs={MENU_TABS[menu].map((tab) => ({ label: s.settings.tabs[tab.id].title, href: tab.href }))} />;
}

/** Page header (title = tab name, so no two tabs share a title) for a tab. */
export function useTabHeader(tab: TTabId): { title: string; description: string } {
  const { s } = useGodmodeStrings();
  return s.settings.tabs[tab];
}
