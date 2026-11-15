/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { createContext } from "react";

/** Elemen DOM di samping tombol Collapsible tempat CollapsibleButton memasang `actionItemElement`. */
export const CollapsibleActionsSlot = createContext<HTMLDivElement | null>(null);
