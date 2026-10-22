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
import { cocokKonfirmasiGrant, useGodmodeStrings } from "@/app/i18n/godmode";
import { inputClass } from "./constants";

const memberService = new InstanceMemberService();

type Props = {
  member: TInstanceMember;
  onSelesai: () => Promise<unknown>;
  onTutup: () => void;
};

/* Memberi Super Admin bukan aksi satu klik: statusnya memberi akses ke SELURUH
   project sekaligus, termasuk project yang belum dibuat. Konfirmasinya berupa
   frasa yang DIKETIK (diperiksa server), bukan rahasia bersama — mengetik
   tidak bisa terjadi karena salah klik. */
export function GrantSuperAdmin({ member, onSelesai, onTutup }: Props) {
  const { s, fill } = useGodmodeStrings();
  const [frasa, setFrasa] = useState("");
  const [sibuk, setSibuk] = useState(false);
  const frasaCocok = cocokKonfirmasiGrant(frasa);

  const handleKonfirmasi = async () => {
    if (!cocokKonfirmasiGrant(frasa)) return;
    setSibuk(true);
    try {
      await memberService.update(member.id, { is_super_admin: true, grant_confirm: frasa });
      setFrasa("");
      await onSelesai();
      onTutup();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: s.grant.granted,
        message: fill(s.grant.granted_message, { name: member.display_name }),
      });
    } catch (err) {
      const message = (err as { error?: string })?.error ?? s.grant.failed;
      setToast({ type: TOAST_TYPE.ERROR, title: s.grant.denied, message });
      setFrasa("");
    } finally {
      setSibuk(false);
    }
  };

  return (
    <div className="space-y-3 border-t border-subtle bg-warning-subtle/40 p-4">
      <div className="flex items-start gap-2">
        <ShieldAlert className="mt-0.5 size-4 shrink-0 text-warning-primary" aria-hidden />
        <div className="space-y-1">
          <p className="text-body-sm-regular font-medium text-primary">
            {fill(s.grant.title, { name: member.display_name })}
          </p>
          <p className="text-11 text-secondary">{s.grant.description}</p>
          <p className="text-11 text-secondary">
            {fill(s.grant.confirm_instruction, { phrase: s.grant.confirm_phrase }).split(s.grant.confirm_phrase)[0]}
            <code className="font-mono rounded bg-layer-2 px-1 py-0.5 text-primary">{s.grant.confirm_phrase}</code>
            {fill(s.grant.confirm_instruction, { phrase: s.grant.confirm_phrase }).split(s.grant.confirm_phrase)[1]}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          className={`${inputClass} min-w-[240px]`}
          type="text"
          autoComplete="off"
          placeholder={s.grant.confirm_phrase}
          aria-label={s.grant.confirm_phrase}
          aria-invalid={frasa.length > 0 && !frasaCocok}
          value={frasa}
          onChange={(e) => setFrasa(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && frasaCocok && !sibuk) handleKonfirmasi();
          }}
        />
        <Button variant="primary" size="sm" disabled={sibuk || !frasaCocok} onClick={handleKonfirmasi}>
          {s.grant.confirm}
        </Button>
        <Button variant="secondary" size="sm" disabled={sibuk} onClick={onTutup}>
          {s.grant.cancel}
        </Button>
      </div>
    </div>
  );
}
