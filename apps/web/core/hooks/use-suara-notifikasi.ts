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

/** Buat elemen Audio untuk satu jenis suara, dimuat lebih awal. */
const buatAudio = (jenis: TJenisSuara) => {
  const audio = new Audio(BERKAS[jenis]);
  audio.preload = "auto";
  return audio;
};

/** Putar satu elemen dari awal pada volume tertentu. Penolakan autoplay ditelan. */
const putarDari = (audio: HTMLAudioElement, volume: number) => {
  audio.volume = Math.min(1, volume);
  audio.currentTime = 0;
  void audio.play().catch(() => {
    // Diabaikan: peramban belum mengizinkan suara otomatis.
  });
};

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

  /** Elemen dering terpisah dari `cache`: ia berulang (`loop`), dan bunyi pesan
   * yang masuk saat sedang berdering tidak boleh memotongnya. */
  const deringRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    const elemen = cache.current;
    const dering = deringRef;
    return () => {
      // Dihentikan saat komponen dilepas supaya bunyi tidak menggantung setelah
      // orangnya berpindah halaman.
      Object.values(elemen).forEach((audio) => audio?.pause());
      dering.current?.pause();
    };
  }, []);

  const suaraSekarang = useCallback((): TSuara => bacaSuara(profil.data?.theme, bisuLama), [profil, bisuLama]);

  const putar = useCallback((jenis: TJenisSuara, volume: number) => {
    if (volume <= 0) return;
    const tersimpan = cache.current[jenis];
    const audio = tersimpan ?? buatAudio(jenis);
    if (!tersimpan) cache.current[jenis] = audio;
    putarDari(audio, volume);
  }, []);

  /** Bunyi pemberitahuan sungguhan: mengikuti volume & bisu akun. */
  const bunyikan = useCallback(
    (jenis: TJenisSuara) => putar(jenis, volumeAudio(suaraSekarang())),
    [putar, suaraSekarang]
  );

  /** Nada dering panggilan masuk, berulang sampai `hentikanDering`.
   *
   * Ikut volume & bisu akun seperti bunyi lain: orang yang membisukan
   * notifikasi tetap melihat kartu panggilan masuk, hanya tanpa suara. Ditolak
   * autoplay (tab belum pernah diklik) itu wajar dan ditelan; kartunya tetap
   * tampil, dan kartu peramban menutupi tab yang tersembunyi. */
  const mulaiDering = useCallback(() => {
    const volume = volumeAudio(suaraSekarang());
    if (volume <= 0) return;
    let audio = deringRef.current;
    if (!audio) {
      audio = new Audio(BERKAS.panggilan);
      audio.loop = true;
      audio.preload = "auto";
      deringRef.current = audio;
    }
    putarDari(audio, volume);
  }, [suaraSekarang]);

  const hentikanDering = useCallback(() => {
    const audio = deringRef.current;
    if (!audio) return;
    audio.pause();
    audio.currentTime = 0;
  }, []);

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

  return { bunyikan, pratinjau, nyala, suara, setNyala, mulaiDering, hentikanDering };
};
