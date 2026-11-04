/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef } from "react";
import { Link } from "react-router";
import { PinOff } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { ContextMenu } from "@plane/propel/context-menu";
import { SetAsDefaultIcon } from "@plane/propel/icons";
import { TabNavigationItem } from "@plane/propel/tab-navigation";
// local imports
import type { TNavigationItem } from "./tab-navigation-root";
import type { TTabPreferences } from "./tab-navigation-utils";

export type TTabNavigationVisibleItemProps = {
  item: TNavigationItem;
  isActive: boolean;
  tabPreferences: TTabPreferences;
  onToggleDefault: (tabKey: string) => void;
  onHide: (tabKey: string) => void;
  itemRef?: (el: HTMLDivElement | null) => void;
  /** Mode geser (HP): tab aktif digeser masuk ke layar saat aktif. */
  scrollIntoViewWhenActive?: boolean;
};

/**
 * Individual visible tab navigation item with context menu
 * Handles right-click actions for setting default and hiding tabs
 */
export function TabNavigationVisibleItem({
  item,
  isActive,
  tabPreferences,
  onToggleDefault,
  onHide,
  itemRef,
  scrollIntoViewWhenActive = false,
}: TTabNavigationVisibleItemProps) {
  const { t } = useTranslation();
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!scrollIntoViewWhenActive || !isActive) return;
    // Bukan scrollIntoView: itu ikut menggeser SEMUA leluhur yang bisa digulir,
    // termasuk baris header ber-overflow-hidden, sehingga nama project terdorong
    // keluar. Cukup gulir jajaran tabnya sendiri.
    const el = wrapperRef.current;
    const scroller = el?.closest<HTMLElement>("[data-tab-scroller]");
    if (!el || !scroller) return;
    // Posisi dari rect, bukan offsetLeft: offsetParent-nya leluhur header yang
    // jauh lebih luar, jadi offsetLeft melenceng ratusan piksel.
    const posisiTab = el.getBoundingClientRect().left - scroller.getBoundingClientRect().left + scroller.scrollLeft;
    // Tab lebih lebar dari jajarannya: rata kiri supaya awal labelnya terbaca.
    const sisa = scroller.clientWidth - el.offsetWidth;
    scroller.scrollTo({ left: Math.max(0, sisa > 0 ? posisiTab - sisa / 2 : posisiTab) });
  }, [scrollIntoViewWhenActive, isActive]);
  const isDefault = item.key === tabPreferences.defaultTab;

  return (
    <div ref={wrapperRef} className="relative flex h-full shrink-0 items-center transition-all duration-300">
      {isActive && (
        <span className="absolute bottom-0 left-1/2 h-0.5 w-[80%] -translate-x-1/2 rounded-t-md bg-accent-primary transition-all duration-300" />
      )}
      <div key={`${item.key}-measure`} ref={itemRef}>
        <ContextMenu>
          <ContextMenu.Trigger>
            <Link key={`${item.key}-${isActive ? "active" : "inactive"}`} to={item.href}>
              <TabNavigationItem isActive={isActive}>
                <span>{t(item.i18n_key)}</span>
              </TabNavigationItem>
            </Link>
          </ContextMenu.Trigger>
          <ContextMenu.Portal>
            <ContextMenu.Content positionerClassName="z-30">
              <ContextMenu.Item
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleDefault(item.key);
                }}
                className="flex cursor-pointer items-center gap-2 text-secondary transition-colors"
              >
                <SetAsDefaultIcon className="size-3 shrink-0" />
                <span className="text-11">{isDefault ? "Clear default" : "Set as default"}</span>
              </ContextMenu.Item>
              <ContextMenu.Item
                onClick={(e) => {
                  e.stopPropagation();
                  onHide(item.key);
                }}
                className="flex cursor-pointer items-center gap-2 text-secondary transition-colors"
              >
                <PinOff className="size-3 shrink-0" />
                <span className="text-11">Hide in more menu</span>
              </ContextMenu.Item>
            </ContextMenu.Content>
          </ContextMenu.Portal>
        </ContextMenu>
      </div>
    </div>
  );
}
