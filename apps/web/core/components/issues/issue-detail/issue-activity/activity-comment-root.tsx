/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import type { E_SORT_ORDER, TActivityFilters, EActivityFilterType } from "@plane/constants";
import { BASE_ACTIVITY_FILTER_TYPES, filterActivityOnSelectedFilters } from "@plane/constants";
import type { TCommentsOperations, TIssueComment } from "@plane/types";
// components
import { CommentThreadCard } from "@/components/comments/card/thread";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// plane web components
import { IssueAdditionalPropertiesActivity } from "@/plane-web/components/issues/issue-details/issue-properties-activity";
import { IssueActivityWorklog } from "@/plane-web/components/issues/worklog/activity/root";
// local imports
import { IssueActivityItem } from "./activity/activity-list";
import { IssueActivityLoader } from "./loader";

type TIssueActivityCommentRoot = {
  workspaceSlug: string;
  projectId: string;
  isIntakeIssue: boolean;
  issueId: string;
  selectedFilters: TActivityFilters[];
  activityOperations: TCommentsOperations;
  showAccessSpecifier?: boolean;
  disabled?: boolean;
  sortOrder: E_SORT_ORDER;
};

export const IssueActivityCommentRoot = observer(function IssueActivityCommentRoot(props: TIssueActivityCommentRoot) {
  const {
    workspaceSlug,
    isIntakeIssue,
    issueId,
    selectedFilters,
    activityOperations,
    showAccessSpecifier,
    projectId,
    disabled,
    sortOrder,
  } = props;
  // store hooks
  const {
    activity: { getActivityAndCommentsByIssueId },
    comment: { getCommentById },
  } = useIssueDetail();
  // derived values
  const activityAndComments = getActivityAndCommentsByIssueId(issueId, sortOrder);

  if (!activityAndComments) return <IssueActivityLoader />;

  if (activityAndComments.length <= 0) return null;

  // Replies are drawn inside their thread root, oldest first whatever the sort order, so
  // they leave the main timeline. A reply whose root is not loaded stays on the timeline.
  const repliesByRootId: Record<string, TIssueComment[]> = {};
  const filteredActivityAndComments = filterActivityOnSelectedFilters(activityAndComments, selectedFilters).filter(
    (activityComment) => {
      if (activityComment.activity_type !== "COMMENT") return true;
      const reply = getCommentById(activityComment.id);
      const rootId = reply?.parent;
      if (!reply || !rootId || !getCommentById(rootId)) return true;
      (repliesByRootId[rootId] ??= []).push(reply);
      return false;
    }
  );
  const orderedRepliesByRootId = Object.fromEntries(
    Object.entries(repliesByRootId).map(([rootId, replies]) => [
      rootId,
      // oxlint-disable-next-line unicorn/no-array-sort -- apps/web lib is ES2022 (no toSorted); the copy is a fresh array
      [...replies].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()),
    ])
  );

  return (
    <div>
      {filteredActivityAndComments.map((activityComment, index) => {
        const comment = getCommentById(activityComment.id);
        return activityComment.activity_type === "COMMENT" ? (
          comment ? (
            <CommentThreadCard
              key={activityComment.id}
              workspaceSlug={workspaceSlug}
              entityId={issueId}
              comment={comment}
              replies={orderedRepliesByRootId[comment.id] ?? []}
              activityOperations={activityOperations}
              ends={index === 0 ? "top" : index === filteredActivityAndComments.length - 1 ? "bottom" : undefined}
              showAccessSpecifier={!!showAccessSpecifier}
              showCopyLinkOption={!isIntakeIssue}
              disabled={disabled}
              projectId={projectId}
            />
          ) : null
        ) : BASE_ACTIVITY_FILTER_TYPES.includes(activityComment.activity_type as EActivityFilterType) ? (
          <IssueActivityItem
            key={activityComment.id}
            activityId={activityComment.id}
            ends={index === 0 ? "top" : index === filteredActivityAndComments.length - 1 ? "bottom" : undefined}
          />
        ) : activityComment.activity_type === "ISSUE_ADDITIONAL_PROPERTIES_ACTIVITY" ? (
          <IssueAdditionalPropertiesActivity
            key={activityComment.id}
            activityId={activityComment.id}
            ends={index === 0 ? "top" : index === filteredActivityAndComments.length - 1 ? "bottom" : undefined}
          />
        ) : activityComment.activity_type === "WORKLOG" ? (
          <IssueActivityWorklog
            key={activityComment.id}
            workspaceSlug={workspaceSlug}
            projectId={projectId}
            issueId={issueId}
            activityComment={activityComment}
            ends={index === 0 ? "top" : index === filteredActivityAndComments.length - 1 ? "bottom" : undefined}
          />
        ) : (
          <></>
        );
      })}
    </div>
  );
});
