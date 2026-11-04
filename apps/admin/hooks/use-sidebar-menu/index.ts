/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// local imports
import { coreSidebarMenuLinks } from "./core";
import type { TSidebarMenuItem } from "./types";

export function useSidebarMenu(): TSidebarMenuItem[] {
  return [
    coreSidebarMenuLinks.general,
    coreSidebarMenuLinks.access,
    coreSidebarMenuLinks.people,
    coreSidebarMenuLinks.rules,
    coreSidebarMenuLinks.notifications,
    coreSidebarMenuLinks.modules,
    coreSidebarMenuLinks.integrations,
    coreSidebarMenuLinks.logs,
  ];
}
