/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pemilih rujukan # (kanal dan work item) di kotak tulis obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, KeyboardEvent, RefObject } from "react";
import { Hash, Lock } from "lucide-react";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import { ChatService } from "@/services/chat.service";
import { cariKueri, rujukanTersisa, sisipkanRujukan } from "./sebut";
import type { TKueriSebut } from "./sebut";

const chatService = new ChatService();

/** Jeda ketik sebelum mencari, supaya satu huruf tidak jadi satu permintaan. */
const JEDA_CARI_MS = 200;

export type TCalonRujukan =
  | { jenis: "kanal"; id: string; teks: string; privat: boolean }
  | { jenis: "tugas"; id: string; teks: string; judul: string };

type TOpsi = {
  slug: string | undefined;
  draf: string;
  setDraf: (teks: string) => void;
  tulisRef: RefObject<HTMLTextAreaElement | null>;
};

/**
 * State pemilih `#` untuk satu kotak tulis, kembaran `useSebutan`.
 *
 * Calonnya datang dari server (`cariRujukan`): kanal yang boleh saya lihat dan
 * work item di project saya. ID yang dipilih disimpan terpisah dan baru disaring
 * saat kirim, jadi rujukan yang sudah dihapus dari draf tidak ikut terkirim.
 */
export function useRujukan({ slug, draf, setDraf, tulisRef }: TOpsi) {
  const [kueri, setKueri] = useState<TKueriSebut | null>(null);
  const [sorot, setSorot] = useState(0);
  const [kueriTunda, setKueriTunda] = useState<string | null>(null);
  const kanalDipilih = useRef(new Map<string, string>());
  const tugasDipilih = useRef(new Map<string, string>());

  // Kueri yang dikirim ke server ikut tertunda; null = pemilih tertutup.
  const teksKueri = kueri?.kueri ?? null;
  useEffect(() => {
    if (teksKueri === null) {
      // oxlint-disable-next-line react/set-state-in-effect -- menyelaraskan kueri tertunda dengan pemilih yang menutup
      setKueriTunda(null);
      return;
    }
    const timer = setTimeout(() => setKueriTunda(teksKueri), JEDA_CARI_MS);
    return () => clearTimeout(timer);
  }, [teksKueri]);

  const { data, error } = useSWR(
    slug && kueriTunda !== null ? `CHAT_RUJUKAN_${slug}_${kueriTunda}` : null,
    slug && kueriTunda !== null ? () => chatService.cariRujukan(slug, kueriTunda) : null,
    { keepPreviousData: true, revalidateOnFocus: false }
  );

  const cocok: TCalonRujukan[] = useMemo(
    () => [
      ...(data?.kanal ?? []).map(
        (k): TCalonRujukan => ({ jenis: "kanal", id: k.id, teks: k.nama, privat: k.tipe === "privat" })
      ),
      ...(data?.tugas ?? []).map((w): TCalonRujukan => ({ jenis: "tugas", id: w.id, teks: w.nomor, judul: w.judul })),
    ],
    [data]
  );
  const terbuka = kueri !== null;
  // Menunggu: jeda ketik belum lewat, atau jawaban pertama belum datang.
  const memuat = terbuka && !error && (kueriTunda !== teksKueri || !data);

  const perbaruiKueri = useCallback((teks: string, kursor: number) => {
    setKueri(cariKueri(teks, kursor, "#"));
    setSorot(0);
  }, []);

  const onChange = useCallback(
    (e: ChangeEvent<HTMLTextAreaElement>) => perbaruiKueri(e.target.value, e.target.selectionStart ?? 0),
    [perbaruiKueri]
  );

  const pilih = useCallback(
    (calon: TCalonRujukan) => {
      const el = tulisRef.current;
      if (!kueri || !el) return;
      const hasil = sisipkanRujukan(draf, kueri.awal, el.selectionStart ?? draf.length, calon.teks, "#");
      (calon.jenis === "kanal" ? kanalDipilih : tugasDipilih).current.set(calon.id, calon.teks);
      setDraf(hasil.teks);
      setKueri(null);
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
      if ((e.key === "ArrowDown" || e.key === "ArrowUp") && cocok.length > 0) {
        e.preventDefault();
        const arah = e.key === "ArrowDown" ? 1 : -1;
        setSorot((s) => (s + arah + cocok.length) % cocok.length);
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

  const idUntukKirim = useCallback(
    (teks: string) => ({
      kanal: rujukanTersisa(teks, kanalDipilih.current, "#"),
      tugas: rujukanTersisa(teks, tugasDipilih.current, "#"),
    }),
    []
  );

  const reset = useCallback(() => {
    kanalDipilih.current.clear();
    tugasDipilih.current.clear();
    setKueri(null);
  }, []);

  return {
    terbuka,
    cocok,
    memuat,
    sorot,
    setSorot,
    pilih,
    onChange,
    onKeyDown,
    onKursor: perbaruiKueri,
    idUntukKirim,
    reset,
  };
}

type TDaftarProps = {
  cocok: TCalonRujukan[];
  memuat: boolean;
  sorot: number;
  onSorot: (i: number) => void;
  onPilih: (calon: TCalonRujukan) => void;
};

const judulBagian = (teks: string) => (
  <p role="presentation" className="px-3 pt-1.5 pb-0.5 text-11 font-semibold text-tertiary">
    {teks}
  </p>
);

/** Daftar calon di atas kotak tulis, dua bagian: kanal lalu work item. Dirender hanya saat pemilih terbuka. */
export function DaftarRujukan({ cocok, memuat, sorot, onSorot, onPilih }: TDaftarProps) {
  const { t } = useTranslation();
  const adaKanal = cocok.some((c) => c.jenis === "kanal");
  const idxTugasPertama = cocok.findIndex((c) => c.jenis === "tugas");
  return (
    <div
      // oxlint-disable-next-line jsx-a11y/prefer-tag-over-role -- combobox ARIA, lihat DaftarSebut
      role="listbox"
      aria-label={t("rujukan_ui.mention_channel_label")}
      aria-busy={memuat}
      className="absolute right-0 bottom-full left-0 z-20 mb-1 max-h-64 overflow-y-auto rounded-popover border border-subtle bg-surface-1 py-1 shadow-overlay-200"
    >
      {cocok.length === 0 ? (
        <p className="px-3 py-2 text-12 text-tertiary">{memuat ? t("rujukan_ui.loading") : t("rujukan_ui.none")}</p>
      ) : (
        cocok.map((calon, i) => (
          <div key={`${calon.jenis}-${calon.id}`}>
            {i === 0 && adaKanal ? judulBagian(t("rujukan_ui.section_channels")) : null}
            {i === idxTugasPertama ? judulBagian(t("rujukan_ui.section_work_items")) : null}
            <button
              type="button"
              // oxlint-disable-next-line jsx-a11y/prefer-tag-over-role -- opsi combobox ARIA, lihat DaftarSebut
              role="option"
              aria-selected={i === sorot}
              // mousedown, bukan click: click datang sesudah textarea kehilangan fokus.
              onMouseDown={(e) => {
                e.preventDefault();
                onPilih(calon);
              }}
              onMouseEnter={() => onSorot(i)}
              className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-13 text-primary ${
                i === sorot ? "bg-layer-1-selected" : "hover:bg-layer-1"
              }`}
            >
              {calon.jenis === "kanal" ? (
                calon.privat ? (
                  <Lock className="size-4 shrink-0 text-tertiary" aria-label={t("rujukan_ui.private_channel")} />
                ) : (
                  <Hash className="size-4 shrink-0 text-tertiary" aria-label={t("rujukan_ui.public_channel")} />
                )
              ) : null}
              <span className="shrink-0 font-medium">{calon.jenis === "kanal" ? calon.teks : `#${calon.teks}`}</span>
              {calon.jenis === "tugas" ? <span className="truncate text-tertiary">{calon.judul}</span> : null}
            </button>
          </div>
        ))
      )}
    </div>
  );
}
