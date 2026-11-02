/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: saklar fitur di sisi store
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { PARADISE_REMOVED, isParadiseGateActive, type TParadiseGate } from "@plane/constants";

type TProjectFeatureFlags = {
  cycle_view?: boolean;
  module_view?: boolean;
  issue_views_view?: boolean;
  page_view?: boolean;
  inbox_view?: boolean;
};

/** Flag fitur per project -> modul God Mode pemiliknya. */
const MODUL_PER_FLAG: Record<keyof TProjectFeatureFlags, TParadiseGate> = {
  // Cycles dicabut (KEP-53): flag-nya selalu false, apa pun yang tersimpan.
  cycle_view: PARADISE_REMOVED,
  module_view: "modules",
  issue_views_view: "views",
  page_view: "pages",
  inbox_view: "intake",
};

/**
 * Flag fitur project (`cycle_view`, `module_view`, dst.) dicek di puluhan tempat:
 * nav, sidebar work item, filter, spreadsheet, Power K, halaman fiturnya. Daripada
 * menambal semuanya, flag milik modul yang dimatikan di God Mode dipaksa `false`
 * di satu pintu: saat project masuk ke `projectMap`. Data di server tidak
 * disentuh, jadi menyalakan ulang modulnya mengembalikan setelan tiap project.
 */
export const withParadiseFeatureGates = <T extends TProjectFeatureFlags>(project: T): T => {
  const dimatikan = (Object.keys(MODUL_PER_FLAG) as (keyof TProjectFeatureFlags)[]).filter(
    (flag) => !isParadiseGateActive(MODUL_PER_FLAG[flag])
  );
  if (dimatikan.length === 0) return project;
  return { ...project, ...Object.fromEntries(dimatikan.map((flag) => [flag, false])) };
};
