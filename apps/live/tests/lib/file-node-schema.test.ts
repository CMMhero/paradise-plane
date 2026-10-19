/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: node berkas non-gambar
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { describe, expect, it } from "vitest";
// plane imports
import { convertHTMLDocumentToAllFormats } from "@plane/editor";

/**
 * Node editor hanya bertahan di server kalau ia terdaftar di
 * CoreEditorExtensionsWithoutProps (packages/editor/.../core-without-props.ts).
 * Kalau tidak, ProseMirror MEMBUANGNYA diam-diam saat Y.Doc dikonversi ke
 * JSON/HTML, tanpa error, tanpa log. Berkas yang diunggah user lenyap dan
 * tidak ada yang tahu sampai ada yang mengeluh.
 *
 * Uji ini menjalankan konversi yang sama dengan yang dipakai server Live.
 */
describe("skema server: node berkas", () => {
  const SRC = "asset-uuid-1234";
  const NAME = "Laporan Bulanan.pdf";
  const SIZE = "204800";
  const inputHTML =
    `<p>sebelum</p>` +
    `<file-component id="file-1" src="${SRC}" name="${NAME}" size="${SIZE}"></file-component>` +
    `<p>sesudah</p>`;

  const result = convertHTMLDocumentToAllFormats({
    document_html: inputHTML,
    variant: "document",
  });
  const json = result.description_json as { content?: { type: string; attrs: Record<string, unknown> }[] };
  const fileNode = json.content?.find((node) => node.type === "fileComponent");

  it("mempertahankan node melewati HTML -> Y.Doc biner -> JSON", () => {
    expect(fileNode).toBeDefined();
  });

  it("mempertahankan atribut yang dibutuhkan kartu berkas", () => {
    // name & size disimpan di node supaya kartu bisa render tanpa memanggil
    // server, dan tetap terbaca kalau aset-nya kelak 404
    expect(fileNode?.attrs.src).toBe(SRC);
    expect(fileNode?.attrs.name).toBe(NAME);
    expect(String(fileNode?.attrs.size)).toBe(SIZE);
  });

  it("me-render node kembali ke HTML tanpa merusak paragraf tetangganya", () => {
    expect(result.description_html).toContain("<file-component");
    expect(result.description_html).toContain(SRC);
    expect(result.description_html).toContain("sebelum");
    expect(result.description_html).toContain("sesudah");
  });

  it("kontrol negatif: node yang TIDAK terdaftar memang dibuang", () => {
    // tanpa ini, uji di atas bisa lolos karena alasan yang salah dan tidak
    // akan pernah bisa gagal
    const control = convertHTMLDocumentToAllFormats({
      document_html: `<p>x</p><bogus-component src="y"></bogus-component>`,
      variant: "document",
    });
    expect(control.description_html).not.toContain("bogus-component");
  });
});
