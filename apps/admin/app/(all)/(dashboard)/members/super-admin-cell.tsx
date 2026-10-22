/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: sel Super Admin di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Shield, ShieldCheck } from "lucide-react";
// plane imports
import type { TInstanceMember } from "@plane/services";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";

type Props = {
  member: TInstanceMember;
  sibuk: boolean;
  /** Membuka baris konfirmasi ketik. Memberi Super Admin tidak boleh satu klik. */
  onMintaAngkat: () => void;
  onCabut: () => void;
};

/* Sengaja mencolok. Di antara 90 akun, status ini yang paling berbahaya kalau
   salah, ikon abu-abu 16px membuatnya sama tak terlihatnya dengan kolom
   "terakhir keluar". Warna `warning` dipilih, bukan `accent`: ini bukan status
   netral, ini hak akses ke SELURUH project. */
export function SuperAdminCell({ member, sibuk, onMintaAngkat, onCabut }: Props) {
  const { s } = useGodmodeStrings();
  if (member.is_super_admin) {
    return (
      <button
        type="button"
        disabled={sibuk}
        onClick={onCabut}
        title={s.supercell.revoke_hint}
        className="mx-auto flex items-center gap-1.5 rounded-full bg-warning-subtle px-2.5 py-1 text-11 font-medium text-warning-primary transition-colors hover:bg-danger-subtle hover:text-danger-primary disabled:opacity-50"
      >
        <ShieldCheck className="size-3.5 shrink-0" aria-hidden />
        {s.supercell.label}
      </button>
    );
  }

  return (
    <button
      type="button"
      disabled={sibuk}
      onClick={onMintaAngkat}
      title={s.supercell.grant_hint}
      className="hover:border-warning-primary mx-auto flex items-center gap-1.5 rounded-full border border-subtle px-2.5 py-1 text-11 text-placeholder transition-colors hover:text-warning-primary disabled:opacity-50"
    >
      <Shield className="size-3.5 shrink-0" aria-hidden />
      {s.supercell.grant_label}
    </button>
  );
}
