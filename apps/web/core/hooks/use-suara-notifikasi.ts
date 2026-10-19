/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: suara notifikasi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useRef } from "react";
import suaraPanggilan from "@/app/assets/sounds/notifikasi-panggilan.mp3?url";
import suaraPesan from "@/app/assets/sounds/notifikasi-pesan.mp3?url";
import useLocalStorage from "./use-local-storage";

/** Nama kuncinya menyebut "obrolan" karena di situlah ia lahir, tapi sejak ada
 * PenjagaNotifikasi ia mengatur SELURUH bunyi pemberitahuan, termasuk tugas yang
 * diberikan dan penyebutan di komentar. Namanya sengaja TIDAK diganti: mengganti
 * kunci berarti mengosongkan pilihan yang sudah tersimpan di peramban semua
 * orang, dan yang sudah mematikan bunyi akan mendapatkannya menyala lagi. */
export const KUNCI_SUARA = "suara_notifikasi_obrolan";

const BERKAS = {
  pesan: suaraPesan,
  panggilan: suaraPanggilan,
} as const;

export type TJenisSuara = keyof typeof BERKAS;

/** Memutar suara notifikasi, dengan SATU saklar bisu yang tersimpan per peramban.
 *
 * Elemen Audio dibuat sekali lalu dipakai ulang, bukan `new Audio()` tiap kali
 * berbunyi: pesan yang datang beruntun akan meninggalkan tumpukan elemen audio
 * yang tidak pernah dibersihkan.
 *
 * Peramban menolak memutar suara sebelum penggunanya pernah berinteraksi dengan
 * halaman. Penolakan itu WAJAR dan sengaja ditelan: satu bunyi yang gagal bukan
 * alasan untuk memunculkan galat ke orang yang belum melakukan apa-apa.
 */
export const useSuaraNotifikasi = () => {
  const { storedValue, setValue } = useLocalStorage<boolean>(KUNCI_SUARA, true);
  const nyala = storedValue ?? true;
  const cache = useRef<Partial<Record<TJenisSuara, HTMLAudioElement>>>({});

  useEffect(() => {
    const elemen = cache.current;
    return () => {
      // Dihentikan saat komponen dilepas supaya bunyi tidak menggantung setelah
      // orangnya berpindah halaman.
      Object.values(elemen).forEach((audio) => audio?.pause());
    };
  }, []);

  const bunyikan = useCallback(
    (jenis: TJenisSuara) => {
      if (!nyala) return;
      let audio = cache.current[jenis];
      if (!audio) {
        audio = new Audio(BERKAS[jenis]);
        audio.preload = "auto";
        cache.current[jenis] = audio;
      }
      audio.currentTime = 0;
      void audio.play().catch(() => {
        // Diabaikan: peramban belum mengizinkan suara otomatis.
      });
    },
    [nyala]
  );

  return { bunyikan, nyala, setNyala: setValue };
};
