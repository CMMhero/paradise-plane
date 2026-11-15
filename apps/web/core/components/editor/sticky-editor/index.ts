/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ComponentPropsWithoutRef } from "react";
import type { EditorRefApi } from "@plane/editor";
import { buatEditorMalas } from "../lazy-editor";
import type { StickyEditor as TStickyEditor } from "./editor";

// Paradise: editor dimuat saat dirender (lihat `lazy-editor.tsx`). Toolbar tidak
// diekspor dari sini karena impornya menarik `@plane/editor` ke bundel awal.
export const StickyEditor = buatEditorMalas<ComponentPropsWithoutRef<typeof TStickyEditor>, EditorRefApi>(
  () => import("./editor").then((m) => m.StickyEditor),
  "StickyEditor"
);
