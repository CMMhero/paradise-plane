/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: deteksi perangkat dari UKURAN, bukan dari
 * teks user agent
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";

/**
 * KENAPA BERKAS INI DIGANTI ISINYA
 *
 * Versi upstream mencocokkan `/iPhone|iPad|iPod|Android/i` terhadap user agent,
 * SEKALI, di dalam useEffect tanpa pendengar apa pun. 107 berkas mempercayai
 * hasilnya, termasuk sidebar utama yang memakainya untuk memutuskan menempel
 * atau melayang. Enam akibatnya nyata dan semuanya pernah dikeluhkan:
 *
 *   1. iPad 1024px mendatar diperlakukan seperti HP genggam.
 *   2. Tablet Android sama.
 *   3. Safari di iPadOS mengirim user agent Mac secara bawaan, jadi iPad yang
 *      SAMA terbaca Desktop di Safari dan HP di Chrome.
 *   4. Jendela desktop yang dikecilkan jadi separuh layar tidak pernah dianggap
 *      sempit, sidebar tetap menempel dan isi halaman tergencet.
 *   5. Memutar HP tidak memicu perhitungan ulang, karena nilainya dibekukan
 *      saat halaman pertama digambar.
 *   6. Daftar merek perangkat tidak akan pernah lengkap. Tiap perangkat baru
 *      berarti menambal daftar lagi.
 *
 * Yang dipakai sekarang adalah dua pertanyaan yang bisa dijawab peramban dengan
 * pasti, bukan ditebak dari nama perangkat: SEBERAPA LEBAR ruangnya, dan APAKAH
 * penunjuknya kasar (jari) atau halus (tetikus).
 *
 * DUA MEDAN, KARENA MEMANG ADA DUA KEBUTUHAN BERBEDA, dan menyatukannya sudah
 * jadi sebab bug di sini. Mayoritas dari 107 pemanggil meneruskan `isMobile` ke
 * Tooltip, yang sebenarnya bertanya "apakah ada hover", bukan "apakah layarnya
 * sempit". Sementara sidebar bertanya persis kebalikannya. Kalau keduanya
 * dilayani satu medan, salah satunya pasti salah: tooltip hilang saat jendela
 * desktop dikecilkan, atau sidebar melayang di iPad mendatar yang ruangnya
 * cukup.
 */

/** Di bawah ini sidebar melayang, bukan menempel.
 *
 * 1024px, bukan 768px. Sidebar aplikasi ini selebar 250px; di tablet tegak
 * 768px sisanya cuma 518px, terlalu sempit untuk daftar work item beserta
 * kolomnya. Tablet mendatar 1024px ke atas ruangnya cukup dan sidebar yang
 * menempel di situ justru lebih enak dipakai. */
const KUERI_SEMPIT = "(max-width: 1023px)";

/** Jari, bukan tetikus. Menjawab "apakah hover bisa diandalkan". */
const KUERI_SENTUH = "(pointer: coarse)";

type TPlatform = {
  /** Perlakukan sebagai perangkat sentuh: hover tidak bisa diandalkan, target
   *  sentuh harus besar, tooltip yang bergantung hover tidak akan pernah muncul.
   *
   *  Sengaja BUKAN sekadar "layar sempit", supaya tooltip tidak ikut hilang saat
   *  orang mengecilkan jendela peramban di desktop. */
  isMobile: boolean;
  /** Ruangnya sempit, apa pun perangkatnya. Ini yang dipakai untuk keputusan
   *  TATA LETAK: sidebar melayang, kolom ditumpuk, panel bergantian. */
  isLayarSempit: boolean;
  platform: string;
};

const bacaPlatform = (userAgent: string): string => {
  if (userAgent.indexOf("Win") !== -1) return "Windows";
  if (userAgent.indexOf("Mac") !== -1) return "MacOS";
  if (userAgent.indexOf("Linux") !== -1) return "Linux";
  return "Unknown";
};

export const usePlatformOS = (): TPlatform => {
  const [platformData, setPlatformData] = useState<TPlatform>({
    isMobile: false,
    isLayarSempit: false,
    platform: "",
  });

  useEffect(() => {
    const sempit = window.matchMedia(KUERI_SEMPIT);
    const sentuh = window.matchMedia(KUERI_SENTUH);

    const hitung = () => {
      setPlatformData({
        isMobile: sentuh.matches,
        isLayarSempit: sempit.matches,
        // Dikosongkan untuk perangkat sentuh, sama seperti perilaku lama, supaya
        // pemanggil yang menampilkan pintasan papan ketik tidak mendadak
        // menawarkan pintasan di perangkat yang tidak punya papan ketik.
        platform: sentuh.matches ? "" : bacaPlatform(window.navigator.userAgent),
      });
    };

    hitung();

    // Inilah yang tidak dimiliki versi lama, dan tanpanya memutar HP atau
    // mengubah ukuran jendela tidak mengubah apa pun sampai halaman dimuat ulang.
    sempit.addEventListener("change", hitung);
    sentuh.addEventListener("change", hitung);

    return () => {
      sempit.removeEventListener("change", hitung);
      sentuh.removeEventListener("change", hitung);
    };
  }, []);

  return platformData;
};
