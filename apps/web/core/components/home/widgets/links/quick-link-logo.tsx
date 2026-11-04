/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Paradise KEP-82: the icon or emoji picked for a quick link, sized for the link card.
import { Logo } from "@plane/propel/emoji-icon-picker";
import type { TQuickLinkMetadata } from "@plane/types";
import { getQuickLinkCardLogo } from "./quick-link-display";

/** Picked icon, else undefined so the card shows the favicon, else the fallback icon. */
export const renderLogo = (link: { url: string; metadata?: TQuickLinkMetadata | null }) => {
  const logo = getQuickLinkCardLogo(link);
  return logo ? <Logo logo={logo} size={22} /> : undefined;
};
