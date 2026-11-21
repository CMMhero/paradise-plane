/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: cermin web aturan area B (menugaskan, mengubah, menyetujui)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Cermin aturan `web=True` di apps/api/plane/utils/aturan/area_tugas.py. Aturan izin
 * lain di area ini tidak dikirim ke web: hasilnya per orang datang dari
 * `bisa-ditugaskan/` (`bidang_terkunci`, `ubah_semua_tugas`, ...).
 */

import { boolWeb } from "./jenis";

/** Bidang tugas yang bisa dikunci/dibuka God Mode (`PILIHAN_BIDANG` di area_tugas.py). */
export const BIDANG_TUGAS = [
  "name",
  "description",
  "state",
  "priority",
  "start_date",
  "labels",
  "estimate",
  "parent",
] as const;
export type TBidangTugas = (typeof BIDANG_TUGAS)[number];

export const ATURAN_WEB_TUGAS = {
  LOCK_COMPLETED_TASKS: boolWeb(true),
  INTAKE_ADMIN_SETS_DUE_DATE: boolWeb(true),
};
