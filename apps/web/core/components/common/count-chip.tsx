/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

//
import { cn } from "@plane/utils";

type TCountChip = {
  count: string | number;
  /** `subtle`: jumlah biasa (isi grup, daftar). `unread`: belum dibaca, pil merah penuh seperti lencana kotak masuk. */
  variant?: "subtle" | "unread";
  className?: string;
};

// bg-accent-subtle, bukan bg-accent-primary/20: merah di atas merah transparan cuma 3,1:1 (terang) / 3,6:1 (gelap).
// `unread` memakai pasangan tombol utama (bg-accent-primary + text-on-color): 4,8:1 terang, 7,4:1 gelap, dan
// angkanya tidak lagi merah kecil di atas merah tua.
const VARIANT_CLASS: Record<NonNullable<TCountChip["variant"]>, string> = {
  subtle: "bg-accent-subtle text-accent-primary",
  unread: "bg-accent-primary text-on-color",
};

export function CountChip(props: TCountChip) {
  const { count, variant = "subtle", className = "" } = props;

  return (
    <div
      className={cn(
        "relative flex flex-shrink-0 items-center justify-center rounded-xl px-2.5 py-0.5 text-caption-sm-semibold",
        VARIANT_CLASS[variant],
        className
      )}
    >
      {count}
    </div>
  );
}
