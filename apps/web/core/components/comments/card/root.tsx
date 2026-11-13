/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import { useRef, useState } from "react";
import { observer } from "mobx-react";
// plane imports
import type { EditorRefApi } from "@plane/editor";
import type { TIssueComment, TCommentsOperations } from "@plane/types";
// plane web imports
import { CommentBlock, CommentCardDisplay } from "@/plane-web/components/comments";
// local imports
import { CommentQuickActions } from "../quick-actions";
import { CommentReplyButton } from "./reply-button";

type TCommentCard = {
  workspaceSlug: string;
  entityId: string;
  comment: TIssueComment | undefined;
  activityOperations: TCommentsOperations;
  ends: "top" | "bottom" | undefined;
  showAccessSpecifier: boolean;
  showCopyLinkOption: boolean;
  enableReplies: boolean;
  disabled?: boolean;
  projectId?: string;
  /** Rendered as a reply inside a thread: a compact inset box instead of a timeline entry. */
  isReply?: boolean;
  /** Shows the Reply button; the thread owner decides what replying to this comment means. */
  onReply?: () => void;
  /** Rendered inside the card under the comment, e.g. its replies. */
  children?: ReactNode;
};

export const CommentCard = observer(function CommentCard(props: TCommentCard) {
  const {
    workspaceSlug,
    entityId,
    comment,
    activityOperations,
    ends,
    showAccessSpecifier,
    showCopyLinkOption,
    disabled = false,
    projectId,
    isReply = false,
    onReply,
    children,
  } = props;
  // states
  const [isEditing, setIsEditing] = useState(false);
  // refs
  const readOnlyEditorRef = useRef<EditorRefApi>(null);
  // derived values
  const workspaceId = comment?.workspace;

  if (!comment || !workspaceId) return null;

  const display = (
    <CommentCardDisplay
      activityOperations={activityOperations}
      entityId={entityId}
      comment={comment}
      disabled={disabled}
      projectId={projectId}
      readOnlyEditorRef={readOnlyEditorRef}
      showAccessSpecifier={showAccessSpecifier}
      workspaceId={workspaceId}
      workspaceSlug={workspaceSlug}
      isEditing={isEditing}
      setIsEditing={setIsEditing}
      renderQuickActions={() => (
        <>
          {onReply && <CommentReplyButton onClick={onReply} />}
          <CommentQuickActions
            activityOperations={activityOperations}
            comment={comment}
            setEditMode={() => setIsEditing(true)}
            showAccessSpecifier={showAccessSpecifier}
            showCopyLinkOption={showCopyLinkOption}
          />
        </>
      )}
    />
  );

  if (isReply) {
    return (
      <div className="rounded-md border border-subtle bg-surface-1 p-2.5 text-body-sm-regular">
        {display}
        {children}
      </div>
    );
  }

  return (
    <CommentBlock comment={comment} ends={ends}>
      {display}
      {children}
    </CommentBlock>
  );
});
