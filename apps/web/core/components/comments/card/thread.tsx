/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: balasan komentar (utas satu tingkat)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { X } from "lucide-react";
import { v4 as uuidv4 } from "uuid";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { IconButton } from "@plane/propel/icon-button";
import type { TCommentsOperations, TIssueComment } from "@plane/types";
// components
import { StatusLampiranTempel, useLampiranTempel } from "@/components/issues/attachment/lampiran-tempel";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useUser } from "@/hooks/store/user";
// local imports
import { CommentCreate } from "../comment-create";
import { CommentCard } from "./root";

/** Threads with more replies than this start folded to the latest few. */
const FOLD_THRESHOLD = 3;
const FOLDED_VISIBLE_COUNT = 2;
const QUOTE_MAX_LENGTH = 140;

type TCommentThreadCard = {
  workspaceSlug: string;
  projectId: string;
  entityId: string;
  /** The thread root: a comment that is not itself a reply. */
  comment: TIssueComment;
  /** Replies of `comment`, oldest first. */
  replies: TIssueComment[];
  activityOperations: TCommentsOperations;
  ends: "top" | "bottom" | undefined;
  showAccessSpecifier: boolean;
  showCopyLinkOption: boolean;
  disabled?: boolean;
};

const getQuote = (comment: TIssueComment): string => {
  const text = (comment.comment_stripped ?? "").replace(/\s+/g, " ").trim();
  return text.length > QUOTE_MAX_LENGTH ? `${text.slice(0, QUOTE_MAX_LENGTH - 1)}…` : text;
};

const buildMentionHtml = (userId: string): string =>
  `<p><mention-component id="${uuidv4()}" entity_name="user_mention" entity_identifier="${userId}"></mention-component> </p>`;

type TReplyComposer = {
  workspaceSlug: string;
  projectId: string;
  entityId: string;
  root: TIssueComment;
  target: TIssueComment;
  activityOperations: TCommentsOperations;
  onClose: () => void;
};

const ReplyComposer = observer(function ReplyComposer(props: TReplyComposer) {
  const { workspaceSlug, projectId, entityId, root, target, activityOperations, onClose } = props;
  const { t } = useTranslation();
  const { getUserDetails } = useMember();
  const { data: currentUser } = useUser();
  const { attachFiles, status } = useLampiranTempel(workspaceSlug, projectId, entityId);
  // derived values
  const targetName = getUserDetails(target.actor)?.display_name ?? target.actor_detail?.display_name ?? "";
  // Replying to a reply attaches to the thread root, so the person is mentioned instead.
  const shouldMention = target.id !== root.id && !target.actor_detail?.is_bot && target.actor !== currentUser?.id;

  return (
    <div
      role="presentation"
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose();
      }}
    >
      <CommentCreate
        workspaceSlug={workspaceSlug}
        entityId={entityId}
        projectId={projectId}
        activityOperations={activityOperations}
        parentId={root.id}
        initialHtml={shouldMention ? buildMentionHtml(target.actor) : undefined}
        focusOnMount
        onSubmitCallback={onClose}
        attachFiles={attachFiles}
        attachmentStatus={<StatusLampiranTempel {...status} />}
        header={
          <div className="mb-1.5 flex items-start gap-2 border-l-2 border-accent-strong bg-surface-1 py-1 pr-1 pl-2">
            <div className="min-w-0 flex-1">
              <div className="text-caption-sm-medium text-secondary">
                {t("issue.comments.replies.replying_to", { name: targetName })}
              </div>
              <div className="truncate text-caption-sm-regular text-tertiary">{getQuote(target)}</div>
            </div>
            <IconButton icon={X} variant="ghost" size="sm" onClick={onClose} aria-label={t("common.cancel")} />
          </div>
        }
      />
    </div>
  );
});

export const CommentThreadCard = observer(function CommentThreadCard(props: TCommentThreadCard) {
  const {
    workspaceSlug,
    projectId,
    entityId,
    comment,
    replies,
    activityOperations,
    ends,
    showAccessSpecifier,
    showCopyLinkOption,
    disabled = false,
  } = props;
  const { t } = useTranslation();
  // states
  const [replyTarget, setReplyTarget] = useState<TIssueComment | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  // A comment that still carries a parent is an orphan (its root is gone): no replying to it.
  const canReply = !disabled && !comment.parent;
  const hashedReplyId = typeof window === "undefined" ? "" : window.location.hash.replace("#comment-", "");
  const hasHashedReply = replies.some((reply) => reply.id === hashedReplyId);
  // derived values
  const isFolded = replies.length > FOLD_THRESHOLD && !isExpanded;
  const visibleReplies = isFolded ? replies.slice(-FOLDED_VISIBLE_COUNT) : replies;
  const hiddenCount = replies.length - visibleReplies.length;
  const canFold = replies.length > FOLD_THRESHOLD;

  // a link to a folded reply must unfold the thread so the scroll can land
  useEffect(() => {
    if (hasHashedReply) setIsExpanded(true);
  }, [hasHashedReply]);

  const showThread = replies.length > 0 || (canReply && replyTarget !== null);

  return (
    <CommentCard
      workspaceSlug={workspaceSlug}
      entityId={entityId}
      comment={comment}
      activityOperations={activityOperations}
      ends={ends}
      showAccessSpecifier={showAccessSpecifier}
      showCopyLinkOption={showCopyLinkOption}
      disabled={disabled}
      projectId={projectId}
      enableReplies
      onReply={canReply ? () => setReplyTarget(comment) : undefined}
    >
      {showThread && (
        <div className="mt-3 flex flex-col gap-2 border-l-2 border-subtle pl-3">
          {canFold && (
            <div>
              <Button variant="ghost" size="sm" onClick={() => setIsExpanded(!isExpanded)}>
                {isFolded
                  ? t("issue.comments.replies.show_earlier", { count: hiddenCount })
                  : t("issue.comments.replies.hide_earlier")}
              </Button>
            </div>
          )}
          {visibleReplies.map((reply) => (
            <CommentCard
              key={reply.id}
              isReply
              workspaceSlug={workspaceSlug}
              entityId={entityId}
              comment={reply}
              activityOperations={activityOperations}
              ends={undefined}
              showAccessSpecifier={showAccessSpecifier}
              showCopyLinkOption={showCopyLinkOption}
              disabled={disabled}
              projectId={projectId}
              enableReplies
              onReply={canReply ? () => setReplyTarget(reply) : undefined}
            />
          ))}
          {canReply && replyTarget && (
            <ReplyComposer
              key={replyTarget.id}
              workspaceSlug={workspaceSlug}
              projectId={projectId}
              entityId={entityId}
              root={comment}
              target={replyTarget}
              activityOperations={activityOperations}
              onClose={() => setReplyTarget(null)}
            />
          )}
        </div>
      )}
    </CommentCard>
  );
});
