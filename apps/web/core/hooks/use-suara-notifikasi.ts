/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: suara notifikasi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useRef } from "react";
import suaraPanggilan from "@/app/assets/sounds/notifikasi-panggilan.mp3?url";
import suaraPesan from "@/app/assets/sounds/notifikasi-pesan.mp3?url";
import { bacaSuara, SUARA_PABRIK, volumeAudio, type TSuara } from "@/lib/suara";
import { useUserProfile } from "./store/user";
import useLocalStorage from "./use-local-storage";

/** Saklar bisu LAMA per peramban. Sejak volume per akun (`profile.theme`), kunci
 * ini hanya dibaca sebagai cadangan untuk akun yang belum pernah menyimpan
 * `suara_bisu`, supaya yang dulu mematikan bunyi tidak mendengarnya lagi.
 * Namanya sengaja TIDAK diganti. */
export const KUNCI_SUARA = "suara_notifikasi_obrolan";

const BERKAS = {
  pesan: suaraPesan,
  panggilan: suaraPanggilan,
} as const;

export type TJenisSuara = keyof typeof BERKAS;

/** Memutar suara notifikasi dengan volume dan bisu milik akun ini.
 *
 * Elemen Audio dibuat sekali lalu dipakai ulang, bukan `new Audio()` tiap kali
 * berbunyi: pesan yang datang beruntun akan meninggalkan tumpukan elemen audio
 * yang tidak pernah dibersihkan.
 *
 * Volume dibaca SAAT berbunyi dari store profil, bukan dari nilai render, jadi
 * penjaga yang hidup di luar `observer` tetap memakai setelan terbaru.
 *
 * Peramban menolak memutar suara sebelum penggunanya pernah berinteraksi dengan
 * halaman. Penolakan itu WAJAR dan sengaja ditelan.
 */
export const useSuaraNotifikasi = () => {
  const { storedValue: nyalaLama } = useLocalStorage<boolean>(KUNCI_SUARA, true);
  const profil = useUserProfile();
  const cache = useRef<Partial<Record<TJenisSuara, HTMLAudioElement>>>({});
  const bisuLama = nyalaLama === false;

  useEffect(() => {
    const elemen = cache.current;
    return () => {
      // Dihentikan saat komponen dilepas supaya bunyi tidak menggantung setelah
      // orangnya berpindah halaman.
      Object.values(elemen).forEach((audio) => audio?.pause());
    };
  }, []);

  const suaraSekarang = useCallback((): TSuara => bacaSuara(profil.data?.theme, bisuLama), [profil, bisuLama]);

  const putar = useCallback((jenis: TJenisSuara, volume: number) => {
    if (volume <= 0) return;
    let audio = cache.current[jenis];
    if (!audio) {
      audio = new Audio(BERKAS[jenis]);
      audio.preload = "auto";
      cache.current[jenis] = audio;
    }
    audio.volume = Math.min(1, volume);
    audio.currentTime = 0;
    void audio.play().catch(() => {
      // Diabaikan: peramban belum mengizinkan suara otomatis.
    });
  }, []);

  /** Bunyi pemberitahuan sungguhan: mengikuti volume & bisu akun. */
  const bunyikan = useCallback(
    (jenis: TJenisSuara) => putar(jenis, volumeAudio(suaraSekarang())),
    [putar, suaraSekarang]
  );

  /** Pratinjau di Preferensi: memutar pada volume yang sedang digeser, abaikan bisu. */
  const pratinjau = useCallback((volume: number) => putar("pesan", volume / 100), [putar]);

  const suara = suaraSekarang();
  const nyala = !suara.bisu && suara.volume > 0;

  /** Saklar cepat di Obrolan & panel Pemberitahuan: menulis `suara_bisu` ke akun. */
  const setNyala = useCallback(
    (nilai: boolean) => {
      // Menyalakan dari volume 0 tidak akan terdengar; kembalikan ke volume pabrik.
      const tambahan = nilai && suaraSekarang().volume === 0 ? { volume_suara: SUARA_PABRIK.volume } : {};
      void profil.updateUserTheme({ suara_bisu: !nilai, ...tambahan }).catch(() => undefined);
    },
    [profil, suaraSekarang]
  );

  return { bunyikan, pratinjau, nyala, suara, setNyala };
};
