/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { MutableRefObject } from "react";
// components
import type { TIssue, IIssueDisplayProperties, TIssueMap, TGroupedIssues } from "@plane/types";
// hooks
import type { TSelectionHelper } from "@/hooks/use-multiple-select";
// types
import { IssueBlockRoot } from "./block-root";
import type { TRenderQuickActions } from "./list-view-types";

/** Kustomisasi Paradise: baris teratas tiap grup digambar langsung, bukan
 * menunggu IntersectionObserver. Placeholder `RenderIfVisible` setinggi satu
 * baris desktop (44px, atau 300px di HP), sedangkan di layar < md baris asli
 * bertumpuk jadi 120-140px. Pertukaran placeholder -> baris di layar pertama
 * membuat seluruh daftar melompat (layout shift ~0,7 di "Assigned" HP).
 * 10 baris cukup menutup satu layar HP; baris di bawahnya tetap malas. */
const BARIS_LANGSUNG = 10;

interface Props {
  issueIds: TGroupedIssues | any;
  issuesMap: TIssueMap;
  groupId: string;
  canEditProperties: (projectId: string | undefined) => boolean;
  updateIssue: ((projectId: string | null, issueId: string, data: Partial<TIssue>) => Promise<void>) | undefined;
  quickActions: TRenderQuickActions;
  displayProperties: IIssueDisplayProperties | undefined;
  containerRef: MutableRefObject<HTMLDivElement | null>;
  isDragAllowed: boolean;
  canDropOverIssue: boolean;
  selectionHelpers: TSelectionHelper;
  isEpic?: boolean;
}

export function IssueBlocksList(props: Props) {
  const {
    issueIds,
    issuesMap,
    groupId,
    updateIssue,
    quickActions,
    displayProperties,
    canEditProperties,
    containerRef,
    selectionHelpers,
    isDragAllowed,
    canDropOverIssue,
    isEpic = false,
  } = props;

  return (
    <div className="relative h-full w-full">
      {issueIds &&
        issueIds.length > 0 &&
        issueIds.map((issueId: string, index: number) => (
          <IssueBlockRoot
            key={issueId}
            issueId={issueId}
            issuesMap={issuesMap}
            updateIssue={updateIssue}
            quickActions={quickActions}
            canEditProperties={canEditProperties}
            displayProperties={displayProperties}
            nestingLevel={0}
            spacingLeft={0}
            containerRef={containerRef}
            selectionHelpers={selectionHelpers}
            groupId={groupId}
            isLastChild={index === issueIds.length - 1}
            shouldRenderByDefault={index < BARIS_LANGSUNG}
            isDragAllowed={isDragAllowed}
            canDropOverIssue={canDropOverIssue}
            isEpic={isEpic}
          />
        ))}
    </div>
  );
}
