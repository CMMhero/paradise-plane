/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: status sesi & kick
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { LogOut } from "lucide-react";
// plane imports
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { Tooltip } from "@plane/propel/tooltip";
import { InstanceActivityService } from "@plane/services";
// components
import { IconAction } from "@/components/common/paradise-ui";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";

const activityService = new InstanceActivityService();

type Props = {
  userId: string;
  nama: string;
  masihLogin: boolean;
  sedangMemakai: boolean;
  /** Baris milik admin yang sedang membuka halaman, backend menolak kick diri sendiri. */
  diriSendiri: boolean;
  onSelesai: () => void;
};

/**
 * Titik status + tombol putuskan sesi.
 *
 * Tiga keadaan, sengaja dibedakan: sesi bisa hidup berhari-hari sesudah orangnya
 * menutup laptop, jadi "masih login" bukan bukti seseorang ada di depan layar.
 */
export function SessionCell({ userId, nama, masihLogin, sedangMemakai, diriSendiri, onSelesai }: Props) {
  const { s, fill } = useGodmodeStrings();
  const [sibuk, setSibuk] = useState(false);

  const status = sedangMemakai
    ? { warna: "bg-success-primary", label: s.session.active, judul: s.session.active_hint }
    : masihLogin
      ? { warna: "bg-warning-primary", label: s.session.idle, judul: s.session.idle_hint }
      : { warna: "bg-layer-3", label: s.session.out, judul: s.session.out_hint };

  // Hanya logout paksa. Menonaktifkan akun sudah punya kontrolnya sendiri di
  // kolom "Aktif", dan backend-nya memang sekalian memutus sesi
  // (`member.py` patch is_active -> _akhiri_sesi). Menaruh dua jalan ke hasil
  // yang sama di satu baris hanya membuat orang ragu harus menekan yang mana.
  const kick = async () => {
    if (!window.confirm(fill(s.session.kick_confirm, { name: nama }))) return;

    setSibuk(true);
    try {
      const hasil = await activityService.kick(userId);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: s.session.kicked,
        message: fill(s.session.kicked_message, { n: hasil.sesi_diputus, name: nama }),
      });
      onSelesai();
    } catch (err) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: s.session.failed,
        message: (err as { error?: string })?.error ?? s.session.kick_failed,
      });
    } finally {
      setSibuk(false);
    }
  };

  return (
    <div className="flex items-center gap-1">
      <Tooltip tooltipContent={status.judul}>
        <span className="flex items-center gap-1.5">
          <span className={`size-2 shrink-0 rounded-full ${status.warna}`} aria-hidden />
          <span className="text-12 whitespace-nowrap text-secondary">{status.label}</span>
        </span>
      </Tooltip>

      {masihLogin && !diriSendiri ? (
        <IconAction
          label={fill(s.session.kick_label, { name: nama })}
          icon={LogOut}
          disabled={sibuk}
          onClick={() => void kick()}
        />
      ) : null}
    </div>
  );
}
