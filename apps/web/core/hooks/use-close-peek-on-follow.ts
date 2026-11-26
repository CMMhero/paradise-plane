/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: mengikuti rujukan dari dalam peek
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback } from "react";
import type { MouseEvent } from "react";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";

/**
 * `onClick` for a link that leaves the current page, such as a work item or
 * channel mention. The peek lives in the store, so without this it stays open on
 * top of the page the link just opened. A click that opens a new tab keeps it.
 */
export const useClosePeekOnFollow = () => {
  const { setPeekIssue } = useIssueDetail();
  return useCallback(
    (event: MouseEvent) => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      setPeekIssue(undefined);
    },
    [setPeekIssue]
  );
};
