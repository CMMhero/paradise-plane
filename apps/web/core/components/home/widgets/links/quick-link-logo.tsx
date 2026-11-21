/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Paradise KEP-82: the icon, emoji or image picked for a quick link, sized for the link card.
import { Logo } from "@plane/propel/emoji-icon-picker";
import type { TQuickLinkLogoProps, TQuickLinkMetadata } from "@plane/types";
import { getQuickLinkCardLogo, getQuickLinkTitle } from "./quick-link-display";

type TQuickLinkLogoViewProps = { logo: TQuickLinkLogoProps; size: number; alt: string };

/** Emoji and icons go through the shared Logo. An image is the stored data URI, never the typed address. */
export function QuickLinkLogoView({ logo, size, alt }: TQuickLinkLogoViewProps) {
  if (logo.in_use !== "image") return <Logo logo={logo} size={size} />;
  const src = logo.image?.data;
  if (!src?.startsWith("data:image/")) return null;
  return (
    <img
      src={src}
      alt={alt}
      width={size}
      height={size}
      referrerPolicy="no-referrer"
      className="flex-shrink-0 object-contain"
      style={{ height: size, width: size }}
    />
  );
}

/** Picked icon, else undefined so the card shows the favicon, else the fallback icon. */
export const renderLogo = (link: { url: string; title?: string | null; metadata?: TQuickLinkMetadata | null }) => {
  const logo = getQuickLinkCardLogo(link);
  return logo ? <QuickLinkLogoView logo={logo} size={22} alt={getQuickLinkTitle(link)} /> : undefined;
};
