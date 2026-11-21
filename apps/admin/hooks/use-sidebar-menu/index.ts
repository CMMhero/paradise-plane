/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { MENU_TABS } from "@/components/common/menu-tree";
import type { TMenuId } from "@/components/common/menu-tree";
// local imports
import { coreSidebarMenuLinks } from "./core";
import type { TSidebarMenuItem } from "./types";

/** Sidebar entries in menu-tree order. */
export function useSidebarMenu(): TSidebarMenuItem[] {
  return (Object.keys(MENU_TABS) as TMenuId[]).map((menu) => coreSidebarMenuLinks[menu]);
}
