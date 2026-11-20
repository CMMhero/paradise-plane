/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: antrean persetujuan satu workspace
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import useSWR from "swr";
// services
import { PersetujuanService } from "@/services/persetujuan.service";
// local imports
import { AWALAN_KUNCI_PERSETUJUAN } from "../approval-actions";

const persetujuanService = new PersetujuanService();

/**
 * Satu kunci untuk halaman Persetujuan dan menu sidebar-nya. Berawalan
 * `AWALAN_KUNCI_PERSETUJUAN`, jadi setiap keputusan (di papan, menu work item,
 * atau halaman ini) ikut menyegarkannya.
 */
export const useAntreanWorkspace = (workspaceSlug: string | undefined) =>
  useSWR(workspaceSlug ? `${AWALAN_KUNCI_PERSETUJUAN}:workspace:${workspaceSlug}` : null, () =>
    persetujuanService.antreanWorkspace(workspaceSlug as string)
  );
