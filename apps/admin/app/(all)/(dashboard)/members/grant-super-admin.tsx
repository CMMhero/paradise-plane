/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: konfirmasi beri Super Admin
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { ShieldAlert } from "lucide-react";
// plane imports
import { Button } from "@plane/propel/button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { InstanceMemberService, type TInstanceMember } from "@plane/services";
// local
import { inputClass } from "./constants";

const memberService = new InstanceMemberService();

type Props = {
  member: TInstanceMember;
  onSelesai: () => Promise<unknown>;
  onTutup: () => void;
};

/* Memberi Super Admin bukan aksi satu klik: statusnya memberi akses ke SELURUH
   project sekaligus, termasuk project yang belum dibuat. Frasanya diperiksa di
   server terhadap `SUPER_ADMIN_GRANT_PASSPHRASE`, tidak ada salinannya di sisi
   klien, jadi tidak ada yang bisa dibaca dari bundle browser. */
export function GrantSuperAdmin({ member, onSelesai, onTutup }: Props) {
  const [frasa, setFrasa] = useState("");
  const [sibuk, setSibuk] = useState(false);

  const handleKonfirmasi = async () => {
    setSibuk(true);
    try {
      await memberService.update(member.id, { is_super_admin: true, grant_passphrase: frasa });
      setFrasa("");
      await onSelesai();
      onTutup();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Super Admin diberikan",
        message: `${member.display_name} sekarang mengakses semua project, termasuk yang dibuat nanti.`,
      });
    } catch (err) {
      const message = (err as { error?: string })?.error ?? "Tidak bisa memberi Super Admin.";
      setToast({ type: TOAST_TYPE.ERROR, title: "Ditolak", message });
      setFrasa("");
    } finally {
      setSibuk(false);
    }
  };

  return (
    <div className="space-y-3 border-t border-subtle bg-warning-subtle/40 p-4">
      <div className="flex items-start gap-2">
        <ShieldAlert className="mt-0.5 size-4 shrink-0 text-warning-primary" />
        <div className="space-y-1">
          <p className="text-body-sm-regular font-medium text-primary">Jadikan {member.display_name} Super Admin?</p>
          <p className="text-11 text-secondary">
            Dia akan mengakses <strong>seluruh project</strong>, termasuk yang dibuat setelah ini, tanpa muncul di
            daftar anggota mana pun. Masukkan frasa konfirmasi untuk melanjutkan.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          className={`${inputClass} min-w-[240px]`}
          type="password"
          placeholder="Frasa konfirmasi"
          value={frasa}
          onChange={(e) => setFrasa(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && frasa && !sibuk) handleKonfirmasi();
          }}
        />
        <Button variant="primary" size="sm" disabled={sibuk || !frasa} onClick={handleKonfirmasi}>
          Beri Super Admin
        </Button>
        <Button variant="secondary" size="sm" disabled={sibuk} onClick={onTutup}>
          Batal
        </Button>
      </div>
    </div>
  );
}
