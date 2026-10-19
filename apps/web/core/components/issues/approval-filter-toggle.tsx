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
import { Clock } from "lucide-react";
import { cn } from "@plane/utils";
import { useApprovalFilter } from "./approval-filter-context";

export const ApprovalFilterToggle = observer(function ApprovalFilterToggle() {
  const { hanyaMenunggu, toggle } = useApprovalFilter();
  return (
    <button
      type="button"
      onClick={toggle}
      title={hanyaMenunggu ? "Tampilkan semua tugas" : "Hanya tampilkan yang menunggu persetujuan"}
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
        hanyaMenunggu
          ? "border-amber-500/50 bg-amber-500/10 text-amber-600"
          : "border-subtle bg-layer-1 text-tertiary hover:text-secondary"
      )}
    >
      <Clock className="size-3 shrink-0" />
      {hanyaMenunggu ? "Tunggu persetujuan ✓" : "Tunggu persetujuan"}
    </button>
  );
});
