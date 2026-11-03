/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pemilih sebutan @ di kotak tulis obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useMemo, useRef, useState } from "react";
import type { ChangeEvent, KeyboardEvent, RefObject } from "react";
import { useTranslation } from "@plane/i18n";
import { Avatar } from "@plane/ui";
import { getFileURL } from "@plane/utils";
import { cariKueriSebut, saringCalon, sebutanTersisa, sisipkanSebut } from "./sebut";
import type { TKueriSebut } from "./sebut";

export type TCalonSebut = { id: string; nama: string; avatar?: string };

type TOpsi = {
  /** Orang yang boleh disebut di percakapan ini, TANPA diri sendiri. */
  calon: TCalonSebut[];
  draf: string;
  setDraf: (teks: string) => void;
  tulisRef: RefObject<HTMLTextAreaElement | null>;
};

/**
 * State pemilih `@` untuk satu kotak tulis.
 *
 * Kotak tulisnya tetap textarea biasa; hook ini cuma membaca posisi kursor,
 * menawarkan calon, lalu menyisipkan `@nama`. ID yang dipilih disimpan terpisah
 * dan baru disaring saat kirim (`idUntukKirim`), jadi sebutan yang sudah dihapus
 * dari draf tidak ikut terkirim.
 */
export function useSebutan({ calon, draf, setDraf, tulisRef }: TOpsi) {
  const [kueri, setKueri] = useState<TKueriSebut | null>(null);
  const [sorot, setSorot] = useState(0);
  const dipilih = useRef(new Map<string, string>());

  const cocok = useMemo(() => (kueri ? saringCalon(calon, kueri.kueri) : []), [calon, kueri]);
  const terbuka = kueri !== null && calon.length > 0;

  const perbaruiKueri = useCallback((teks: string, kursor: number) => {
    setKueri(cariKueriSebut(teks, kursor));
    setSorot(0);
  }, []);

  const onChange = useCallback(
    (e: ChangeEvent<HTMLTextAreaElement>) => perbaruiKueri(e.target.value, e.target.selectionStart ?? 0),
    [perbaruiKueri]
  );

  const pilih = useCallback(
    (orang: TCalonSebut) => {
      const el = tulisRef.current;
      if (!kueri || !el) return;
      const hasil = sisipkanSebut(draf, kueri.awal, el.selectionStart ?? draf.length, orang.nama);
      dipilih.current.set(orang.id, orang.nama);
      setDraf(hasil.teks);
      setKueri(null);
      // Kursor dipindah sesudah React menulis nilai baru ke textarea.
      requestAnimationFrame(() => {
        el.focus();
        el.setSelectionRange(hasil.kursor, hasil.kursor);
      });
    },
    [draf, kueri, setDraf, tulisRef]
  );

  /** true = tombolnya sudah dipakai pemilih, jangan diteruskan ke penangan kirim. */
  const onKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>): boolean => {
      if (!terbuka) return false;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const arah = e.key === "ArrowDown" ? 1 : -1;
        setSorot((s) => (cocok.length === 0 ? 0 : (s + arah + cocok.length) % cocok.length));
        return true;
      }
      if ((e.key === "Enter" || e.key === "Tab") && cocok[sorot]) {
        e.preventDefault();
        pilih(cocok[sorot]);
        return true;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        setKueri(null);
        return true;
      }
      return false;
    },
    [terbuka, cocok, sorot, pilih]
  );

  const idUntukKirim = useCallback((teks: string) => sebutanTersisa(teks, dipilih.current), []);

  const reset = useCallback(() => {
    dipilih.current.clear();
    setKueri(null);
  }, []);

  return { terbuka, cocok, sorot, setSorot, pilih, onChange, onKeyDown, onKursor: perbaruiKueri, idUntukKirim, reset };
}

type TDaftarProps = {
  cocok: TCalonSebut[];
  sorot: number;
  onSorot: (i: number) => void;
  onPilih: (orang: TCalonSebut) => void;
};

/** Daftar calon di atas kotak tulis. Dirender hanya saat pemilih terbuka. */
export function DaftarSebut({ cocok, sorot, onSorot, onPilih }: TDaftarProps) {
  const { t } = useTranslation();
  return (
    // Pola combobox ARIA: fokus tetap di textarea, jadi <select>/<datalist> tidak
    // bisa dipakai (keduanya mencuri fokus dan tidak bisa menampilkan avatar).
    <div
      // oxlint-disable-next-line jsx-a11y/prefer-tag-over-role
      role="listbox"
      aria-label={t("chatkartu_ui.mention_label")}
      className="absolute right-0 bottom-full left-0 z-20 mb-1 max-h-64 overflow-y-auto rounded-popover border border-subtle bg-surface-1 py-1 shadow-overlay-200"
    >
      {cocok.length === 0 ? (
        <p className="px-3 py-2 text-12 text-tertiary">{t("chatkartu_ui.mention_none")}</p>
      ) : (
        cocok.map((orang, i) => (
          <button
            key={orang.id}
            type="button"
            // oxlint-disable-next-line jsx-a11y/prefer-tag-over-role -- opsi combobox ARIA, lihat di atas
            role="option"
            aria-selected={i === sorot}
            // mousedown, bukan click: click datang SESUDAH textarea kehilangan
            // fokus, dan kursor yang dipakai sisipan sudah hilang.
            onMouseDown={(e) => {
              e.preventDefault();
              onPilih(orang);
            }}
            onMouseEnter={() => onSorot(i)}
            className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-13 text-primary ${
              i === sorot ? "bg-layer-1-selected" : "hover:bg-layer-1"
            }`}
          >
            <Avatar name={orang.nama} src={getFileURL(orang.avatar ?? "")} size={20} shape="circle" />
            <span className="truncate">{orang.nama}</span>
          </button>
        ))
      )}
    </div>
  );
}
