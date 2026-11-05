/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: konfirmasi peran manager di departemen lain
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * KEP-93 (5 Nov 2026): tidak ada "manager departemen". Manager yang diseret ke
 * departemen di divisi LAIN duduk di sana sebagai Staf atau Supervisor, dan
 * jenjang Manager-nya tetap. Dialog ini menanyakan perannya sebelum disimpan
 * (permintaan user: "when we add/drag, ask me for confirmation").
 */

import { useState } from "react";
// plane imports
import { Button } from "@plane/propel/button";
import { TINGKAT_MEMBER, TINGKAT_SUPERVISOR } from "@plane/services";
import { cn } from "@plane/utils";
// local
import { EModalWidth, ParadiseModal } from "@/components/common/paradise-ui";
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { namaJenjang } from "./papan-logika";

export type TTawaranPeran = {
  nama: string;
  tempat: string;
  /** Peran yang terpilih saat dialog dibuka (lajur tempat ia dilepas). */
  bawaan: number;
  kirim: (peran: number) => Promise<unknown>;
};

const PILIHAN = [TINGKAT_SUPERVISOR, TINGKAT_MEMBER] as const;

export function DialogPeran({ tawaran, onTutup }: { tawaran: TTawaranPeran | null; onTutup: () => void }) {
  return tawaran ? (
    // `key` = dialog baru per tawaran, jadi pilihan bawaan tidak terbawa dari tawaran lama.
    <IsiDialogPeran key={`${tawaran.nama}:${tawaran.tempat}`} tawaran={tawaran} onTutup={onTutup} />
  ) : null;
}

function IsiDialogPeran({ tawaran, onTutup }: { tawaran: TTawaranPeran; onTutup: () => void }) {
  const { s, fill } = useGodmodeStrings();
  const [peran, setPeran] = useState(tawaran.bawaan);
  const [sibuk, setSibuk] = useState(false);
  const isi = { name: tawaran.nama, place: tawaran.tempat };

  const kirim = async () => {
    setSibuk(true);
    try {
      await tawaran.kirim(peran);
      onTutup();
    } finally {
      setSibuk(false);
    }
  };

  return (
    <ParadiseModal
      isOpen
      onClose={onTutup}
      width={EModalWidth.MD}
      title={fill(s.org.board.role_title, isi)}
      closeLabel={s.editor.close}
      footer={
        <>
          <Button variant="secondary" size="base" onClick={onTutup}>
            {s.org.cancel}
          </Button>
          <Button variant="primary" size="base" loading={sibuk} onClick={() => void kirim()}>
            {fill(s.org.board.role_confirm, { role: namaJenjang(peran, s) })}
          </Button>
        </>
      }
    >
      <p className="text-13 text-secondary">{fill(s.org.board.role_message, isi)}</p>
      <fieldset className="mt-3 grid gap-2">
        <legend className="sr-only">{fill(s.org.board.role_label, isi)}</legend>
        {PILIHAN.map((t) => {
          const aktif = t === peran;
          return (
            <label
              key={t}
              aria-label={namaJenjang(t, s)}
              className={cn(
                "flex cursor-pointer items-start gap-2 rounded-card border px-3 py-2 transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent-strong",
                aktif ? "border-accent-strong bg-accent-subtle" : "border-subtle hover:bg-layer-transparent-hover"
              )}
            >
              <input
                type="radio"
                name="peran-departemen"
                value={t}
                checked={aktif}
                onChange={() => setPeran(t)}
                className="mt-1 accent-current"
              />
              <span>
                <span className="block text-13 font-medium text-primary">{namaJenjang(t, s)}</span>
                <span className="block text-11 text-tertiary">
                  {t === TINGKAT_SUPERVISOR ? s.org.board.role_supervisor_hint : s.org.board.role_staff_hint}
                </span>
              </span>
            </label>
          );
        })}
      </fieldset>
    </ParadiseModal>
  );
}
