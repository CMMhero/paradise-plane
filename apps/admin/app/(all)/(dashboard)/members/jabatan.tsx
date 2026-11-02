/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: lencana jenjang God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu lencana jenjang untuk Accounts dan Organization, supaya "Supervisor"
 * berwarna sama di kedua halaman. Warna mengikuti jangkauan: makin luas
 * jangkauannya makin kuat warnanya; jenjang kosong merah karena datanya kurang.
 */

import { Badge } from "@plane/propel/badge";
import { TINGKAT_DIREKTUR, TINGKAT_MANAGER, TINGKAT_SUPERVISOR } from "@plane/services";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";

type TVarian = "brand" | "success" | "warning" | "neutral" | "danger";

const varianTingkat = (tingkat: number | null): TVarian => {
  if (tingkat === null) return "danger";
  if (tingkat >= TINGKAT_DIREKTUR) return "brand";
  if (tingkat >= TINGKAT_MANAGER) return "success";
  if (tingkat >= TINGKAT_SUPERVISOR) return "warning";
  return "neutral";
};

export function BadgeJabatan({ tingkat, size = "base" }: { tingkat: number | null; size?: "sm" | "base" }) {
  const { s } = useGodmodeStrings();
  const label =
    tingkat === null
      ? s.members.level_unset
      : tingkat >= TINGKAT_DIREKTUR
        ? s.members.level_director
        : tingkat >= TINGKAT_MANAGER
          ? s.members.level_manager
          : tingkat >= TINGKAT_SUPERVISOR
            ? s.members.level_supervisor
            : s.members.level_staff;
  return (
    <Badge variant={varianTingkat(tingkat)} size={size}>
      {label}
    </Badge>
  );
}
