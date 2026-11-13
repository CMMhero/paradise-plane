/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Reply } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";

type TCommentReplyButton = {
  onClick: () => void;
};

export function CommentReplyButton({ onClick }: TCommentReplyButton) {
  const { t } = useTranslation();
  return (
    <Button variant="ghost" size="sm" onClick={onClick} prependIcon={<Reply className="size-3.5" />}>
      {t("issue.comments.replies.action")}
    </Button>
  );
}
