/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: cermin web aturan area A (apa yang dilihat tiap jenjang)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Cermin apps/api/plane/utils/aturan/area_visibilitas.py.
 */

import { pilihanWeb } from "./jenis";

export const DIRECTOR_SIDEBAR_HIDES_CHOICES = ["none", "archives", "archives_your_work"] as const;
export type TDirectorSidebarHides = (typeof DIRECTOR_SIDEBAR_HIDES_CHOICES)[number];

/** Kunci menu sidebar yang disembunyikan dari Direktur untuk setiap pilihan. */
export const DIRECTOR_SIDEBAR_HIDDEN_KEYS: Record<TDirectorSidebarHides, readonly string[]> = {
  none: [],
  archives: ["archives"],
  archives_your_work: ["archives", "your_work"],
};

export const ATURAN_WEB_VISIBILITAS = {
  DIRECTOR_SIDEBAR_HIDES: pilihanWeb(DIRECTOR_SIDEBAR_HIDES_CHOICES, "archives"),
};
