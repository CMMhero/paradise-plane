/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: badge status persetujuan di kartu 
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Badge "Menunggu persetujuan" di kartu/list/kanban (KEP-25/26): tugas staf
 * yang belum disetujui HARUS terlihat beda di papan, bukan cuma di sidebar
 * detail. Membaca `approval_status` yang sudah ikut di payload issue — tanpa
 * request tambahan per baris. null = tak pernah butuh persetujuan → tak tampil.
 */

import { observer } from "mobx-react";
import { CheckCircle2, Clock, XCircle } from "lucide-react";
import { EPillSize, EPillVariant, Pill } from "@plane/propel/pill";
import type { TIssue } from "@plane/types";

export const ApprovalCardBadge = observer(function ApprovalCardBadge({ issue }: { issue: TIssue }) {
  const status = issue.approval_status ?? null;
  if (status === "menunggu") {
    return (
      <Pill variant={EPillVariant.WARNING} size={EPillSize.XS}>
        <Clock className="size-3 shrink-0" />
        Menunggu persetujuan
      </Pill>
    );
  }
  if (status === "ditolak") {
    return (
      <Pill variant={EPillVariant.ERROR} size={EPillSize.XS}>
        <XCircle className="size-3 shrink-0" />
        Ditolak — perlu revisi
      </Pill>
    );
  }
  if (status === "disetujui") {
    return (
      <Pill variant={EPillVariant.SUCCESS} size={EPillSize.XS}>
        <CheckCircle2 className="size-3 shrink-0" />
        Disetujui
      </Pill>
    );
  }
  return <></>;
});
