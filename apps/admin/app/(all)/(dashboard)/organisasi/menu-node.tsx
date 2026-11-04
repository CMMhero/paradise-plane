/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: menu aksi divisi/departemen (KEP-29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu menu "..." di kepala divisi, kartu departemen papan, dan kotak bagan: ubah, hapus,
 * tambah orang, pindah departemen / ganti project. Isi menu hanya mengirim
 * perintah; modalnya ada di kelola.tsx.
 *
 * Menu DI-PORTAL ke body: kotak bagan ada di dalam isi yang di-transform, dan
 * `position: fixed` milik CustomMenu ikut tergeser kalau tidak di-portal.
 * ATRIBUT_ABAIKAN mencegah klik menu memulai geser kanvas.
 */

import type { ReactNode } from "react";
import { ArrowRightLeft, Pencil, Plus, Trash2, UserPlus } from "lucide-react";
// plane imports
import { CustomMenu } from "@plane/ui";
import { cn } from "@plane/utils";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { ATRIBUT_ABAIKAN } from "./kanvas";
import type { TKelola } from "./util";

type TItem = { kunci: string; label: string; icon: ReactNode; onClick: () => void; bahaya?: boolean };

function MenuAksi({ nama, items, className }: { nama: string; items: TItem[]; className?: string }) {
  const { s, fill } = useGodmodeStrings();
  return (
    <div className={cn("shrink-0", className)} {...{ [ATRIBUT_ABAIKAN]: "" }}>
      <CustomMenu
        ellipsis
        closeOnSelect
        placement="bottom-end"
        ariaLabel={fill(s.org.actions_for, { name: nama })}
        portalElement={typeof document === "undefined" ? undefined : document.body}
      >
        {items.map((it) => (
          <CustomMenu.MenuItem
            key={it.kunci}
            onClick={it.onClick}
            variant={it.bahaya ? "danger" : "default"}
            className="flex items-center gap-2"
          >
            <span className="shrink-0 [&>svg]:size-3.5">{it.icon}</span>
            {it.label}
          </CustomMenu.MenuItem>
        ))}
      </CustomMenu>
    </div>
  );
}

type TMenuProps = { id: string; nama: string; onKelola: TKelola; className?: string };

export function MenuDivisi({ id, nama, onKelola, className }: TMenuProps) {
  const { s } = useGodmodeStrings();
  const items: TItem[] = [
    {
      kunci: "ubah",
      label: s.org.edit_name_code,
      icon: <Pencil />,
      onClick: () => onKelola({ jenis: "ubah-divisi", id }),
    },
    {
      kunci: "dep",
      label: s.org.new_department,
      icon: <Plus />,
      onClick: () => onKelola({ jenis: "buat-departemen", divisiId: id }),
    },
    {
      kunci: "mgr",
      label: s.org.add_manager,
      icon: <UserPlus />,
      onClick: () => onKelola({ jenis: "tambah-manager", id }),
    },
    {
      kunci: "hapus",
      label: s.org.delete,
      icon: <Trash2 />,
      bahaya: true,
      onClick: () => onKelola({ jenis: "hapus-divisi", id }),
    },
  ];
  return <MenuAksi nama={nama} items={items} className={className} />;
}

export function MenuDepartemen({ id, nama, onKelola, className }: TMenuProps) {
  const { s } = useGodmodeStrings();
  const items: TItem[] = [
    {
      kunci: "ubah",
      label: s.org.edit_name_code,
      icon: <Pencil />,
      onClick: () => onKelola({ jenis: "ubah-departemen", id }),
    },
    {
      kunci: "orang",
      label: s.org.add_member,
      icon: <UserPlus />,
      onClick: () => onKelola({ jenis: "tambah-anggota", id }),
    },
    {
      kunci: "setelan",
      label: s.org.move_or_project,
      icon: <ArrowRightLeft />,
      onClick: () => onKelola({ jenis: "setelan-departemen", id }),
    },
    {
      kunci: "hapus",
      label: s.org.delete,
      icon: <Trash2 />,
      bahaya: true,
      onClick: () => onKelola({ jenis: "hapus-departemen", id }),
    },
  ];
  return <MenuAksi nama={nama} items={items} className={className} />;
}
