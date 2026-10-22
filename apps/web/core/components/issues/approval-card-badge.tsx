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
import { useTranslation } from "@plane/i18n";
import { EPillSize, EPillVariant, Pill } from "@plane/propel/pill";
import type { TIssue } from "@plane/types";

export const ApprovalCardBadge = observer(function ApprovalCardBadge({ issue }: { issue: TIssue }) {
  const { t } = useTranslation();
  const status = issue.approval_status ?? null;
  if (status === "menunggu") {
    const label = t("issue.approval.badge.pending");
    return (
      <Pill variant={EPillVariant.WARNING} size={EPillSize.XS} title={label}>
        <Clock className="size-3 shrink-0" aria-hidden />
        {label}
      </Pill>
    );
  }
  if (status === "ditolak") {
    const label = t("issue.approval.badge.rejected");
    return (
      <Pill variant={EPillVariant.ERROR} size={EPillSize.XS} title={label}>
        <XCircle className="size-3 shrink-0" aria-hidden />
        {label}
      </Pill>
    );
  }
  if (status === "disetujui") {
    const label = t("issue.approval.badge.approved");
    return (
      <Pill variant={EPillVariant.SUCCESS} size={EPillSize.XS} title={label}>
        <CheckCircle2 className="size-3 shrink-0" aria-hidden />
        {label}
      </Pill>
    );
  }
  return <></>;
});
