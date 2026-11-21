/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: lampiran gambar di galeri work item
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vite-plus/test";
import type { TIssueAttachment } from "@plane/types";
import { attachmentGalleryEntries, isImageFileName } from "@/components/common/image-gallery/attachment-items";

const attachment = (name: string, sumber?: TIssueAttachment["sumber"]): TIssueAttachment => ({
  id: name,
  attributes: { name, size: 1 },
  asset_url: `https://files.example/${name}`,
  issue_id: "i1",
  updated_at: "",
  updated_by: "",
  created_by: "",
  sumber,
});

describe("isImageFileName", () => {
  it("knows image extensions in any case", () => {
    expect(isImageFileName("photo.JPG")).toBe(true);
    expect(isImageFileName("diagram.final.png")).toBe(true);
    expect(isImageFileName("scan.webp")).toBe(true);
  });

  it("rejects other files and names without an extension", () => {
    expect(isImageFileName("report.pdf")).toBe(false);
    expect(isImageFileName("png")).toBe(false);
    expect(isImageFileName(undefined)).toBe(false);
  });
});

describe("attachmentGalleryEntries", () => {
  it("keeps uploaded images in list order and skips files that are not images", () => {
    const entries = attachmentGalleryEntries([
      attachment("b.png"),
      attachment("notes.pdf"),
      undefined,
      attachment("a.jpg", "attachment"),
    ]);
    expect(entries.map((e) => e.name)).toEqual(["b.png", "a.jpg"]);
    expect(entries[0]).toMatchObject({
      src: "https://files.example/b.png",
      downloadSrc: "https://files.example/b.png",
    });
  });

  it("skips images taken from the description or a comment, which the gallery already has", () => {
    const entries = attachmentGalleryEntries([attachment("d.png", "description"), attachment("c.png", "comment")]);
    expect(entries).toEqual([]);
  });
});
