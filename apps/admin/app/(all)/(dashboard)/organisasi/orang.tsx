/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: baris & daftar orang di Struktur organisasi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu bentuk baris orang untuk manager, supervisor, staf, dan direktur:
 * avatar + nama + email (PersonCell), lencana jenjang yang sama dengan
 * Accounts, lalu aksi ikon di kanan. Tambah orang lewat CustomSearchSelect
 * upstream (cari-ketik), karena calonnya bisa puluhan orang.
 */

import { useState, type ReactNode } from "react";
import { UserPlus } from "lucide-react";
// plane imports
import { Badge } from "@plane/propel/badge";
import { getButtonStyling } from "@plane/propel/button";
import type { TAnggotaHierarki } from "@plane/services";
import { CustomSearchSelect } from "@plane/ui";
import { cn } from "@plane/utils";
// components
import { IconAction, Panel, PersonCell } from "@/components/common/paradise-ui";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { BadgeJabatan } from "../members/jabatan";

export type TAksiBaris = {
  label: string;
  icon: React.FC<{ className?: string }>;
  onClick: () => Promise<void>;
};

const AKSI_KOSONG: TAksiBaris[] = [];

/** Satu orang dalam daftar organisasi. Aksi berjalan satu per satu (tombol mati selama sibuk). */
export function BarisOrang({
  nama,
  email,
  tingkat,
  badges,
  aksi = AKSI_KOSONG,
}: {
  nama: string;
  email: string;
  tingkat: number | null;
  badges?: ReactNode;
  aksi?: TAksiBaris[];
}) {
  const [sibuk, setSibuk] = useState(false);
  const jalankan = async (fn: () => Promise<void>) => {
    setSibuk(true);
    try {
      await fn();
    } finally {
      setSibuk(false);
    }
  };
  return (
    <li className="flex items-center gap-3 px-4 py-2.5 transition-colors hover:bg-layer-1-hover">
      <div className="min-w-0 flex-1">
        <PersonCell name={nama} email={email} size="sm" badges={badges} />
      </div>
      <BadgeJabatan tingkat={tingkat} />
      {aksi.length > 0 && (
        <div className="flex shrink-0 items-center">
          {aksi.map((a) => (
            <IconAction
              key={a.label}
              label={a.label}
              icon={a.icon}
              disabled={sibuk}
              onClick={() => void jalankan(a.onClick)}
            />
          ))}
        </div>
      )}
    </li>
  );
}

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

/** Panel berisi daftar orang + jumlah + aksi tambah. Kosong = kalimat penjelas, bukan tabel kosong. */
export function PanelOrang({
  judul,
  catatan,
  icon,
  jumlah,
  tambah,
  kosong,
  children,
}: {
  judul: string;
  catatan?: string;
  icon?: ReactNode;
  jumlah: number;
  tambah?: ReactNode;
  kosong: string;
  children: ReactNode;
}) {
  return (
    <Panel
      flush
      icon={icon}
      title={
        <span className="flex items-center gap-2">
          {judul}
          <Badge variant="neutral" size="sm">
            {jumlah}
          </Badge>
        </span>
      }
      description={catatan}
      actions={tambah}
    >
      {jumlah === 0 ? (
        <p className="px-4 py-6 text-center text-12 text-tertiary">{kosong}</p>
      ) : (
        <ul className="divide-y divide-subtle">{children}</ul>
      )}
    </Panel>
  );
}

/** Subjudul kelompok di dalam satu PanelOrang (Supervisor / Staf). */
export function SubjudulKelompok({ children }: { children: ReactNode }) {
  return (
    <li className="bg-layer-2 px-4 py-1 text-10 font-semibold tracking-wide text-tertiary uppercase">{children}</li>
  );
}
