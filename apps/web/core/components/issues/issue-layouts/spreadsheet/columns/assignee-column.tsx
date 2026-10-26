/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// types
import type { TIssue } from "@plane/types";
// components
import { MemberDropdown } from "@/components/dropdowns/member/dropdown";
// hooks
import { useBisaDitugaskan, useOpsiAssignee } from "@/hooks/use-aturan-tugas";

type Props = {
  issue: TIssue;
  onClose: () => void;
  onChange: (issue: TIssue, data: Partial<TIssue>, updates: any) => void;
  disabled: boolean;
};

export const SpreadsheetAssigneeColumn = observer(function SpreadsheetAssigneeColumn(props: Props) {
  const { issue, onChange, disabled, onClose } = props;
  const { workspaceSlug } = useParams();
  // Daftar dari server (diri+bawahan/semua): atasan melihat bawahannya di
  // divisi ini. `undefined` saat memuat = fallback anggota-project (dropdown
  // tetap bisa dibuka, server yang menolak).
  const daftarBoleh = useBisaDitugaskan(workspaceSlug?.toString(), issue?.project_id);
  const diriSendiri = !daftarBoleh.memuat && daftarBoleh.mode === "diri-sendiri";
  // Union dengan assignee yang sudah ada; staf hanya boleh menambah rekan.
  const opsi = useOpsiAssignee(workspaceSlug?.toString(), issue?.project_id, issue?.assignee_ids);
  return (
    <div className="h-11 border-b-[0.5px] border-subtle">
      <MemberDropdown
        value={issue?.assignee_ids ?? []}
        onChange={(data) => {
          onChange(
            issue,
            { assignee_ids: opsi.rapikan(data) },
            {
              changed_property: "assignees",
              change_details: data,
            }
          );
        }}
        projectId={issue?.project_id ?? undefined}
        disabled={disabled}
        memberIds={opsi.memberIds}
        placeholder={diriSendiri ? "Hanya diri sendiri" : "Assignees"}
        multiple
        buttonVariant={
          issue?.assignee_ids && issue.assignee_ids.length > 1 ? "transparent-without-text" : "transparent-with-text"
        }
        buttonClassName="text-left rounded-none group-[.selected-issue-row]:bg-accent-primary/5 group-[.selected-issue-row]:hover:bg-accent-primary/10 px-page-x"
        buttonContainerClassName="w-full"
        optionsClassName="z-[9]"
        onClose={onClose}
      />
    </div>
  );
});
