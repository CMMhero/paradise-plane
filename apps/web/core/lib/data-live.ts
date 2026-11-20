/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: data hidup tanpa refresh halaman
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu pintu untuk dua hal yang sama maksudnya: menyegarkan ISI layar tanpa
 * memuat ulang halaman.
 *
 * 1. Sinyal dari server. `apps/live` meneruskan sinyal `{ tipe: "data", jenis, ... }`
 *    (lihat `plane/utils/sinyal_data.py`) hanya ke orang yang boleh melihatnya.
 *    Sinyalnya cuma petunjuk (jenis, id project/tugas); isinya TIDAK ikut, jadi
 *    layar menarik ulang lewat API biasa yang sudah menegakkan hak lihat.
 * 2. Tombol segarkan di aplikasi, dan jam cadangan saat soket putus.
 *
 * Dua jenis penyegar yang disegarkan bersamaan:
 * - kunci SWR (daftar, dashboard, lencana): `mutate` pada kunci yang cocok.
 * - penyegar terdaftar: layar yang datanya hidup di store MobX (daftar tugas,
 *   detail tugas) mendaftarkan fungsi penariknya lewat `useDaftarPenyegar`.
 *
 * Tiga jaga-jaga yang disengaja:
 * - Rentetan sinyal digabung (jeda `JEDA_GABUNG_MS`, batas tunggu `BATAS_TUNGGU_MS`),
 *   jadi 30 kejadian beruntun menjadi SATU putaran penarikan.
 * - Tab tersembunyi tidak menarik apa pun. Sinyal yang datang saat tersembunyi
 *   disimpan dan, saat tab kembali, hanya kunci yang disebutnya yang ditarik.
 *   Penarikan menyeluruh hanya bila tab tersembunyi sangat lama (`AMBANG_KETINGGALAN_MS`)
 *   atau soket sempat putus. Berpindah tab/jendela sebentar tidak menarik apa pun,
 *   dan semua penarikan otomatis berjalan senyap (tanpa kerangka, tanpa gulir loncat).
 * - Saat orang sedang mengetik, penarikan kunci SWR ditunda sampai fokus lepas,
 *   supaya isian yang belum disimpan tidak tertimpa data baru.
 */

import { useSyncExternalStore } from "react";
import { mutate as mutateSwr } from "swr";

/** Sinyal dari server. Bentuknya sama dengan muatan `siarkan_data`, tanpa `untuk`. */
export type TSinyalData = {
  jenis: string;
  proyek?: string | null;
  tugas?: string | null;
  bidang?: string[];
  aksi?: string;
  oleh?: string | null;
};

export const JENIS_TUGAS = "tugas";
export const JENIS_NOTIFIKASI = "notifikasi";
export const JENIS_ANGGOTA_PROJECT = "anggota-project";

/** Fungsi penarik milik satu layar. Mengembalikan promise supaya tombol segarkan
 * bisa menunggu sampai semuanya selesai. */
type TPenyegar = {
  jenis: readonly string[];
  /** Id project yang diurus layar ini; `null`/kosong = semua project. */
  proyek?: string | null;
  /** Id tugas yang diurus layar ini (detail/peek); kosong = tak dibatasi. */
  tugas?: string | null;
  tarik: () => Promise<unknown> | unknown;
};

/** Gabung sinyal beruntun jadi satu putaran. */
const JEDA_GABUNG_MS = 600;
/** Rentetan sinyal tanpa henti tetap menyegarkan paling lambat sebegini. */
const BATAS_TUNGGU_MS = 3000;
/** Jeda sesudah fokus lepas dari kolom isian sebelum tarikan tertunda jalan. */
const JEDA_SESUDAH_MENGETIK_MS = 1500;
/** Tab yang tersembunyi selama ini dianggap mungkin ketinggalan dan disegarkan senyap sekali saat
 * kembali. 5 menit: peramban mulai membatasi timer tab latar sekitar menit ke-5 dan membekukannya
 * kemudian, jadi sebelum itu soket dan sinyal masih bisa dipercaya. */
export const AMBANG_KETINGGALAN_MS = 5 * 60_000;
/** Soket yang putus sependek ini dianggap tidak melewatkan sinyal; lebih lama dari ini, kejar senyap. */
export const AMBANG_PUTUS_MS = 10_000;
/** Jam cadangan saat soket live putus: kabar tidak bisa dipercaya sampai tersambung lagi. */
export const SELANG_CADANGAN_MS = 120_000;
/** Penarikan menyeluruh otomatis tidak diulang lebih rapat dari ini (pemicu yang bersamaan menyatu). */
const JEDA_MINIMAL_OTOMATIS_MS = 30_000;

const penyegar = new Map<symbol, TPenyegar>();
const pendengar = new Set<() => void>();
let sedangMenyegarkan = 0;
let selesaiTerakhir: number | null = null;

let tertunda: Map<string, TSinyalData[]> = new Map();
let waktuGabung: ReturnType<typeof setTimeout> | null = null;
let mulaiMenunggu = 0;
let swrTertunda: TSinyalData[] = [];
let tersembunyiSejak: number | null = null;
/** Sinyal yang tiba saat tab tersembunyi, satu per (jenis, proyek, tugas). */
const sinyalSaatTersembunyi = new Map<string, TSinyalData>();
/** Soket tersambung ulang saat tab tersembunyi: kejar sekali begitu tab terlihat. */
let perluKejarMenyeluruh = false;
let otomatisBerjalan: Promise<void> | null = null;
let otomatisTerakhir = 0;

const kunciSinyal = (s: TSinyalData) => `${s.jenis}:${s.proyek ?? ""}:${s.tugas ?? ""}`;

/** Jendela sedang dilihat dan berfokus. Hanya saat itu penarikan otomatis boleh jalan. */
export const jendelaAktif = (): boolean =>
  typeof document !== "undefined" && document.visibilityState === "visible" && document.hasFocus();

const kabari = () => pendengar.forEach((f) => f());

const langganan = (f: () => void) => {
  pendengar.add(f);
  return () => {
    pendengar.delete(f);
  };
};

/** Sedang ada putaran penarikan (untuk memutar ikon tombol segarkan). */
export function useSedangMenyegarkan(): boolean {
  return useSyncExternalStore(
    langganan,
    () => sedangMenyegarkan > 0,
    () => false
  );
}

/** Waktu (ms epoch) putaran terakhir selesai, atau `null` kalau belum pernah. */
export function useSelesaiTerakhir(): number | null {
  return useSyncExternalStore(
    langganan,
    () => selesaiTerakhir,
    () => null
  );
}

/** Daftarkan penarik sebuah layar. Mengembalikan fungsi pelepas. */
export function daftarkanPenyegar(p: TPenyegar): () => void {
  const id = Symbol("penyegar");
  penyegar.set(id, p);
  return () => {
    penyegar.delete(id);
  };
}

export function kolomIsianAktif(): boolean {
  if (typeof document === "undefined") return false;
  const el = document.activeElement as HTMLElement | null;
  if (!el) return false;
  if (el.isContentEditable) return true;
  const tag = el.tagName;
  return (
    tag === "TEXTAREA" ||
    (tag === "INPUT" && !["checkbox", "radio", "button", "submit"].includes((el as HTMLInputElement).type))
  );
}

const teksKunci = (kunci: unknown): string => {
  try {
    return typeof kunci === "string" ? kunci : JSON.stringify(kunci);
  } catch {
    return "";
  }
};

/** Kunci SWR mana yang perlu ditarik ulang untuk kumpulan sinyal ini. */
function kunciCocok(kunci: unknown, sinyal: TSinyalData[]): boolean {
  const teks = teksKunci(kunci);
  if (!teks) return false;
  const huruf = teks.toLowerCase();
  return sinyal.some((s) => {
    if (s.proyek && teks.includes(s.proyek)) return true;
    if (s.tugas && teks.includes(s.tugas)) return true;
    if (huruf.includes("attention")) return s.jenis === JENIS_TUGAS || s.jenis === JENIS_NOTIFIKASI;
    // Membaca obrolan di satu tab menurunkan lencana dan baris daftar di tab lain.
    if (s.jenis === JENIS_NOTIFIKASI)
      return (
        huruf.includes("notification") ||
        huruf.includes("inbox") ||
        huruf.startsWith("chat_belum_dibaca") ||
        huruf.startsWith("chat_percakapan_") ||
        huruf.startsWith("chat_kanal_")
      );
    if (s.jenis === JENIS_ANGGOTA_PROJECT) return huruf.includes("member") || huruf.includes("project");
    return false;
  });
}

const kunciDeskripsi = (kunci: unknown) => teksKunci(kunci).toLowerCase().includes("description");

/** Jalankan penyegar terdaftar yang peduli pada sinyal ini, atau semuanya (`sinyal` kosong). */
async function jalankanPenyegar(sinyal: TSinyalData[] | null): Promise<void> {
  const tugasLari: Promise<unknown>[] = [];
  for (const p of penyegar.values()) {
    const peduli =
      sinyal === null ||
      sinyal.some(
        (s) =>
          p.jenis.includes(s.jenis) &&
          (!p.proyek || !s.proyek || p.proyek === s.proyek) &&
          (!p.tugas || !s.tugas || p.tugas === s.tugas)
      );
    if (!peduli) continue;
    try {
      tugasLari.push(Promise.resolve(p.tarik()).catch(() => undefined));
    } catch {
      // Satu penarik yang galat tidak boleh menggagalkan yang lain.
    }
  }
  await Promise.all(tugasLari);
}

async function putaran(sinyal: TSinyalData[] | null, termasukSwr: boolean): Promise<void> {
  sedangMenyegarkan += 1;
  kabari();
  try {
    const kerja: Promise<unknown>[] = [jalankanPenyegar(sinyal)];
    if (termasukSwr) {
      const mengetik = kolomIsianAktif();
      if (mengetik && sinyal !== null) {
        // Tunda tarikan SWR sampai fokus lepas; lihat catatan modul.
        swrTertunda.push(...sinyal);
      } else {
        kerja.push(
          mutateSwr((kunci) => {
            if (sinyal === null) return mengetik ? !kunciDeskripsi(kunci) : true;
            return kunciCocok(kunci, sinyal);
          })
        );
      }
    }
    await Promise.all(kerja);
  } finally {
    sedangMenyegarkan -= 1;
    selesaiTerakhir = Date.now();
    kabari();
  }
}

function lepasGabungan() {
  waktuGabung = null;
  mulaiMenunggu = 0;
  const kumpulan = [...tertunda.values()].flat();
  tertunda = new Map();
  if (kumpulan.length === 0) return;
  if (typeof document !== "undefined" && document.visibilityState === "hidden") {
    // Disimpan; saat tab terlihat lagi hanya kunci yang disebut sinyal yang ditarik.
    kumpulan.forEach((s) => sinyalSaatTersembunyi.set(kunciSinyal(s), s));
    return;
  }
  void putaran(kumpulan, true);
}

/** Terima satu sinyal dari server. Dipanggil lapisan soket. */
export function terimaSinyalData(sinyal: TSinyalData): void {
  if (!sinyal || typeof sinyal.jenis !== "string") return;
  const kunci = kunciSinyal(sinyal);
  const daftar = tertunda.get(kunci) ?? [];
  daftar.push(sinyal);
  tertunda.set(kunci, daftar);
  const sekarang = Date.now();
  if (!mulaiMenunggu) mulaiMenunggu = sekarang;
  if (waktuGabung) clearTimeout(waktuGabung);
  const sisa = Math.max(0, BATAS_TUNGGU_MS - (sekarang - mulaiMenunggu));
  waktuGabung = setTimeout(lepasGabungan, Math.min(JEDA_GABUNG_MS, sisa));
}

/** Segarkan SEMUA isi layar: tombol segarkan, soket tersambung ulang, jam cadangan. */
export function segarkanSemua(): Promise<void> {
  return putaran(null, true);
}

/**
 * Penarikan menyeluruh OTOMATIS (tab lama tersembunyi, soket putus, jam cadangan).
 * Pemicu yang datang bersamaan menyatu ke satu putaran, dan putaran berikutnya
 * baru boleh jalan setelah `JEDA_MINIMAL_OTOMATIS_MS`. Tombol segarkan tidak lewat sini.
 */
export function segarkanSenyap(): Promise<void> {
  if (otomatisBerjalan) return otomatisBerjalan;
  if (Date.now() - otomatisTerakhir < JEDA_MINIMAL_OTOMATIS_MS) return Promise.resolve();
  otomatisTerakhir = Date.now();
  otomatisBerjalan = segarkanSemua().finally(() => {
    otomatisBerjalan = null;
  });
  return otomatisBerjalan;
}

/** Soket tersambung ulang sesudah putus `terputusMs`. Sinyal selama itu hilang, jadi kejar senyap. */
export function saatSoketTersambungUlang(terputusMs: number): void {
  if (terputusMs < AMBANG_PUTUS_MS) return;
  if (typeof document !== "undefined" && document.visibilityState === "hidden") {
    perluKejarMenyeluruh = true;
    return;
  }
  void segarkanSenyap();
}

/** Tab terlihat lagi: tarik apa yang memang perlu, senyap, dan tidak lebih. */
function kejarSaatTerlihat(): void {
  const lama = tersembunyiSejak === null ? 0 : Date.now() - tersembunyiSejak;
  tersembunyiSejak = null;
  const menyeluruh = perluKejarMenyeluruh || lama >= AMBANG_KETINGGALAN_MS;
  perluKejarMenyeluruh = false;
  const sinyal = [...sinyalSaatTersembunyi.values()];
  sinyalSaatTersembunyi.clear();
  if (menyeluruh) {
    void segarkanSenyap();
  } else if (sinyal.length > 0) {
    void putaran(sinyal, true);
  }
}

function saatVisibilitas() {
  if (document.visibilityState === "hidden") {
    tersembunyiSejak ??= Date.now();
  } else {
    kejarSaatTerlihat();
  }
}

/** Pasang pendengar tingkat dokumen. Dipanggil sekali oleh lapisan workspace. */
export function pasangPenjagaData(): () => void {
  let waktuMengetik: ReturnType<typeof setTimeout> | null = null;
  const saatFokusLepas = () => {
    if (swrTertunda.length === 0) return;
    if (waktuMengetik) clearTimeout(waktuMengetik);
    waktuMengetik = setTimeout(() => {
      if (kolomIsianAktif() || swrTertunda.length === 0) return;
      const sinyal = swrTertunda;
      swrTertunda = [];
      void mutateSwr((kunci) => kunciCocok(kunci, sinyal));
    }, JEDA_SESUDAH_MENGETIK_MS);
  };
  document.addEventListener("visibilitychange", saatVisibilitas);
  document.addEventListener("focusout", saatFokusLepas);
  return () => {
    document.removeEventListener("visibilitychange", saatVisibilitas);
    document.removeEventListener("focusout", saatFokusLepas);
    if (waktuMengetik) clearTimeout(waktuMengetik);
    if (waktuGabung) clearTimeout(waktuGabung);
    waktuGabung = null;
    tertunda = new Map();
  };
}
