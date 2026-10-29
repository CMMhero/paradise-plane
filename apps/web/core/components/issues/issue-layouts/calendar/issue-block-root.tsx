/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React, { useEffect, useRef, useState } from "react";
import { combine } from "@atlaskit/pragmatic-drag-and-drop/combine";
import { draggable } from "@atlaskit/pragmatic-drag-and-drop/element/adapter";
import { observer } from "mobx-react";
// plane helpers
import { useOutsideClickDetector } from "@plane/hooks";
// components
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useAturanTugas } from "@/hooks/use-aturan-tugas";
import type { TRenderQuickActions } from "../list/list-view-types";
import { HIGHLIGHT_CLASS } from "../utils";
import { CalendarIssueBlock } from "./issue-block";
// types

type Props = {
  issueId: string;
  quickActions: TRenderQuickActions;
  isDragDisabled: boolean;
  isEpic?: boolean;
  canEditProperties: (projectId: string | undefined) => boolean;
};

export const CalendarIssueBlockRoot = observer(function CalendarIssueBlockRoot(props: Props) {
  const { issueId, quickActions, isDragDisabled, isEpic = false, canEditProperties } = props;

  const issueRef = useRef<HTMLAnchorElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const {
    issue: { getIssueById },
  } = useIssueDetail();

  const issue = getIssueById(issueId);
  // Kustomisasi Paradise: menjatuhkan kartu di tanggal lain = menggeser tenggat,
  // jadi hanya pembuat tugas atau Super Admin yang boleh menyeretnya. Server
  // menegakkannya; tanpa ini seretannya selalu berakhir 403.
  const { bisaGantiTenggat } = useAturanTugas();

  const canDrag =
    !isDragDisabled && canEditProperties(issue?.project_id ?? undefined) && bisaGantiTenggat(issue ?? undefined);

  useEffect(() => {
    const element = issueRef.current;

    if (!element) return;

    return combine(
      draggable({
        element,
        canDrag: () => canDrag,
        getInitialData: () => ({ id: issue?.id, date: issue?.target_date }),
        onDragStart: () => {
          setIsDragging(true);
        },
        onDrop: () => {
          setIsDragging(false);
        },
      })
    );
  }, [issueRef?.current, issue, canDrag]);

  useOutsideClickDetector(issueRef, () => {
    issueRef?.current?.classList?.remove(HIGHLIGHT_CLASS);
  });

  if (!issue) return null;

  return (
    <CalendarIssueBlock
      isDragging={isDragging}
      issue={issue}
      quickActions={quickActions}
      ref={issueRef}
      isEpic={isEpic}
    />
  );
});
