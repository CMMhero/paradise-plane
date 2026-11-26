/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Handle } from "hast-util-to-mdast";
import type { PhrasingContent } from "mdast";

// Simpul mdast sungguhan, bukan teks rakitan: yang dirakit hanya memuat anak
// bertipe teks, jadi tautan, tebal, atau kode di dalam miring/garis bawah hilang.
const emphasis: Handle = (state, node) => {
  const hasil = { type: "emphasis" as const, children: state.all(node) as PhrasingContent[] };
  state.patch(node, hasil);
  return hasil;
};

export const parseMarks: Record<string, Handle> = {
  u: (state, node) => state.all(node),
  i: emphasis,
  em: emphasis,
};
