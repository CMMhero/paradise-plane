/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { IProjectIssuesFilter } from "@/store/issue/project";

/**
 * Yang benar-benar dibutuhkan kalender dari sebuah store filter.
 *
 * Sebelumnya tiap komponen kalender mendaftar union lima store konkret
 * (project, module, cycle, project view), padahal semuanya hanya membaca satu
 * hal: `issueFilters.displayFilters.calendar`. Akibatnya menambah satu store
 * baru berarti menyunting lima berkas, dan store yang kebetulan tidak punya
 * method yang tak pernah dipakai pun ikut ditolak.
 *
 * `Pick` di sini menyatakan kebutuhan sebenarnya, bukan daftar siapa saja yang
 * kebetulan boleh masuk.
 */
export type TCalendarFilterStore = Pick<IProjectIssuesFilter, "issueFilters">;
