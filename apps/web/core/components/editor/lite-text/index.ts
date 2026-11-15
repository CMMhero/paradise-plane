/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ComponentPropsWithoutRef } from "react";
import type { EditorRefApi } from "@plane/editor";
import { buatEditorMalas } from "../lazy-editor";
import type { LiteTextEditor as TLiteTextEditor } from "./editor";

// Paradise: editor dimuat saat dirender (lihat `lazy-editor.tsx`). Toolbar tidak
// diekspor dari sini; impornya `TOOLBAR_ITEMS` menarik `@plane/editor` kembali
// ke bundel awal. Ambil langsung dari `./toolbar` bila perlu.
export const LiteTextEditor = buatEditorMalas<ComponentPropsWithoutRef<typeof TLiteTextEditor>, EditorRefApi>(
  () => import("./editor").then((m) => m.LiteTextEditor),
  "LiteTextEditor"
);
