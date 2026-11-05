/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: petunjuk @ # di placeholder (KEP-91)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { isEmptyHtmlString } from "@plane/utils";

type TPlaceholder = string | ((isFocused: boolean, value: string) => string);

/** Gabung teks placeholder dengan petunjuk singkat `@`/`#`. */
export const sambungTip = (teks: string, tip: string) => (teks ? `${teks} · ${tip}` : tip);

/**
 * Placeholder editor yang membawa petunjuk `@ mention · # channel or work item`.
 *
 * Petunjuk hanya ikut saat dokumen masih KOSONG. Tanpa syarat itu, ekstensi
 * placeholder Tiptap menampilkannya di tiap baris kosong di tengah deskripsi
 * yang sudah berisi, dan itu cuma jadi gangguan.
 */
export const placeholderDenganTip = (placeholder: TPlaceholder | undefined, tip: string): TPlaceholder | undefined => {
  if (placeholder === undefined) return undefined;
  return (isFocused: boolean, value: string) => {
    const teks = typeof placeholder === "string" ? placeholder : placeholder(isFocused, value);
    return isEmptyHtmlString(value ?? "") ? sambungTip(teks, tip) : teks;
  };
};
