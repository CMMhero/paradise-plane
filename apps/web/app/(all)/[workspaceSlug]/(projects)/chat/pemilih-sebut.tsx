/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pemilih sebutan @ di kotak tulis obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Fragment, useCallback, useMemo, useRef, useState } from "react";
import type { ChangeEvent, KeyboardEvent, RefObject } from "react";
import { useTranslation } from "@plane/i18n";
import { Avatar } from "@plane/ui";
import { getFileURL } from "@plane/utils";
import { cariKueriSebut, cocokSemua, saringCalon, semuaTersisa, sebutanTersisa, sisipkanSebut } from "./sebut";
import type { TKueriSebut } from "./sebut";

export type TCalonSebut = {
  id: string;
  nama: string;
  avatar?: string;
  /** Diri sendiri: boleh disebut (cuma disorot), ditandai "(you)" di daftar. */
  saya?: boolean;
  /** Entri sintetis `@all`, bukan orang. */
  semua?: boolean;
};

/** Entri `@all` di puncak daftar. Namanya yang masuk ke teks: `@all`. */
const CALON_SEMUA: TCalonSebut = { id: "__semua__", nama: "all", semua: true };

type TOpsi = {
  /** Orang yang boleh disebut di percakapan ini, termasuk diri sendiri. */
  calon: TCalonSebut[];
  /** Tawarkan `@all` (hanya di kanal, bukan DM). */
  bolehSemua: boolean;
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
export function useSebutan({ calon, bolehSemua, draf, setDraf, tulisRef }: TOpsi) {
  const [kueri, setKueri] = useState<TKueriSebut | null>(null);
  const [sorot, setSorot] = useState(0);
  const dipilih = useRef(new Map<string, string>());
  const semuaDipilih = useRef(false);

  const cocok = useMemo(() => {
    if (!kueri) return [];
    const orang = saringCalon(calon, kueri.kueri);
    return bolehSemua && cocokSemua(kueri.kueri) ? [CALON_SEMUA, ...orang] : orang;
  }, [calon, bolehSemua, kueri]);
  const terbuka = kueri !== null && (calon.length > 0 || bolehSemua);

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
      if (orang.semua) semuaDipilih.current = true;
      else dipilih.current.set(orang.id, orang.nama);
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

  /** Hanya `@all` yang dipilih dari daftar dan masih ada di teks yang jadi pemberitahuan. */
  const semuaUntukKirim = useCallback((teks: string) => semuaTersisa(teks, semuaDipilih.current), []);

  const reset = useCallback(() => {
    dipilih.current.clear();
    semuaDipilih.current = false;
    setKueri(null);
  }, []);

  return {
    terbuka,
    cocok,
    sorot,
    setSorot,
    pilih,
    onChange,
    onKeyDown,
    onKursor: perbaruiKueri,
    idUntukKirim,
    semuaUntukKirim,
    reset,
  };
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
          <Fragment key={orang.id}>
            {orang.semua ? (
              <p role="presentation" className="px-3 pt-1 pb-0.5 text-11 font-semibold text-tertiary">
                {t("rujukan_ui.section_everyone")}
              </p>
            ) : i === 1 && cocok[0]?.semua ? (
              <p role="presentation" className="px-3 pt-1.5 pb-0.5 text-11 font-semibold text-tertiary">
                {t("rujukan_ui.section_people")}
              </p>
            ) : null}
            <button
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
              {orang.semua ? (
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-accent-subtle text-12 font-semibold text-accent-primary">
                  @
                </span>
              ) : (
                <Avatar name={orang.nama} src={getFileURL(orang.avatar ?? "")} size={20} shape="circle" />
              )}
              <span className="truncate">
                {orang.semua
                  ? `@all · ${t("rujukan_ui.everyone_room")}`
                  : orang.saya
                    ? `${orang.nama} (${t("rujukan_ui.you")})`
                    : orang.nama}
              </span>
            </button>
          </Fragment>
        ))
      )}
    </div>
  );
}
