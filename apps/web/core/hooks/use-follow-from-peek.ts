/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: mengikuti rujukan dari dalam peek
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback } from "react";
import type { MouseEvent } from "react";
import { useNavigate } from "react-router";
// plane imports
import { releaseOverlayEntry } from "@plane/hooks";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";

/**
 * `onClick` for a link that leaves the current page from inside the work item
 * peek, such as a work item or channel mention. The peek lives in the store, so
 * without this it stays open on top of the page the link opens. Outside the
 * peek, or when the click opens a new tab, the link behaves as usual.
 */
export const useFollowFromPeek = () => {
  const navigate = useNavigate();
  const detail = useIssueDetail();
  return useCallback(
    (event: MouseEvent, to: string) => {
      if (!detail.peekIssue) return;
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      const replace = releaseOverlayEntry();
      detail.setPeekIssue(undefined);
      void navigate(to, { replace });
    },
    [detail, navigate]
  );
};
