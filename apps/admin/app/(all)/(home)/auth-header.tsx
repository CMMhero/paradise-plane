/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import Link from "next/link";
import { PlaneLockup } from "@plane/propel/icons";

// `PlaneLockup` HANYA namanya yang masih Plane, isinya sudah ditukar dan
// merender logo + teks "Paradise Perkasa" (lihat
// `packages/propel/src/icons/brand/plane-lockup.tsx`). Jadi layar login ini
// TIDAK memasang logo vendor, meski grep atas kata "Plane" menuduhnya begitu.
// Dibiarkan bernama lama karena mengganti namanya menyentuh 8 berkas di tiga app
// tanpa satu piksel pun berubah di layar.
export function AuthHeader() {
  return (
    <div className="sticky top-0 flex w-full flex-shrink-0 items-center justify-between gap-6">
      {/* lg:invisible: the brand panel already shows the logo there; the row keeps its height. */}
      <Link
        href="/"
        aria-label="Space Paradise Perkasa God Mode"
        className="rounded-button focus-visible:ring-2 focus-visible:ring-accent-strong focus-visible:outline-none lg:invisible"
      >
        <PlaneLockup height={20} width={95} className="text-primary" />
      </Link>
    </div>
  );
}
