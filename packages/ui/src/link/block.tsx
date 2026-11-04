/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
// plane utils
import { calculateTimeAgo, cn, getIconForLink } from "@plane/utils";
// plane ui
import type { TContextMenuItem } from "../dropdowns/context-menu/root";
import { CustomMenu } from "../dropdowns/custom-menu";

export type TLinkItemBlockProps = {
  title: string;
  url: string;
  createdAt?: Date | string;
  menuItems?: TContextMenuItem[];
  onClick?: () => void;
  /** Paradise KEP-82: site favicon or a manual icon (data URI). Falls back to the link-type icon. */
  iconSrc?: string | null;
  /** Paradise KEP-82: wide page preview (og:image, data URI). Shown above the title; falls back to the icon. */
  imageSrc?: string | null;
  /** Paradise KEP-82: second line shown instead of the "time ago" text (e.g. who a shared link is for). */
  description?: string;
  /** Paradise KEP-82: icon picked by the user (project-style emoji/icon). Wins over `iconSrc`. */
  icon?: React.ReactNode;
};

function LinkMenuItemContent({ item }: { item: TContextMenuItem }) {
  const ItemIcon = item.icon;
  return (
    <>
      {ItemIcon && <ItemIcon className={cn("h-3 w-3", item.iconClassName)} />}
      <div>
        <h5>{item.title}</h5>
        {item.description && (
          <p
            className={cn("whitespace-pre-line text-tertiary", {
              "text-placeholder": item.disabled,
            })}
          >
            {item.description}
          </p>
        )}
      </div>
    </>
  );
}

export function LinkItemBlock(props: TLinkItemBlockProps) {
  // props
  const { title, url, createdAt, menuItems, onClick, iconSrc, imageSrc, description, icon } = props;
  // icons
  const Icon = getIconForLink(url);
  // A favicon that fails to decode falls back to the link-type icon instead of a broken image.
  // Remembers WHICH source failed, so a new icon gets its own chance without an effect.
  const [brokenIconSrc, setBrokenIconSrc] = React.useState<string | null>(null);
  const isIconBroken = Boolean(iconSrc) && brokenIconSrc === iconSrc;
  // Same idea for the preview image: a failed one drops the card back to the icon layout.
  const [brokenImageSrc, setBrokenImageSrc] = React.useState<string | null>(null);
  const showImage = Boolean(imageSrc) && brokenImageSrc !== imageSrc;
  const secondLine = description ?? (createdAt ? calculateTimeAgo(createdAt) : undefined);
  return (
    <div
      // oxlint-disable-next-line jsx-a11y/prefer-tag-over-role -- memuat tombol menu di dalamnya; <button> bersarang tidak valid
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        // Hanya tombol pada kartu itu sendiri; Enter/Spasi di menu di dalamnya tidak boleh ikut membuka tautan.
        if (e.target !== e.currentTarget) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick?.();
        }
      }}
      className="group flex w-full min-w-0 cursor-pointer flex-col overflow-hidden rounded-card border-[0.5px] border-subtle bg-surface-1"
    >
      {showImage && imageSrc && (
        <img
          src={imageSrc}
          alt=""
          width={1200}
          height={628}
          loading="lazy"
          decoding="async"
          className="aspect-[1.91/1] w-full border-b-[0.5px] border-subtle bg-surface-2 object-cover"
          onError={() => setBrokenImageSrc(imageSrc)}
        />
      )}
      <div className="flex min-h-[64px] items-center gap-4 px-4 py-2">
        <div className="grid size-10 flex-shrink-0 place-items-center rounded-sm bg-surface-2 p-2">
          {icon ? (
            icon
          ) : iconSrc && !isIconBroken ? (
            <img
              src={iconSrc}
              alt=""
              width={24}
              height={24}
              className="size-6 object-contain"
              onError={() => setBrokenIconSrc(iconSrc)}
            />
          ) : (
            // oxlint-disable-next-line react/static-components -- ikon dipilih dari URL lewat getIconForLink (referensi stabil per url), bukan komponen baru
            <Icon className="size-6 stroke-2 text-tertiary group-hover:text-primary" />
          )}
        </div>
        <div className="min-w-0 flex-1 truncate">
          <div className="truncate text-13 font-medium">{title}</div>
          {secondLine && <div className="truncate text-11 font-medium text-placeholder">{secondLine}</div>}
        </div>
        {menuItems && (
          // Paradise: dulu `hidden group-hover:block`. Di layar sentuh hover tak
          // pernah terjadi, jadi Edit/Hapus tak terjangkau sama sekali; dan
          // `display:none` juga mengeluarkan tombol menu dari urutan Tab. Dengan
          // opacity tombolnya tetap bisa difokus papan ketik dan muncul saat itu.
          <div className="opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100 sentuh:opacity-100">
            <CustomMenu placement="bottom-end" menuItemsClassName="z-20" closeOnSelect verticalEllipsis>
              {menuItems.map((item) => (
                <CustomMenu.MenuItem
                  key={item.key}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    item.action();
                  }}
                  className={cn("flex w-full items-center gap-2", {
                    "text-placeholder": item.disabled,
                  })}
                  disabled={item.disabled}
                >
                  <LinkMenuItemContent item={item} />
                </CustomMenu.MenuItem>
              ))}
            </CustomMenu>
          </div>
        )}
      </div>
    </div>
  );
}
