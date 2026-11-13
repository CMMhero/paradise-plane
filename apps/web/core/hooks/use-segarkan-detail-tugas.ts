/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: detail tugas ikut hidup
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { JENIS_TUGAS, kolomIsianAktif } from "@/lib/data-live";
import { useIssueDetail } from "./store/use-issue-detail";
import { useDaftarPenyegar } from "./use-daftar-penyegar";

/**
 * Detail/peek tugas menarik ulang tugasnya, aktivitas, komentar, sub-tugas,
 * tautan, lampiran, dan relasi saat tugas ini berubah. Semuanya senyap: tanpa
 * kerangka pemuat.
 *
 * Saat orang sedang mengetik di kolom isian, tugasnya sendiri TIDAK ditarik
 * (deskripsi yang sedang disunting tidak boleh ditimpa); aktivitas dan komentar
 * baru tetap masuk karena tidak menyentuh isian itu.
 */
export function useSegarkanDetailTugas(
  workspaceSlug: string | undefined,
  projectId: string | undefined,
  issueId: string | undefined
) {
  const {
    issue: { fetchIssue },
    fetchActivities,
    fetchComments,
    subIssues,
    link,
    attachment,
    relation,
  } = useIssueDetail();
  const siap = !!workspaceSlug && !!projectId && !!issueId;

  useDaftarPenyegar({
    jenis: [JENIS_TUGAS],
    proyek: projectId,
    tugas: issueId,
    aktif: siap,
    tarik: async () => {
      if (!workspaceSlug || !projectId || !issueId) return;
      const kerja: Promise<unknown>[] = [
        fetchActivities(workspaceSlug, projectId, issueId, "mutate"),
        fetchComments(workspaceSlug, projectId, issueId, "mutate"),
        subIssues.fetchSubIssues(workspaceSlug, projectId, issueId),
        link.fetchLinks(workspaceSlug, projectId, issueId),
        attachment.fetchAttachments(workspaceSlug, projectId, issueId),
        relation.fetchRelations(workspaceSlug, projectId, issueId),
      ];
      if (!kolomIsianAktif()) kerja.push(fetchIssue(workspaceSlug, projectId, issueId));
      // Satu penarik yang gagal tidak menggagalkan yang lain.
      await Promise.allSettled(kerja);
    },
  });
}
