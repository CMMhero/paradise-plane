/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ComponentPropsWithoutRef } from "react";
import type { EditorRefApi } from "@plane/editor";
import { buatEditorMalas } from "../lazy-editor";
import type { RichTextEditor as TRichTextEditor } from "./editor";

// Paradise: editor dimuat saat dirender (lihat `lazy-editor.tsx`).
export const RichTextEditor = buatEditorMalas<ComponentPropsWithoutRef<typeof TRichTextEditor>, EditorRefApi>(
  () => import("./editor").then((m) => m.RichTextEditor),
  "RichTextEditor"
);
