/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: sebutan dan rujukan di dalam Markdown
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Plugin remark yang menjalankan `potongRujukan` (sebut.ts) dan `potongTautan`
 * (tautan.ts) di potongan TEKS pohon Markdown, bukan di teks mentah. Karena itu
 * sebutan tetap jalan di dalam daftar atau huruf tebal, dan tidak pernah di dalam
 * kode (kode tidak punya anak teks). Tautan Markdown yang menunjuk profil, kanal,
 * atau work item yang tercatat jadi pil yang sama.
 *
 * Tanpa impor beralias, supaya bisa dites tanpa React.
 */

import type { Link, Nodes, Parents, Root, RootContent } from "mdast";
import type { Plugin } from "unified";
import { idProfil } from "../../../../../core/lib/markdown/pesan";
import { potongRujukan } from "./sebut";
import type { TPotonganRujukan, TSumberRujukan } from "./sebut";
import { potongTautan } from "./tautan";

export type TPil = Exclude<TPotonganRujukan, { jenis: "teks" }>;

/** `span` berpenanda; perendernya mencari `data-rujukan` (isi-markdown.tsx). */
const pil = (potongan: TPil): RootContent =>
  ({
    type: "rujukan",
    data: {
      hName: "span",
      hProperties: { dataRujukan: potongan.jenis, dataId: "id" in potongan ? potongan.id : "" },
      hChildren: [{ type: "text", value: potongan.isi }],
    },
  }) as unknown as RootContent;

const teksSimpul = (simpul: Nodes): string =>
  "value" in simpul ? simpul.value : "children" in simpul ? (simpul.children as Nodes[]).map(teksSimpul).join("") : "";

const pilDariTautan = (tautan: Link, sumber: TSumberRujukan): TPil | undefined => {
  const orang = idProfil(tautan.url);
  if (orang && (!sumber.asal || tautan.url.startsWith(`${sumber.asal}/`))) {
    const nama = teksSimpul(tautan);
    return { jenis: "sebut", id: orang, isi: nama.startsWith("@") ? nama : `@${nama}` };
  }
  const kanal = sumber.kanal?.find((k) => tautan.url.endsWith(`/chat/?ruang=${k.id}`));
  if (kanal) return { jenis: "kanal", id: kanal.id, isi: `#${kanal.nama}` };
  const tugas = sumber.tugas?.find((w) => tautan.url.endsWith(`/browse/${w.nomor}/`));
  return tugas ? { jenis: "tugas", id: tugas.id, isi: `#${tugas.nomor}` } : undefined;
};

/** Alamat telanjang yang luput dari GFM (mis. menempel di kata sebelumnya). */
const denganTautan = (teks: string): RootContent[] => {
  const hasil: RootContent[] = [];
  for (const p of potongTautan(teks)) {
    if (p.jenis === "teks") {
      hasil.push({ type: "text", value: p.isi });
      continue;
    }
    hasil.push({ type: "link", url: p.alamat, children: [{ type: "text", value: p.alamat }] });
    if (p.ekor) hasil.push({ type: "text", value: p.ekor });
  }
  return hasil;
};

const telusuri = (induk: Parents, sumber: TSumberRujukan) => {
  induk.children = (induk.children as RootContent[]).flatMap((anak): RootContent[] => {
    if (anak.type === "link") {
      const hasil = pilDariTautan(anak, sumber);
      return [hasil ? pil(hasil) : anak];
    }
    if (anak.type === "text")
      return potongRujukan(anak.value, sumber).flatMap((p) => (p.jenis === "teks" ? denganTautan(p.isi) : [pil(p)]));
    if ("children" in anak) telusuri(anak, sumber);
    return [anak];
  }) as Parents["children"];
};

export const remarkRujukan: Plugin<[TSumberRujukan?], Root> =
  (sumber = {}) =>
  (pohon) =>
    telusuri(pohon, sumber);
