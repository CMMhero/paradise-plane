/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TSelectionHelper } from "@/hooks/use-multiple-select";

type Props = {
  className?: string;
  selectionHelpers: TSelectionHelper;
};

// Community edition tidak punya operasi massal, dan satu-satunya isi komponen
// ini dulu adalah spanduk "upgrade ke Plane Pro" yang muncul BEGITU user
// menyeleksi beberapa work item, permukaan yang gampang tersentuh dan terlewat
// dari pembersihan merek `a407ce0`.
//
// Sengaja merender NOL, bukan diganti pesan lain: menyeleksi beberapa item lalu
// tidak melihat apa-apa sudah jujur menggambarkan keadaannya. Mengiklankan
// produk yang tidak bisa dibeli kantor ini justru menyesatkan.
//
// Props dipertahankan supaya pemanggil di `core/` tidak perlu diubah, bentuknya
// tetap sama, isinya saja yang kosong. Awalan `_` adalah konvensi oxlint untuk
// parameter yang sengaja tidak dipakai (repo ini oxlint, BUKAN eslint).
export function IssueBulkOperationsRoot(_props: Props) {
  return null;
}
