/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Paradise KEP-82: what a quick link shows. Manual values win, the site's values
// are the default, and clearing the manual values brings the default back.
import type { TLogoProps, TQuickLinkMetadata } from "@plane/types";

type TQuickLinkLike = {
  title?: string | null;
  url: string;
  metadata?: TQuickLinkMetadata | null;
};

export const getQuickLinkTitle = (link: TQuickLinkLike): string =>
  link.title?.trim() || link.metadata?.title || link.url;

/** Only server-made image data URIs are rendered, never a remote address. */
export const getQuickLinkIcon = (link: TQuickLinkLike): string | null => {
  const icon = link.metadata?.favicon;
  return icon && icon.startsWith("data:image/") ? icon : null;
};

/** Wide page preview (og:image). Server-made data URI only; the card falls back to the icon without it. */
export const getQuickLinkImage = (link: TQuickLinkLike): string | null => {
  const image = link.metadata?.og_image;
  return image && image.startsWith("data:image/") ? image : null;
};

export const hasQuickLinkOverride = (link: TQuickLinkLike): boolean =>
  Boolean(link.title?.trim() || link.metadata?.logo_props);

const usableLogo = (logo: TLogoProps | null | undefined): TLogoProps | null => {
  if (logo?.in_use === "emoji" && logo.emoji?.value) return logo;
  if (logo?.in_use === "icon" && logo.icon?.name) return logo;
  return null;
};

/** Icon or emoji picked from the project icon set. Wins over the favicon. */
export const getQuickLinkLogo = (link: TQuickLinkLike): TLogoProps | null => usableLogo(link.metadata?.logo_props);

/**
 * Logo drawn on the card: the picked one, else nothing while the site has a favicon,
 * else the fallback icon the link was created with (imported portal links).
 */
export const getQuickLinkCardLogo = (link: TQuickLinkLike): TLogoProps | null =>
  getQuickLinkLogo(link) ?? (getQuickLinkIcon(link) ? null : usableLogo(link.metadata?.logo_cadangan));

/** One grid for shared and personal links so both rows of cards have the same width. */
export const QUICK_LINK_GRID_CLASS = "grid grid-cols-[repeat(auto-fill,minmax(min(100%,14.5rem),1fr))] gap-2";
