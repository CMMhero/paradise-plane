/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: ikon jenis berkas
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { cn } from "../utils/classname";
import { getFileKind, getFileKindStyle } from "./file-kind";

export type FileTypeIconProps = {
  name?: string | null;
  /** MIME type, when known. The file name's extension is checked first. */
  type?: string | null;
  size?: "sm" | "md";
  className?: string;
};

/** Coloured tile with an icon for the file's kind (PDF, Word, Excel, video...). Decorative. */
export function FileTypeIcon({ name, type, size = "md", className }: FileTypeIconProps) {
  const { icon: Icon, tone } = getFileKindStyle(getFileKind({ name, type }));
  return (
    <span
      aria-hidden
      className={cn(
        "grid shrink-0 place-items-center rounded-md",
        tone,
        size === "sm" ? "size-7" : "size-9",
        className
      )}
    >
      <Icon className={size === "sm" ? "size-3.5" : "size-4.5"} />
    </span>
  );
}
