/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pemilih orang di Struktur organisasi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tambah orang lewat CustomSearchSelect upstream (cari-ketik), karena calonnya
 * bisa puluhan orang. Baris & panel orang milik panel detail lama ikut dibuang
 * bersama tab "Chart & details" (KEP-86).
 */

import { useState } from "react";
import { UserPlus } from "lucide-react";
// plane imports
import { getButtonStyling } from "@plane/propel/button";
import type { TAnggotaHierarki } from "@plane/services";
import { CustomSearchSelect } from "@plane/ui";
import { cn } from "@plane/utils";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { BadgeJabatan } from "../members/jabatan";

/** Tombol "Tambah orang" yang membuka daftar calon dengan cari-ketik. */
export function PemilihOrang({
  calon,
  keterangan,
  onTambah,
  label,
}: {
  calon: TAnggotaHierarki[];
  /** Teks kecil di kanan nama calon (asal penempatan, jenjang). Tanpa hook: dipanggil di dalam map. */
  keterangan: (o: TAnggotaHierarki) => string;
  onTambah: (o: TAnggotaHierarki) => Promise<void>;
  label: string;
}) {
  const { s } = useGodmodeStrings();
  const [sibuk, setSibuk] = useState(false);
  return (
    <CustomSearchSelect
      value={null}
      disabled={sibuk}
      maxHeight="lg"
      placement="bottom-end"
      noResultsMessage={calon.length === 0 ? s.org.no_candidates : s.members.empty}
      customButtonClassName={cn(getButtonStyling("secondary", "base"), "w-auto")}
      customButton={
        // Gaya tombol dipasang di <button> milik CustomSearchSelect, isinya cuma ikon + label.
        <>
          <UserPlus className="size-3.5" aria-hidden />
          {label}
        </>
      }
      onChange={async (id: string) => {
        const o = calon.find((x) => x.id === id);
        if (!o) return;
        setSibuk(true);
        try {
          await onTambah(o);
        } finally {
          setSibuk(false);
        }
      }}
      options={calon.map((o) => {
        const ket = keterangan(o);
        return {
          value: o.id,
          query: `${o.display_name} ${o.email}`,
          content: (
            <span className="flex w-72 items-center gap-2">
              <span className="min-w-0 flex-1">
                <span className="block truncate text-12 text-primary">{o.display_name}</span>
                <span className="block truncate text-10 text-tertiary">{ket || o.email}</span>
              </span>
              <BadgeJabatan tingkat={o.tingkat} size="sm" />
            </span>
          ),
        };
      })}
    />
  );
}
