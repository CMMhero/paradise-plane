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
import { InstanceActivityService } from "@plane/services";

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
  const [sibuk, setSibuk] = useState(false);

  const status = sedangMemakai
    ? { warna: "bg-green-600", label: "Sedang memakai", judul: "Ada request dalam beberapa menit terakhir" }
    : masihLogin
      ? { warna: "bg-amber-600", label: "Masih login", judul: "Sesi masih hidup, tapi tidak ada aktivitas terbaru" }
      : { warna: "bg-placeholder", label: "Keluar", judul: "Tidak ada sesi hidup" };

  // Hanya logout paksa. Menonaktifkan akun sudah punya kontrolnya sendiri di
  // kolom "Aktif", dan backend-nya memang sekalian memutus sesi
  // (`member.py` patch is_active -> _akhiri_sesi). Menaruh dua jalan ke hasil
  // yang sama di satu baris hanya membuat orang ragu harus menekan yang mana.
  const kick = async () => {
    if (!window.confirm(`Putuskan semua sesi ${nama}? Dia akan diminta login lagi.`)) return;

    setSibuk(true);
    try {
      const hasil = await activityService.kick(userId);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: "Sesi diputus",
        message: `${hasil.sesi_diputus} sesi ${nama} diakhiri.`,
      });
      onSelesai();
    } catch (err) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Gagal",
        message: (err as { error?: string })?.error ?? "Tidak bisa memutus sesi.",
      });
    } finally {
      setSibuk(false);
    }
  };

  return (
    <div className="flex items-center justify-center gap-2">
      <span className="flex items-center gap-1.5" title={status.judul}>
        <span className={`size-2 rounded-full ${status.warna}`} aria-hidden />
        <span className="text-11 whitespace-nowrap text-secondary">{status.label}</span>
      </span>

      {masihLogin && !diriSendiri ? (
        <button
          type="button"
          disabled={sibuk}
          onClick={() => kick()}
          className="hover:text-red-600 rounded p-1 text-secondary hover:bg-layer-1 disabled:opacity-40"
          title="Putuskan sesi, dia harus login lagi"
          aria-label={`Putuskan sesi ${nama}`}
        >
          <LogOut className="size-4" />
        </button>
      ) : null}
    </div>
  );
}
