/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: daftar tugas ikut hidup
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useParams } from "next/navigation";
import type { EIssuesStoreType } from "@plane/types";
import { JENIS_TUGAS } from "@/lib/data-live";
import { useDaftarPenyegar } from "./use-daftar-penyegar";
import { useIssuesActions } from "./use-issues-actions";
import { useIssues } from "./store/use-issues";

/**
 * Daftar/papan/spreadsheet/kalender/gantt menarik ulang dirinya saat tugas di
 * project-nya berubah, memakai opsi paginasi yang sedang aktif, tanpa
 * mengosongkan daftar (`tarikSenyap`). Dilewati saat daftar sedang memuat.
 */
export function useSegarkanDaftarTugas(storeType: EIssuesStoreType, viewId?: string) {
  const { projectId } = useParams();
  const { issues } = useIssues(storeType);
  const { fetchIssues } = useIssuesActions(storeType);

  useDaftarPenyegar({
    jenis: [JENIS_TUGAS],
    proyek: projectId?.toString(),
    tarik: async () => {
      // Store draf bukan turunan store dasar dan tidak punya paginasi tugas.
      if (!("tarikSenyap" in issues)) return;
      const opsi = issues.paginationOptions;
      if (!opsi || issues.getIssueLoader()) return;
      await issues.tarikSenyap(() => fetchIssues("loaded", opsi, viewId));
    },
  });
}
