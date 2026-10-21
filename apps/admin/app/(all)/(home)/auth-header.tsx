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
      <Link href="/">
        <PlaneLockup height={20} width={95} className="text-primary" />
      </Link>
    </div>
  );
}
