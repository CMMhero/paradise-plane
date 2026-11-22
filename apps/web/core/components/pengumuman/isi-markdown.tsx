/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: isi pengumuman (Markdown)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Pengumuman baru ditulis di penyunting kaya dan disimpan sebagai Markdown di
 * `isi` (teks biasa, jadi Obrolan dan email tetap terbaca). Pengumuman lama
 * adalah teks polos, jadi sebelum dirender: baris tunggal tetap jadi baris
 * baru, dan tautan telanjang jadi tautan.
 */

import ReactMarkdown from "react-markdown";
import { KOMPONEN_MARKDOWN } from "@/components/wiki/pratinjau/teks";

/** Baris tunggal = baris baru (Markdown murni menggabungkannya), tautan telanjang = tautan. Murni. */
export const siapkanMarkdown = (teks: string): string =>
  teks.replace(/([^\n])\n(?=[^\n])/g, "$1  \n").replace(/(^|\s)(https?:\/\/[^\s<>]*[^\s<>.,;:!?)])/g, "$1<$2>");

/**
 * Gambar dibuang dari isi (react-markdown tidak merender HTML mentah, dan
 * alamat gambar bisa dari mana saja). Gambar dan berkas dilampirkan terpisah.
 */
export function IsiMarkdown({ teks }: { teks: string }) {
  return (
    <div className="text-13 leading-relaxed [overflow-wrap:anywhere] text-secondary">
      <ReactMarkdown disallowedElements={["img"]} components={KOMPONEN_MARKDOWN}>
        {siapkanMarkdown(teks)}
      </ReactMarkdown>
    </div>
  );
}
