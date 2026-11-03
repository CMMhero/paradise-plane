/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: nilai bersama halaman Struktur organisasi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Dipisah dari berkas komponen supaya Fast Refresh tetap hot-swap
 * (alasan yang sama dengan members/constants.ts).
 */

import {
  TINGKAT_DIREKTUR,
  TINGKAT_MANAGER,
  type TAnggotaHierarki,
  type TDepartemenOrganisasi,
  type TDivisiOrganisasi,
  type TOrangOrganisasi,
} from "@plane/services";
import type { TGodmodeStrings } from "@/app/i18n/godmode";

export type TAksiOrganisasi = {
  /** Aksi struktur mengembalikan true kalau berhasil (galat sudah di-toast), supaya modal tahu boleh menutup. */
  buatDivisi: (kode: string, nama: string) => Promise<boolean>;
  ubahDivisi: (id: string, kode: string, nama: string) => Promise<boolean>;
  hapusDivisi: (id: string) => Promise<boolean>;
  buatDepartemen: (divisiId: string, kode: string, nama: string) => Promise<boolean>;
  ubahDepartemen: (
    id: string,
    data: { kode?: string; nama?: string; divisi_id?: string; project_ids?: string[] }
  ) => Promise<boolean>;
  simpanProject: (id: string, projectIds: string[]) => Promise<boolean>;
  hapusDepartemen: (id: string) => Promise<boolean>;
  tempatkan: (
    orang: TAnggotaHierarki,
    tujuan: { departemen_id?: string | null; divisi_id?: string | null }
  ) => Promise<void>;
  /** Ganti SELURUH daftar departemen seseorang (MENGGANTI, bukan tambah-satu). */
  setelEkstra: (orangId: string, departemenIds: string[]) => Promise<void>;
  /** Ganti SELURUH daftar divisi yang dipimpin seseorang (KEP-76). */
  setelDivisi: (orangId: string, divisiIds: string[]) => Promise<void>;
  /** Naik/turun jenjang tanpa memindahkan penempatan (mis. staf <-> supervisor). */
  ubahTingkat: (orang: TAnggotaHierarki, tingkat: number) => Promise<void>;
  /**
   * "Tambah" ke departemen = gabung: yang sudah ditempatkan di departemen lain
   * tetap memegang departemen lamanya (multi-departemen). Pindah murni = cabut
   * di node lama + tambah di node baru.
   */
  tambahKeDepartemen: (orang: TAnggotaHierarki, departemenId: string) => Promise<void>;
};

/**
 * Perintah kelola yang membuka satu modal di tingkat halaman. Bagan, pohon, dan
 * panel detail memakai modal yang sama, jadi aturan buat/ubah/hapus/tambah orang
 * hanya ditulis sekali (kelola.tsx).
 */
export type TPerintahKelola =
  | { jenis: "buat-divisi" }
  | { jenis: "ubah-divisi"; id: string }
  | { jenis: "hapus-divisi"; id: string }
  | { jenis: "tambah-manager"; id: string }
  | { jenis: "buat-departemen"; divisiId: string }
  | { jenis: "ubah-departemen"; id: string }
  | { jenis: "hapus-departemen"; id: string }
  | { jenis: "setelan-departemen"; id: string }
  | { jenis: "tambah-anggota"; id: string };

export type TKelola = (perintah: TPerintahKelola) => void;

/**
 * Calon manager divisi: siapa pun di bawah Direktur yang belum jadi manager di
 * sini. Penempatan ke divisi menaikkan jenjang ke Manager, jadi supervisor/staf
 * ikut jadi calon (tak perlu bolak-balik ke halaman Member).
 */
export const calonManager = (orang: TAnggotaHierarki[], divisi: TDivisiOrganisasi): TAnggotaHierarki[] => {
  const sudah = new Set(divisi.manager.map((m) => m.id));
  return orang.filter((o) => o.tingkat !== null && o.tingkat < TINGKAT_DIREKTUR && !sudah.has(o.id));
};

/**
 * Calon anggota departemen: semua jenjang di bawah Direktur yang belum di sini
 * (KEP-76: manager boleh duduk di departemen di luar divisinya). Menambah tidak
 * memindahkan penempatan lamanya.
 */
export const calonAnggota = (orang: TAnggotaHierarki[], dep: TDepartemenOrganisasi): TAnggotaHierarki[] => {
  const sudah = new Set(dep.anggota.map((a) => a.id));
  return orang.filter((o) => (o.tingkat === null || o.tingkat < TINGKAT_DIREKTUR) && !sudah.has(o.id));
};

/** Departemen + divisi orang ini sekarang (semua barisnya), untuk penanda di daftar calon. */
export const tempatOrang = (
  o: TAnggotaHierarki,
  namaDepartemen: Record<string, string>,
  namaDivisi: Record<string, string>
): string[] => {
  const dep = o.departemen_ids ?? (o.departemen_id ? [o.departemen_id] : []);
  const div =
    o.tingkat !== null && o.tingkat >= TINGKAT_MANAGER ? (o.divisi_ids ?? (o.divisi_id ? [o.divisi_id] : [])) : [];
  return [...div.map((id) => namaDivisi[id]), ...dep.map((id) => namaDepartemen[id])].filter(
    (n): n is string => typeof n === "string" && n.length > 0
  );
};

/** "also in Finance, IT" untuk daftar calon. Fungsi biasa (bukan hook) karena dipanggil di dalam map. */
export const asalOrang = (
  o: TAnggotaHierarki,
  namaDepartemen: Record<string, string>,
  namaDivisi: Record<string, string>,
  s: TGodmodeStrings,
  fill: (template: string, vars: Record<string, string | number>) => string
): string => {
  const tempat = tempatOrang(o, namaDepartemen, namaDivisi);
  if (tempat.length > 0) return fill(s.org.moved_from_bare, { from: tempat.join(", ") });
  return o.tingkat === null ? s.org.not_yet_leveled : "";
};

export const cariDepartemen = (
  divisi: TDivisiOrganisasi[],
  id: string
): { dep: TDepartemenOrganisasi; divisi: TDivisiOrganisasi } | undefined => {
  for (const v of divisi) {
    const dep = v.departemen.find((d) => d.id === id);
    if (dep) return { dep, divisi: v };
  }
  return undefined;
};

/** Node yang sedang dibuka di panel kanan. */
export type TPilihan =
  | { jenis: "ringkasan" }
  | { jenis: "divisi"; id: string }
  | { jenis: "departemen"; id: string }
  | { jenis: "belum" }
  | { jenis: "lama" };

export const samaPilihan = (a: TPilihan, b: TPilihan): boolean =>
  a.jenis === b.jenis && ("id" in a ? a.id : "") === ("id" in b ? b.id : "");

/** Cocokkan orang dengan kata cari global (nama/email). `q` sudah huruf kecil. */
export const cocokOrang = (q: string, o: Pick<TOrangOrganisasi, "nama" | "email">): boolean =>
  !q || `${o.nama} ${o.email}`.toLowerCase().includes(q);

export const cocokTeks = (q: string, ...teks: string[]): boolean => !q || teks.join(" ").toLowerCase().includes(q);

/** Departemen yang lolos cari: namanya cocok, atau salah satu orangnya cocok. */
export const depCocok = (q: string, d: TDepartemenOrganisasi): boolean =>
  cocokTeks(q, d.nama, d.kode) || d.anggota.some((a) => cocokOrang(q, a));

export const divisiCocok = (q: string, v: TDivisiOrganisasi): boolean =>
  cocokTeks(q, v.nama, v.kode) || v.manager.some((m) => cocokOrang(q, m)) || v.departemen.some((d) => depCocok(q, d));

const KODE_MAKS = 20;
/** Kata sambung yang tak ikut jadi huruf kode ("Research and Development" -> RD). */
const KATA_SAMBUNG = new Set(["and", "of", "the", "dan", "&", "untuk", "for"]);

/**
 * Kode usulan dari nama: banyak kata -> huruf depan tiap kata ("Human Resources"
 * -> HR), satu kata -> tiga huruf pertama ("Finance" -> FIN). Bentrok dengan kode
 * yang sudah ada diberi angka (FIN2, FIN3) supaya simpan tidak ditolak
 * constraint unik backend. Hanya huruf/angka, huruf besar, maks 20.
 */
export const kodeDariNama = (nama: string, terpakai: Iterable<string> = []): string => {
  const kata = nama
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .split(/\s+/)
    .filter((k) => k && !KATA_SAMBUNG.has(k.toLowerCase()));
  if (kata.length === 0) return "";
  const dasar = (kata.length === 1 ? kata[0].slice(0, 3) : kata.map((k) => k[0]).join(""))
    .toUpperCase()
    .slice(0, KODE_MAKS);
  const ada = new Set([...terpakai].map((k) => k.toUpperCase()));
  if (!ada.has(dasar)) return dasar;
  for (let n = 2; ; n++) {
    const calon = `${dasar.slice(0, KODE_MAKS - String(n).length)}${n}`;
    if (!ada.has(calon)) return calon;
  }
};
