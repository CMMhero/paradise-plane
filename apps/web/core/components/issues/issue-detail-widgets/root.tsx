/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
// plane imports
import type { TIssueServiceType, TWorkItemWidgets } from "@plane/types";
import { observer } from "mobx-react";
// hooks
import { useTerlibatDiAnak } from "@/hooks/use-aturan-tugas";
// local imports
import { IssueDetailWidgetActionButtons } from "./action-buttons";
import { IssueDetailWidgetCollapsibles } from "./issue-detail-widget-collapsibles";
import { IssueDetailWidgetModals } from "./issue-detail-widget-modals";

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled: boolean;
  /** Tugas diarsipkan: sub-work item ikut terkunci walau saya terlibat di anaknya. */
  isArchived?: boolean;
  renderWidgetModals?: boolean;
  issueServiceType: TIssueServiceType;
  hideWidgets?: TWorkItemWidgets[];
};

export const IssueDetailWidgets = observer(function IssueDetailWidgets(props: Props) {
  const {
    workspaceSlug,
    projectId,
    issueId,
    disabled,
    isArchived = false,
    renderWidgetModals = true,
    issueServiceType,
    hideWidgets,
  } = props;
  // Kustomisasi Paradise: yang sudah mengerjakan salah satu anak boleh menambah
  // sub-work item di induknya, walau induk itu bukan buatan atau tugasnya.
  const terlibatDiAnak = useTerlibatDiAnak(issueId, issueServiceType);
  const subIssueDisabled = isArchived || (disabled && !terlibatDiAnak);

  return (
    <>
      <div className="flex flex-col space-y-4">
        <IssueDetailWidgetActionButtons
          workspaceSlug={workspaceSlug}
          projectId={projectId}
          issueId={issueId}
          disabled={disabled}
          subIssueDisabled={subIssueDisabled}
          issueServiceType={issueServiceType}
          hideWidgets={hideWidgets}
        />
        <IssueDetailWidgetCollapsibles
          workspaceSlug={workspaceSlug}
          projectId={projectId}
          issueId={issueId}
          disabled={disabled}
          subIssueDisabled={subIssueDisabled}
          issueServiceType={issueServiceType}
          hideWidgets={hideWidgets}
        />
      </div>
      {renderWidgetModals && (
        <IssueDetailWidgetModals
          workspaceSlug={workspaceSlug}
          projectId={projectId}
          issueId={issueId}
          issueServiceType={issueServiceType}
          hideWidgets={hideWidgets}
        />
      )}
    </>
  );
});
