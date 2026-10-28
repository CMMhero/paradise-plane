/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tombol filter tunggu-persetujuan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tombol toggle kecil di atas papan: "Tunggu persetujuan". Aktif = hanya kartu
 * ber-chip kuning yang tampil. Mati = semua tampil. Keadaan hidup di context
 * lokal per papan (tidak tersimpan di view, tidak ikut URL).
 */

import { observer } from "mobx-react";
import { Check, Clock } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
import { useApprovalFilter } from "./approval-filter-context";

export const ApprovalFilterToggle = observer(function ApprovalFilterToggle() {
  const { t } = useTranslation();
  const { hanyaMenunggu, toggle } = useApprovalFilter();
  const label = t("issue.approval.filter.pending_only");
  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={hanyaMenunggu}
      title={hanyaMenunggu ? t("issue.approval.filter.show_all_title") : t("issue.approval.filter.show_pending_title")}
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium transition-colors",
        hanyaMenunggu
          ? "border-warning-subtle bg-warning-subtle text-warning-primary"
          : "border-subtle bg-layer-1 text-tertiary hover:text-secondary"
      )}
    >
      {hanyaMenunggu ? (
        <Check className="size-3 shrink-0" aria-hidden />
      ) : (
        <Clock className="size-3 shrink-0" aria-hidden />
      )}
      {label}
    </button>
  );
});
