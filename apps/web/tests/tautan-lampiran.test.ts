/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu berkas untuk lampiran work item
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vite-plus/test";
import { attachmentCardHtml } from "@/components/issues/attachment/tautan-lampiran";

const PATH =
  "/api/assets/v2/workspaces/pt-paradise/projects/02fbed73-1248-41e9-b2e1-26f000222d63" +
  "/issues/21590198-621a-41cd-8b35-ab39a41dce76/attachments/5d475ee9-3ed8-4b45-9e3c-6aa0b5f9f5d7/";

describe("attachmentCardHtml", () => {
  it("renders a card with escaped attributes and the name as text", () => {
    expect(attachmentCardHtml({ url: PATH, name: 'a"<b>.pdf', size: 2048, type: "application/pdf" })).toBe(
      `<file-component src="${PATH}" name="a&quot;&lt;b&gt;.pdf" size="2048" type="application/pdf">` +
        "a&quot;&lt;b&gt;.pdf</file-component>"
    );
  });

  it("leaves out what is unknown", () => {
    expect(attachmentCardHtml({ url: PATH, name: "x.zip", size: null, type: null })).toBe(
      `<file-component src="${PATH}" name="x.zip">x.zip</file-component>`
    );
  });
});
