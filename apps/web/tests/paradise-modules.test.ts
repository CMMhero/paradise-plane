/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: every module guards its menu and its pages
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vite-plus/test";
import { PARADISE_MODULES, PARADISE_NAV_ITEMS, WORKSPACE_SIDEBAR_DYNAMIC_NAVIGATION_ITEMS } from "@plane/constants";
import type { TParadiseModule } from "@plane/types";
import { moduleForNavKey, moduleForPath } from "@/lib/paradise-modules";

/**
 * One page per module that the module switch must close. A Record, so adding a
 * module to @plane/types fails type checking here until its page is mapped.
 * null = the module has no page of its own (a feature inside work items).
 */
const PAGE_OF_MODULE: Record<TParadiseModule, string | null> = {
  inbox: "/ws/notifications/",
  your_work: "/ws/profile/abc/",
  stickies: "/ws/stickies/",
  drafts: "/ws/drafts/",
  quick_links: "/ws/quick-links/",
  dashboards: "/ws/kinerja/",
  initiatives: "/ws/initiatives/",
  views: "/ws/workspace-views/",
  analytics: "/ws/kinerja/analitik/",
  chat: "/ws/chat/",
  wiki: "/ws/wiki/",
  archives: "/ws/projects/archives/",
  work_items: "/ws/projects/p1/issues/",
  modules: "/ws/projects/p1/modules/",
  pages: "/ws/projects/p1/pages/",
  intake: "/ws/projects/p1/intake/",
  approvals: "/ws/persetujuan/",
  time_tracking: null,
  estimates: "/ws/settings/projects/p1/estimates/",
};

describe("paradise module gates", () => {
  it.each(Object.keys(PARADISE_MODULES) as TParadiseModule[])("%s closes its page", (module) => {
    const page = PAGE_OF_MODULE[module];
    if (page) expect(moduleForPath(page)).toBe(module);
  });

  it.each(PARADISE_NAV_ITEMS.map((item) => [item.key, item] as const))(
    "menu %s and its page follow the same module",
    (_key, item) => {
      expect(moduleForNavKey(item.key)).toBe(item.module);
      expect(moduleForPath(`/ws${item.href}`)).toBe(item.module);
      expect(WORKSPACE_SIDEBAR_DYNAMIC_NAVIGATION_ITEMS[item.key]?.href).toBe(item.href);
    }
  );
});
