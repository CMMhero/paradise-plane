/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: indikator kehadiran obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Kehadiran (online / away / offline) anggota workspace.
 *
 * Satu soket per tab ke `apps/live` (`/obrolan/?mode=kehadiran`), dipasang SEKALI
 * di lapisan workspace oleh `useSambungKehadiran`. Komponen mana pun membaca
 * status satu orang lewat `useStatusKehadiran(userId)` tanpa membuka sambungan
 * sendiri dan tanpa menarik apa pun dari server: datanya didorong lewat soket.
 *
 * Status tab ini sendiri: "online" kalau tab terlihat dan ada gerakan dalam
 * AMBANG_AWAY_MS, selain itu "away". Server menggabungkan semua tab satu orang
 * (yang terbaik menang) dan menganggap tab yang berhenti berdetak sudah pergi.
 */

import { useEffect, useSyncExternalStore } from "react";
import { LIVE_BASE_PATH, LIVE_BASE_URL } from "@plane/constants";
import { segarkanSemua, terimaSinyalData, type TSinyalData } from "@/lib/data-live";
import {
  statusTab,
  terapkanPesanKehadiran,
  type TPesanKehadiran,
  type TPetaKehadiran,
  type TStatusKehadiran,
} from "@/lib/kehadiran";

export type { TStatusKehadiran } from "@/lib/kehadiran";

/** Detak tiap 25 detik; server menganggap pergi sesudah 75 detik tanpa detak. */
const SELANG_DETAK_MS = 25_000;
/** Gerakan mouse dicatat paling sering sekali per detik. */
const JEDA_CATAT_GERAK_MS = 1000;
const TANGGA_SAMBUNG_ULANG = [1000, 2000, 5000, 10000, 30000];

// ---- penyimpanan bersama (satu per tab) ----
let peta: TPetaKehadiran = new Map();
const pendengar = new Set<() => void>();

const kabari = () => pendengar.forEach((f) => f());

const langganan = (f: () => void) => {
  pendengar.add(f);
  return () => {
    pendengar.delete(f);
  };
};

/** Status satu orang. Offline kalau tidak ada tab yang melapor. */
export function useStatusKehadiran(userId: string | null | undefined): TStatusKehadiran {
  return useSyncExternalStore(
    langganan,
    () => (userId ? (peta.get(userId) ?? "offline") : "offline"),
    () => "offline"
  );
}

/** Seluruh peta kehadiran, untuk mengurutkan daftar. Petanya diganti utuh pada
 * tiap perubahan (tidak pernah diubah di tempat), jadi aman sebagai snapshot. */
export function usePetaKehadiran(): TPetaKehadiran {
  return useSyncExternalStore(
    langganan,
    () => peta,
    () => peta
  );
}

// ---- sinyal panggilan DM (menumpang soket yang sama) ----
/** Soket kehadiran tab ini, kalau sedang terbuka. Satu-satunya jalur sinyal
 * panggilan DM: ia hidup di lapisan workspace, jadi dering sampai ke halaman
 * mana pun, bukan cuma saat percakapannya sedang dibuka. */
let soketTerbuka: WebSocket | null = null;
const pendengarPanggilan = new Set<(pesan: unknown) => void>();

/** Dengarkan sinyal panggilan (`tipe: "panggilan"`). Bentuknya diperiksa
 * pemakainya; lapisan soket hanya mengantar. */
export function dengarPanggilan(f: (pesan: unknown) => void): () => void {
  pendengarPanggilan.add(f);
  return () => {
    pendengarPanggilan.delete(f);
  };
}

/** Kirim satu sinyal panggilan. `false` kalau soket sedang putus, supaya
 * pemanggil bisa bilang begitu alih-alih menunggu jawaban yang tak akan datang.
 * `dari` sengaja tidak ada: server yang mengisinya dari identitas terperiksa. */
export function kirimSinyalPanggilan(isi: { ke: string; ruang: string; muatan: unknown }): boolean {
  const ws = soketTerbuka;
  if (!ws || ws.readyState !== WebSocket.OPEN) return false;
  try {
    ws.send(JSON.stringify({ tipe: "panggilan", ...isi }));
    return true;
  } catch {
    return false;
  }
}

/** Dibaca di dalam penangan klik, di luar render. */
export const soketKehadiranTerbuka = (): boolean => soketTerbuka?.readyState === WebSocket.OPEN;

/** Soket kehadiran sedang terbuka: tombol panggilan DM boleh ditekan. */
export function useKehadiranTersambung(): boolean {
  return useSyncExternalStore(
    langganan,
    () => soketTerbuka !== null,
    () => false
  );
}

// ---- sambungan (satu per tab, dihitung referensinya) ----
let pemakai = 0;
let hentikan: (() => void) | null = null;

function mulai(slug: string): () => void {
  let hidup = true;
  let ws: WebSocket | null = null;
  let percobaan = 0;
  let waktuSambung: ReturnType<typeof setTimeout> | null = null;
  let jamDetak: ReturnType<typeof setInterval> | null = null;
  let gerakTerakhir = Date.now();
  let dicatatPada = 0;
  let terkirim: "online" | "away" | null = null;
  let pernahTersambung = false;

  const kirim = (paksa = false) => {
    const status = statusTab(gerakTerakhir, Date.now(), document.visibilityState === "visible");
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    if (!paksa && status === terkirim) return;
    terkirim = status;
    ws.send(JSON.stringify({ tipe: "hadir", status }));
  };

  const gerak = () => {
    const sekarang = Date.now();
    if (sekarang - dicatatPada < JEDA_CATAT_GERAK_MS) return;
    dicatatPada = sekarang;
    gerakTerakhir = sekarang;
    // Kembali dari away diumumkan seketika, bukan menunggu detak berikutnya.
    if (terkirim === "away") kirim();
  };
  const terlihat = () => {
    if (document.visibilityState === "visible") gerakTerakhir = Date.now();
    kirim();
  };

  const sambung = () => {
    if (!hidup) return;
    let url: URL;
    try {
      url = new URL(LIVE_BASE_URL?.trim() || window.location.origin);
      url.protocol = window.location.protocol === "https:" ? "wss" : "ws";
      url.pathname = `${LIVE_BASE_PATH}/obrolan/`;
      url.searchParams.set("workspace", slug);
      url.searchParams.set("mode", "kehadiran");
    } catch {
      return;
    }
    const soket = new WebSocket(url.toString());
    ws = soket;
    soket.addEventListener("open", () => {
      // Tersambung lagi sesudah putus: sinyal yang lewat selama itu hilang, jadi kejar.
      if (pernahTersambung) void segarkanSemua();
      pernahTersambung = true;
      percobaan = 0;
      terkirim = null;
      soketTerbuka = soket;
      kabari();
      kirim(true);
    });
    soket.addEventListener("message", (ev) => {
      try {
        const pesan = JSON.parse(ev.data as string) as
          | TPesanKehadiran
          | { tipe: "panggilan" }
          | ({ tipe: "data" } & TSinyalData);
        if (pesan.tipe === "data") {
          // Sinyal "data berubah" (tugas, notifikasi, anggota project). Isinya cuma petunjuk.
          const { tipe: _tipe, ...sinyal } = pesan;
          terimaSinyalData(sinyal);
          return;
        }
        if (pesan.tipe === "panggilan") {
          // Satu pendengar yang galat tidak boleh menelan sinyal untuk yang lain.
          pendengarPanggilan.forEach((f) => {
            try {
              f(pesan);
            } catch {
              // Diabaikan; lihat di atas.
            }
          });
          return;
        }
        peta = terapkanPesanKehadiran(peta, pesan);
        kabari();
      } catch {
        // Pesan rusak diabaikan; potret berikutnya membetulkannya.
      }
    });
    soket.addEventListener("close", () => {
      ws = null;
      if (soketTerbuka === soket) soketTerbuka = null;
      // Tanpa sambungan, status orang lain tidak bisa dipercaya lagi.
      peta = new Map();
      kabari();
      if (!hidup) return;
      const jeda = TANGGA_SAMBUNG_ULANG[Math.min(percobaan, TANGGA_SAMBUNG_ULANG.length - 1)];
      percobaan += 1;
      waktuSambung = setTimeout(sambung, jeda);
    });
    soket.addEventListener("error", () => soket.close());
  };

  const OPSI_PASIF = { passive: true } as const;
  window.addEventListener("pointerdown", gerak, OPSI_PASIF);
  window.addEventListener("pointermove", gerak, OPSI_PASIF);
  window.addEventListener("keydown", gerak, OPSI_PASIF);
  window.addEventListener("wheel", gerak, OPSI_PASIF);
  window.addEventListener("touchstart", gerak, OPSI_PASIF);
  document.addEventListener("visibilitychange", terlihat);
  // Detak selalu dikirim (paksa): server butuh bukti tab ini masih hidup.
  jamDetak = setInterval(() => kirim(true), SELANG_DETAK_MS);
  sambung();

  return () => {
    hidup = false;
    if (waktuSambung) clearTimeout(waktuSambung);
    if (jamDetak) clearInterval(jamDetak);
    window.removeEventListener("pointerdown", gerak);
    window.removeEventListener("pointermove", gerak);
    window.removeEventListener("keydown", gerak);
    window.removeEventListener("wheel", gerak);
    window.removeEventListener("touchstart", gerak);
    document.removeEventListener("visibilitychange", terlihat);
    ws?.close();
    ws = null;
    soketTerbuka = null;
    peta = new Map();
    kabari();
  };
}

/** Pasang sekali di lapisan workspace. Pemanggil kedua di tab yang sama tidak
 * membuka soket kedua. `aktif` false (modul Chat mati) = tidak menyambung. */
export function useSambungKehadiran(slug: string | undefined, aktif: boolean) {
  useEffect(() => {
    if (!slug || !aktif) return;
    pemakai += 1;
    if (pemakai === 1) hentikan = mulai(slug);
    return () => {
      pemakai -= 1;
      if (pemakai === 0) {
        hentikan?.();
        hentikan = null;
      }
    };
  }, [slug, aktif]);
}
