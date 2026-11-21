/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: lampiran gambar work item di galeri
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TImageGalleryEntry } from "@plane/propel/image-gallery";
import type { TIssueAttachment } from "@plane/types";
import { getFileURL } from "@plane/utils";

/** Formats every browser shows in an `<img>`. Attachments carry no MIME type, only a name. */
const IMAGE_EXTENSIONS = new Set(["png", "jpg", "jpeg", "gif", "webp", "avif", "bmp", "svg", "ico"]);

export const isImageFileName = (name: string | undefined): boolean => {
  const extension = name?.split(".").pop()?.toLowerCase();
  return !!extension && extension !== name?.toLowerCase() && IMAGE_EXTENSIONS.has(extension);
};

/**
 * Image attachments for the work item gallery, in list order. Images that
 * came from the description or a comment (KEP-88) are skipped: they are
 * already in the gallery, at their place in the text.
 */
export const attachmentGalleryEntries = (attachments: (TIssueAttachment | undefined)[]): TImageGalleryEntry[] =>
  attachments.flatMap((attachment) => {
    if (!attachment || attachment.sumber === "description" || attachment.sumber === "comment") return [];
    if (!isImageFileName(attachment.attributes?.name)) return [];
    const src = getFileURL(attachment.asset_url ?? "");
    return src ? [{ src, downloadSrc: src, name: attachment.attributes.name }] : [];
  });
