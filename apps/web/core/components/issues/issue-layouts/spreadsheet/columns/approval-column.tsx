/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kolom status persetujuan di spreadsheet
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Dulu chip persetujuan menumpang di sel judul. Sekarang kolom sendiri yang
 * ikut Display properties (`approval_status`) dan modul Approvals di God Mode.
 * Tanpa status (tugas tak pernah butuh persetujuan) sel menampilkan tanda
 * strip, sama seperti sel kosong lain. Kolom ini hanya-baca: keputusan lewat
 * tombol Setujui/Tolak di chip, yang hanya muncul untuk pemutus.
 */

import { observer } from "mobx-react";
import type { TIssue } from "@plane/types";
import { ApprovalCardBadge } from "@/components/issues/approval-card-badge";

type Props = {
  issue: TIssue;
  onClose: () => void;
  onChange: (issue: TIssue, data: Partial<TIssue>, updates: unknown) => void;
  disabled: boolean;
};

export const SpreadsheetApprovalColumn = observer(function SpreadsheetApprovalColumn({ issue }: Props) {
  return (
    <div className="flex h-11 w-full items-center border-b-[0.5px] border-subtle px-page-x group-[.selected-issue-row]:bg-accent-primary/5">
      {issue.approval_status ? (
        <ApprovalCardBadge issue={issue} />
      ) : (
        <span className="text-13 text-placeholder" aria-hidden>
          -
        </span>
      )}
    </div>
  );
});
