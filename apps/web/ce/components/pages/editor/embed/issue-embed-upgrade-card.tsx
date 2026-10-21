/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { cn } from "@plane/utils";
// components
import { ProIcon } from "@/components/common/pro-icon";

export function IssueEmbedUpgradeCard(props: any) {
  return (
    <div
      className={cn(
        "flex w-full items-center justify-between gap-5 rounded-md border-[0.5px] border-subtle bg-layer-1 px-5 py-2 shadow-raised-100 max-md:flex-wrap",
        {
          "border-2": props.selected,
        }
      )}
    >
      {/* Dulu ajakan berlangganan ke plane.so/pro. Tombol upgrade dibuang:
          instalasi internal ini tidak berlangganan tier upstream, jadi tombolnya
          hanya akan membawa karyawan ke halaman jualan yang tidak berlaku. */}
      <div className="flex items-center gap-4">
        <ProIcon className="size-4 flex-shrink-0" />
        <p className="!text-14 text-secondary">Menyematkan work item di halaman belum tersedia.</p>
      </div>
    </div>
  );
}
