/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo } from "react";
import uniq from "lodash-es/uniq";
import { observer } from "mobx-react";
// plane package imports
import type { TActivityFilters } from "@plane/constants";
import { E_SORT_ORDER, EUserPermissions } from "@plane/constants";
import { useLocalStorage } from "@plane/hooks";
// i18n
import { useTranslation } from "@plane/i18n";
//types
import type { TFileSignedURLResponse, TIssue, TIssueComment } from "@plane/types";
// components
import { CommentCreate } from "@/components/comments/comment-create";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useProject } from "@/hooks/store/use-project";
import { useUser, useUserPermissions } from "@/hooks/store/user";
import { useBolehPercakapanTugas, useTugasSelesai } from "@/hooks/use-aturan-tugas";
import { useAturan } from "@/hooks/use-aturan";
import { useUrutanAktivitas } from "@/hooks/use-urutan-aktivitas";
import { efektifFilterAktivitas, posisiKotakKomentar } from "@/lib/tampilan-bawaan";
// plane web components
import { ActivityFilterRoot } from "@/plane-web/components/issues/worklog/activity/filter-root";
import { IssueActivityWorklogCreateButton } from "@/plane-web/components/issues/worklog/activity/worklog-create-button";
import { IssueActivityCommentRoot } from "./activity-comment-root";
import { useWorkItemCommentOperations } from "./helper";
import { StatusLampiranTempel, useLampiranTempel } from "@/components/issues/attachment/lampiran-tempel";
import { ActivitySortRoot } from "./sort-root";

type TIssueActivity = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled?: boolean;
  isIntakeIssue?: boolean;
  /** Tugas untuk menilai hak komentar kalau belum ada di store detail (intake). */
  issue?: Partial<TIssue>;
};

export type TActivityOperations = {
  createComment: (data: Partial<TIssueComment>) => Promise<TIssueComment>;
  updateComment: (commentId: string, data: Partial<TIssueComment>) => Promise<void>;
  removeComment: (commentId: string) => Promise<void>;
  uploadCommentAsset: (blockId: string, file: File, commentId?: string) => Promise<TFileSignedURLResponse>;
};

export const IssueActivity = observer(function IssueActivity(props: TIssueActivity) {
  const { workspaceSlug, projectId, issueId, disabled = false, isIntakeIssue = false } = props;
  // i18n
  const { t } = useTranslation();
  // hooks
  const { urutan: sortOrder, setUrutan: setSortOrder } = useUrutanAktivitas();
  // Tanpa nilai awal: `storedValue` null = orang ini belum memilih, jadi bawaan dari
  // aturan God Mode yang berlaku (dibaca saat render, bukan disalin ke localStorage).
  const { setValue: setFilterValue, storedValue: storedFilters } = useLocalStorage<TActivityFilters[] | null>(
    "issue_activity_filters",
    null
  );
  const { get: getAturan } = useAturan();
  const selectedFilters = efektifFilterAktivitas(storedFilters, getAturan("ACTIVITY_DEFAULT_FILTERS"));
  const posisiKotak = posisiKotakKomentar(getAturan("COMMENT_BOX_POSITION"), sortOrder);
  // store hooks
  const {
    issue: { getIssueById },
  } = useIssueDetail();

  const { getProjectRoleByWorkspaceSlugAndProjectId } = useUserPermissions();
  const { getProjectById } = useProject();
  const { data: currentUser } = useUser();
  // derived values
  const issue = props.issue ?? (issueId ? getIssueById(issueId) : undefined);
  const currentUserProjectRole = getProjectRoleByWorkspaceSlugAndProjectId(workspaceSlug, projectId);
  const isAdmin = currentUserProjectRole === EUserPermissions.ADMIN;
  const isGuest = currentUserProjectRole === EUserPermissions.GUEST;
  const isAssigned = issue?.assignee_ids && currentUser?.id ? issue?.assignee_ids.includes(currentUser?.id) : false;
  const isWorklogButtonEnabled = !isIntakeIssue && !isGuest && (isAdmin || isAssigned);
  // Komentar, balasan, dan reaksi mengikuti hak ubah (keputusan 2026-11-17).
  // Server tetap penegaknya (`galat_percakapan_tugas`); ini hanya menyembunyikan
  // kontrol yang pasti ditolak.
  const bolehPercakapan = useBolehPercakapanTugas(workspaceSlug, projectId, issue);
  const tugasSelesai = useTugasSelesai()(issue);
  const percakapanTerkunci = disabled || !bolehPercakapan;
  // toggle filter
  const toggleFilter = (filter: TActivityFilters) => {
    let nextFilters: TActivityFilters[] = [];
    if (selectedFilters.includes(filter)) {
      if (selectedFilters.length === 1) return selectedFilters; // Ensure at least one filter is applied
      nextFilters = selectedFilters.filter((f) => f !== filter);
    } else {
      nextFilters = [...selectedFilters, filter];
    }

    setFilterValue(uniq(nextFilters));
  };

  const toggleSortOrder = () => {
    void setSortOrder(sortOrder === E_SORT_ORDER.ASC ? E_SORT_ORDER.DESC : E_SORT_ORDER.ASC);
  };

  // helper hooks
  const activityOperations = useWorkItemCommentOperations(workspaceSlug, projectId, issueId);

  // pasted/dropped files in the comment box become work item attachments
  const { attachFiles, status: statusLampiran } = useLampiranTempel(workspaceSlug, projectId, issueId);

  const project = getProjectById(projectId);
  const renderCommentCreationBox = useMemo(
    () =>
      !bolehPercakapan ? (
        <p className="rounded-md border border-subtle bg-surface-1 px-3 py-2 text-body-sm-regular text-secondary">
          {t(tugasSelesai ? "jenjang_p29.done_locked" : "issue.comments.not_involved")}
        </p>
      ) : (
        <CommentCreate
          workspaceSlug={workspaceSlug}
          entityId={issueId}
          activityOperations={activityOperations}
          showToolbarInitially
          projectId={projectId}
          attachFiles={attachFiles}
          attachmentStatus={<StatusLampiranTempel {...statusLampiran} />}
        />
      ),
    [
      workspaceSlug,
      issueId,
      activityOperations,
      projectId,
      attachFiles,
      statusLampiran,
      bolehPercakapan,
      tugasSelesai,
      t,
    ]
  );
  if (!project) return <></>;

  return (
    <div className="space-y-4">
      {/* header */}
      <div className="flex items-center justify-between">
        <div className="text-h5-medium text-primary">{t("common.activity")}</div>
        <div className="flex items-center gap-2">
          {isWorklogButtonEnabled && (
            <IssueActivityWorklogCreateButton
              workspaceSlug={workspaceSlug}
              projectId={projectId}
              issueId={issueId}
              disabled={disabled}
            />
          )}
          <ActivitySortRoot sortOrder={sortOrder} toggleSort={toggleSortOrder} />
          <ActivityFilterRoot
            selectedFilters={selectedFilters}
            toggleFilter={toggleFilter}
            isIntakeIssue={isIntakeIssue}
            projectId={projectId}
          />
        </div>
      </div>

      {/* rendering activity */}
      <div className="space-y-3">
        <div className="min-h-[200px]">
          <div className="space-y-3">
            {!disabled && posisiKotak === "top" && renderCommentCreationBox}
            <IssueActivityCommentRoot
              projectId={projectId}
              workspaceSlug={workspaceSlug}
              isIntakeIssue={isIntakeIssue}
              issueId={issueId}
              selectedFilters={selectedFilters}
              activityOperations={activityOperations}
              showAccessSpecifier={!!project.anchor}
              disabled={percakapanTerkunci}
              sortOrder={sortOrder}
            />
            {!disabled && posisiKotak === "bottom" && renderCommentCreationBox}
          </div>
        </div>
      </div>
    </div>
  );
});
