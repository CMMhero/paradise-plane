/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React, { useMemo } from "react";
import { observer } from "mobx-react";
import { Disclosure, Transition } from "@headlessui/react";
// plane imports
import {
  PARADISE_TOP_NAV_KEYS,
  WORKSPACE_SIDEBAR_DYNAMIC_NAVIGATION_ITEMS_LINKS,
  WORKSPACE_SIDEBAR_STATIC_NAVIGATION_ITEMS,
  WORKSPACE_SIDEBAR_STATIC_NAVIGATION_ITEMS_LINKS,
} from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { ChevronRightIcon } from "@plane/propel/icons";
import { cn } from "@plane/utils";
// store hooks
import useLocalStorage from "@/hooks/use-local-storage";
import {
  usePersonalNavigationPreferences,
  useWorkspaceNavigationPreferences,
} from "@/hooks/use-navigation-preferences";
// plane-web imports
import { SidebarItem } from "@/plane-web/components/workspace/sidebar/sidebar-item";

// Chat dan Pengumuman sudah ada di grup atas, bukan di grup Workspace.
const WORKSPACE_GROUP_ITEMS = WORKSPACE_SIDEBAR_DYNAMIC_NAVIGATION_ITEMS_LINKS.filter(
  (item) => !PARADISE_TOP_NAV_KEYS.includes(item.key)
);

export const SidebarMenuItems = observer(function SidebarMenuItems() {
  // routers
  const { setValue: toggleWorkspaceMenu, storedValue: isWorkspaceMenuOpen } = useLocalStorage<boolean>(
    "is_workspace_menu_open",
    true
  );

  // hooks
  const { preferences: personalPreferences } = usePersonalNavigationPreferences();
  const { preferences: workspacePreferences } = useWorkspaceNavigationPreferences();
  // translation
  const { t } = useTranslation();

  const toggleListDisclosure = (isOpen: boolean) => {
    toggleWorkspaceMenu(isOpen);
  };

  // Filter static navigation items based on personal preferences
  const filteredStaticNavigationItems = useMemo(() => {
    const items = [...WORKSPACE_SIDEBAR_STATIC_NAVIGATION_ITEMS_LINKS];
    const personalItems: Array<(typeof items)[0] & { sort_order: number }> = [];

    // Add personal items based on preferences with their sort_order
    const stickiesItem = WORKSPACE_SIDEBAR_STATIC_NAVIGATION_ITEMS["stickies"];
    if (personalPreferences.items.stickies?.enabled && stickiesItem) {
      personalItems.push({
        ...stickiesItem,
        sort_order: personalPreferences.items.stickies.sort_order,
      });
    }
    if (personalPreferences.items.your_work?.enabled && WORKSPACE_SIDEBAR_STATIC_NAVIGATION_ITEMS["your-work"]) {
      personalItems.push({
        ...WORKSPACE_SIDEBAR_STATIC_NAVIGATION_ITEMS["your-work"],
        sort_order: personalPreferences.items.your_work.sort_order,
      });
    }
    if (personalPreferences.items.drafts?.enabled && WORKSPACE_SIDEBAR_STATIC_NAVIGATION_ITEMS["drafts"]) {
      personalItems.push({
        ...WORKSPACE_SIDEBAR_STATIC_NAVIGATION_ITEMS["drafts"],
        sort_order: personalPreferences.items.drafts.sort_order,
      });
    }
    if (personalPreferences.items.quick_links?.enabled && WORKSPACE_SIDEBAR_STATIC_NAVIGATION_ITEMS["quick_links"]) {
      personalItems.push({
        ...WORKSPACE_SIDEBAR_STATIC_NAVIGATION_ITEMS["quick_links"],
        sort_order: personalPreferences.items.quick_links.sort_order,
      });
    }

    // Sort personal items by sort_order
    personalItems.sort((a, b) => a.sort_order - b.sort_order);

    // Chat dan Pengumuman ikut grup atas (Home, Drafts, ...), di atas grup Workspace.
    const topItems = WORKSPACE_SIDEBAR_DYNAMIC_NAVIGATION_ITEMS_LINKS.filter((item) =>
      PARADISE_TOP_NAV_KEYS.includes(item.key)
    );

    // Merge static items with sorted personal items
    return [...items, ...personalItems, ...topItems];
  }, [personalPreferences]);

  const sortedNavigationItems = useMemo(
    () =>
      // Peringatan LAMA soal efisiensi, bukan dari perubahan ini. Gerbang oxlint memakai --deny-warnings
      // pada berkas yang di-stage, jadi utang lama ikut menghalangi commit.
      // oxlint-disable-next-line no-map-spread
      WORKSPACE_GROUP_ITEMS.map((item) => {
        const preference = workspacePreferences.items[item.key];
        return {
          ...item,
          sort_order: preference ? preference.sort_order : 0,
        };
        // oxlint-disable-next-line unicorn/no-array-sort -- apps/web lib is ES2022 (no toSorted); map result is a fresh array
      }).sort((a, b) => a.sort_order - b.sort_order),
    [workspacePreferences]
  );

  return (
    <>
      <div className="flex flex-col gap-0.5">
        {filteredStaticNavigationItems.map((item, _index) => (
          // Peringatan LAMA, bukan dari perubahan ini. Memakai indeks sebagai key memang rapuh saat daftarnya diurut ulang, tapi memperbaikinya berarti mengubah logika upstream yang bukan urusan perbaikan aria-label ini. Gerbang oxlint memakai --deny-warnings
          // pada berkas yang di-stage, jadi utang lama ikut menghalangi commit.
          // oxlint-disable-next-line react/no-array-index-key
          <SidebarItem key={`static_${_index}`} item={item} />
        ))}
      </div>
      <Disclosure as="div" className="flex flex-col" defaultOpen={!!isWorkspaceMenuOpen}>
        <div className="group flex w-full items-center justify-between rounded-sm px-2 py-1.5 text-placeholder hover:bg-layer-transparent-hover">
          <Disclosure.Button
            as="button"
            type="button"
            className="flex w-full items-center gap-1 text-left text-13 font-semibold whitespace-nowrap text-placeholder"
            onClick={() => toggleListDisclosure(!isWorkspaceMenuOpen)}
          >
            {/* TANPA aria-label, dan itu disengaja. Tombol ini sudah punya teks
                terlihat "Workspace", sementara aria-label MENIMPA teks itu bagi
                pembaca layar. Label lamanya menunjuk kunci terjemahan yang tidak
                ada di locale mana pun, jadi yang dibacakan pembaca layar adalah
                nama kunci mentah, bukan nama tombolnya. Keadaan buka/tutup sudah
                disampaikan `aria-expanded` yang dipasang Headless UI sendiri. */}
            <span className="text-13 font-semibold">{t("common.workspace")}</span>
          </Disclosure.Button>
          <div className="pointer-events-none flex items-center opacity-0 group-hover:pointer-events-auto group-hover:opacity-100">
            <Disclosure.Button
              as="button"
              type="button"
              className="flex-shrink-0 rounded-sm p-0.5 hover:bg-layer-1"
              onClick={() => toggleListDisclosure(!isWorkspaceMenuOpen)}
              /* Hanya berisi ikon, jadi ia memang butuh nama. Memakai kunci
                 yang SUDAH ADA di locale; buka/tutup disampaikan aria-expanded. */
              aria-label={t("common.workspace")}
            >
              <ChevronRightIcon
                className={cn("size-3 flex-shrink-0 transition-all", {
                  "rotate-90": isWorkspaceMenuOpen,
                })}
              />
            </Disclosure.Button>
          </div>
        </div>
        <Transition
          show={!!isWorkspaceMenuOpen}
          enter="transition duration-100 ease-out"
          enterFrom="transform scale-95 opacity-0"
          enterTo="transform scale-100 opacity-100"
          leave="transition duration-75 ease-out"
          leaveFrom="transform scale-100 opacity-100"
          leaveTo="transform scale-95 opacity-0"
        >
          {isWorkspaceMenuOpen && (
            <Disclosure.Panel as="div" className="flex flex-col gap-0.5" static>
              <>
                {/* Item "Departments" (projects) tidak lagi di grup ini: daftar departemen di bawahnya sudah memuatnya. */}
                {sortedNavigationItems.map((item, _index) => (
                  // Peringatan LAMA, bukan dari perubahan ini. Memakai indeks sebagai key memang rapuh saat daftarnya diurut ulang, tapi memperbaikinya berarti mengubah logika upstream yang bukan urusan perbaikan aria-label ini. Gerbang oxlint memakai --deny-warnings
                  // pada berkas yang di-stage, jadi utang lama ikut menghalangi commit.
                  // oxlint-disable-next-line react/no-array-index-key
                  <SidebarItem key={`dynamic_${_index}`} item={item} />
                ))}
              </>
            </Disclosure.Panel>
          )}
        </Transition>
      </Disclosure>
    </>
  );
});
