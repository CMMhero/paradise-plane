/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: jenis berkas
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vite-plus/test";
import { getFileKind } from "./file-kind";

describe("getFileKind", () => {
  it.each([
    ["laporan.pdf", null, "pdf"],
    ["Surat.DOCX", null, "word"],
    ["anggaran.xlsx", "application/octet-stream", "excel"],
    ["data.csv", "", "excel"],
    ["paparan.pptx", null, "powerpoint"],
    ["foto.jpeg", null, "image"],
    ["logo.svg", "image/svg+xml", "image"],
    ["rekaman.mov", null, "video"],
    ["suara.m4a", null, "audio"],
    ["arsip.7z", null, "archive"],
    ["catatan.md", null, "text"],
    ["config.json", null, "code"],
    ["setup.exe", "application/x-msdownload", "other"],
  ] as const)("%s (%s) is %s", (name, type, kind) => {
    expect(getFileKind({ name, type })).toBe(kind);
  });

  it("falls back to the MIME type when the name has no extension", () => {
    expect(getFileKind({ name: "scan", type: "application/pdf" })).toBe("pdf");
    expect(getFileKind({ name: "clip", type: "video/webm; codecs=vp9" })).toBe("video");
    expect(getFileKind({ name: "README", type: "text/plain" })).toBe("text");
  });

  it("ignores a query string after the extension", () => {
    expect(getFileKind({ name: "/files/report.pdf?download=1" })).toBe("pdf");
  });

  it("is other when nothing is known", () => {
    expect(getFileKind({ name: null, type: null })).toBe("other");
    expect(getFileKind({ name: "berkas", type: "" })).toBe("other");
  });
});
