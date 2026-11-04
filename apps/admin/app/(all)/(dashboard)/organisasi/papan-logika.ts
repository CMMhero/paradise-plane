/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: logika papan seret-lepas organisasi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Modul murni (tanpa React). Satu seretan atau satu pilihan menu diterjemahkan
 * jadi satu badan POST /api/instances/hierarki/ plus posisi sesudahnya, supaya
 * tampilan bisa diperbarui optimis lalu dibatalkan kalau server menolak.
 *
 * Aturan KEP-76 yang dicerminkan di sini (penegaknya tetap server):
 * - Dari daftar People = TAMBAH satu tempat (`departemen_id` / `divisi_id`).
 * - Dari departemen ke departemen lain (atau divisi ke divisi) = PINDAH: satu
 *   POST `departemen_ids` / `divisi_ids` pengganti, jadi atomik. Ctrl/Alt saat
 *   melepas = tambah.
 * - Diseret kembali ke daftar People = CABUT dari tempat asalnya saja. Jenjang
 *   tetap, KECUALI supervisor/manager yang jadi tanpa tempat sama sekali: jatuh ke
 *   Staf (KEP-86, cermin `tingkat_sesudah_cabut` di server).
 * - Memimpin divisi menaikkan jenjang ke Manager; turun di bawah Manager
 *   melepas divisinya. Direktur tidak ditempatkan (KEP-23, sama dengan
 *   `calonAnggota`).
 */

import {
  TINGKAT_DIREKTUR,
  TINGKAT_MANAGER,
  TINGKAT_MEMBER,
  TINGKAT_SUPERVISOR,
  type TAnggotaHierarki,
  type THierarkiResponse,
  type TOrangOrganisasi,
  type TPohonOrganisasi,
  type TSetJabatan,
} from "@plane/services";
import type { TGodmodeStrings } from "@/app/i18n/godmode";

export const LAJUR_JENJANG = [TINGKAT_MEMBER, TINGKAT_SUPERVISOR, TINGKAT_MANAGER, TINGKAT_DIREKTUR] as const;

/** Akun terhapus (KEP-50) tidak boleh muncul atau diseret. */
export const akunTerhapus = (email: string): boolean => email.toLowerCase().endsWith("@deleted.local");

export type TAsal = { jenis: "departemen" | "divisi"; id: string };
export type TTujuan =
  | { jenis: "departemen"; id: string; tingkat?: number }
  | { jenis: "divisi"; id: string }
  | { jenis: "jenjang"; tingkat: number }
  /** Daftar People: lepas dari tempat asal seretan. */
  | { jenis: "lepas" };

const KUNCI_SERET = "paradiseOrgOrang";
const KUNCI_TUJUAN = "paradiseOrgTujuan";

export type TDataSeret = { orangId: string; asal?: TAsal };

export const dataSeret = (d: TDataSeret): Record<string, unknown> => ({ [KUNCI_SERET]: d });
export const bacaSeret = (data: Record<string | symbol, unknown>): TDataSeret | null => {
  const isi = data[KUNCI_SERET];
  return isi && typeof isi === "object" && "orangId" in isi ? (isi as TDataSeret) : null;
};
export const dataTujuan = (t: TTujuan): Record<string, unknown> => ({ [KUNCI_TUJUAN]: t });
export const bacaTujuan = (data: Record<string | symbol, unknown>): TTujuan | null => {
  const isi = data[KUNCI_TUJUAN];
  return isi && typeof isi === "object" && "jenis" in isi ? (isi as TTujuan) : null;
};

/** Ctrl (Windows/Linux) atau Alt/Option (Mac) = salin, bukan pindah. */
export const tombolSalin = (input: { ctrlKey: boolean; altKey: boolean; metaKey: boolean }): boolean =>
  input.ctrlKey || input.altKey || input.metaKey;

export type TPosisi = { tingkat: number; departemen_ids: string[]; divisi_ids: string[] };

export const posisiDari = (o: TAnggotaHierarki): TPosisi => ({
  tingkat: o.tingkat ?? TINGKAT_MEMBER,
  departemen_ids: o.departemen_ids ?? (o.departemen_id ? [o.departemen_id] : []),
  divisi_ids: (o.tingkat ?? 0) >= TINGKAT_MANAGER ? (o.divisi_ids ?? (o.divisi_id ? [o.divisi_id] : [])) : [],
});

/** Mode yang akan terjadi kalau dilepas di `tujuan` sekarang (untuk label sorotan). */
export const modeLepas = (
  asal: TAsal | undefined,
  tujuan: TTujuan,
  salin: boolean
): "tambah" | "pindah" | "pimpin" | "jenjang" | "lepas" | null => {
  if (tujuan.jenis === "jenjang") return "jenjang";
  // Chip dari daftar People sendiri tidak punya tempat untuk dilepas.
  if (tujuan.jenis === "lepas") return asal ? "lepas" : null;
  const pindah = !salin && asal?.jenis === tujuan.jenis && asal.id !== tujuan.id;
  if (pindah) return "pindah";
  return tujuan.jenis === "divisi" ? "pimpin" : "tambah";
};

export type TRencana =
  | {
      hasil: "kirim";
      badan: Omit<TSetJabatan, "member_id">;
      sesudah: TPosisi;
      mode: NonNullable<ReturnType<typeof modeLepas>>;
    }
  | { hasil: "direktur" }
  | { hasil: "sudah" };

const tanpa = (daftar: string[], id: string | undefined) => daftar.filter((x) => x !== id);
const dengan = (daftar: string[], id: string) => (daftar.includes(id) ? daftar : [...daftar, id]);

export function rencanakan(o: TAnggotaHierarki, asal: TAsal | undefined, tujuan: TTujuan, salin: boolean): TRencana {
  if (tujuan.jenis === "lepas") return asal ? rencanaCabut(o, asal) : { hasil: "sudah" };
  const awal = posisiDari(o);
  const mode = modeLepas(asal, tujuan, salin) ?? "tambah";

  if (tujuan.jenis === "jenjang") {
    if (tujuan.tingkat === awal.tingkat && o.tingkat !== null && !o.tingkat_bawaan) return { hasil: "sudah" };
    return {
      hasil: "kirim",
      mode,
      badan: { tingkat: tujuan.tingkat },
      sesudah: {
        ...awal,
        tingkat: tujuan.tingkat,
        divisi_ids: tujuan.tingkat >= TINGKAT_MANAGER ? awal.divisi_ids : [],
      },
    };
  }

  if (awal.tingkat >= TINGKAT_DIREKTUR) return { hasil: "direktur" };

  if (tujuan.jenis === "departemen") {
    const deps = dengan(mode === "pindah" ? tanpa(awal.departemen_ids, asal?.id) : awal.departemen_ids, tujuan.id);
    // Lajur Supervisor/Staf di dalam departemen tidak pernah MENURUNKAN manager:
    // itu akan melepas divisinya diam-diam. Menurunkan = lajur Levels di atas.
    const ganti = tujuan.tingkat !== undefined && tujuan.tingkat !== awal.tingkat && awal.tingkat < TINGKAT_MANAGER;
    if (!ganti && deps.length === awal.departemen_ids.length && deps.every((d) => awal.departemen_ids.includes(d)))
      return { hasil: "sudah" };
    const tingkat = ganti && tujuan.tingkat !== undefined ? tujuan.tingkat : awal.tingkat;
    const badan: Omit<TSetJabatan, "member_id"> =
      mode === "pindah" ? { departemen_ids: deps } : { departemen_id: tujuan.id };
    if (ganti) badan.tingkat = tingkat;
    return {
      hasil: "kirim",
      mode,
      badan,
      sesudah: { tingkat, departemen_ids: deps, divisi_ids: tingkat >= TINGKAT_MANAGER ? awal.divisi_ids : [] },
    };
  }

  const divs = dengan(mode === "pindah" ? tanpa(awal.divisi_ids, asal?.id) : awal.divisi_ids, tujuan.id);
  if (divs.length === awal.divisi_ids.length && divs.every((d) => awal.divisi_ids.includes(d)))
    return { hasil: "sudah" };
  return {
    hasil: "kirim",
    mode,
    badan: mode === "pindah" ? { divisi_ids: divs } : { divisi_id: tujuan.id },
    sesudah: { ...awal, tingkat: Math.max(awal.tingkat, TINGKAT_MANAGER), divisi_ids: divs },
  };
}

/**
 * Jenjang sesudah tempat dicabut, cermin `plane/db/penempatan.tingkat_sesudah_cabut`:
 * supervisor/manager tanpa satu tempat pun tersisa jatuh ke Staf; direktur tidak.
 */
export const tingkatSesudahCabut = (tingkat: number, sisa: Pick<TPosisi, "departemen_ids" | "divisi_ids">): number =>
  tingkat >= TINGKAT_SUPERVISOR &&
  tingkat < TINGKAT_DIREKTUR &&
  sisa.departemen_ids.length === 0 &&
  sisa.divisi_ids.length === 0
    ? TINGKAT_MEMBER
    : tingkat;

/** Lepas dari satu tempat saja (menu "Remove from" / seret ke People). */
export function rencanaCabut(o: TAnggotaHierarki, asal: TAsal): Extract<TRencana, { hasil: "kirim" }> {
  const awal = posisiDari(o);
  const sisa =
    asal.jenis === "departemen"
      ? { ...awal, departemen_ids: tanpa(awal.departemen_ids, asal.id) }
      : { ...awal, divisi_ids: tanpa(awal.divisi_ids, asal.id) };
  const sesudah = { ...sisa, tingkat: tingkatSesudahCabut(awal.tingkat, sisa) };
  return {
    hasil: "kirim",
    mode: "lepas",
    badan:
      asal.jenis === "departemen" ? { departemen_ids: sesudah.departemen_ids } : { divisi_ids: sesudah.divisi_ids },
    sesudah,
  };
}

/**
 * Badan POST yang mengembalikan orang ke posisi sebelum perubahan (tombol Undo).
 * Orang yang dulu sama sekali tanpa baris jabatan dikembalikan dengan
 * `tingkat: null` (= cabut jenjang + semua tempat), bukan dijadikan Staf eksplisit.
 */
export function badanPulihkan(o: TAnggotaHierarki): Omit<TSetJabatan, "member_id"> {
  const awal = posisiDari(o);
  const tanpaBaris =
    (o.tingkat === null || o.tingkat_bawaan === true) &&
    awal.departemen_ids.length === 0 &&
    awal.divisi_ids.length === 0;
  if (tanpaBaris) return { tingkat: null };
  return { tingkat: awal.tingkat, departemen_ids: awal.departemen_ids, divisi_ids: awal.divisi_ids };
}

// ---------------------------------------------------------------------------
// Pembaruan optimis cache SWR
// ---------------------------------------------------------------------------

export function terapkanKeHierarki(data: THierarkiResponse, orangId: string, p: TPosisi): THierarkiResponse {
  return {
    ...data,
    anggota: data.anggota.map((a) =>
      a.id === orangId
        ? {
            ...a,
            tingkat: p.tingkat,
            tingkat_bawaan: false,
            departemen_ids: p.departemen_ids,
            divisi_ids: p.divisi_ids,
            departemen_id: p.departemen_ids[0] ?? null,
            divisi_id: p.divisi_ids[0] ?? null,
          }
        : a
    ),
  };
}

export function terapkanKePohon(pohon: TPohonOrganisasi, o: TAnggotaHierarki, p: TPosisi): TPohonOrganisasi {
  const entri: TOrangOrganisasi = {
    id: o.id,
    nama: o.display_name,
    email: o.email,
    tingkat: p.tingkat,
    tingkat_nama: null,
  };
  return {
    ...pohon,
    divisi: pohon.divisi.map((v) => ({
      ...v,
      manager: [
        ...v.manager.filter((m) => m.id !== o.id),
        ...(p.tingkat >= TINGKAT_MANAGER && p.divisi_ids.includes(v.id) ? [entri] : []),
      ],
      departemen: v.departemen.map((d) => {
        const anggota = [
          ...d.anggota.filter((a) => a.id !== o.id),
          ...(p.departemen_ids.includes(d.id) ? [entri] : []),
        ];
        return { ...d, anggota, jumlah_orang: anggota.length };
      }),
    })),
  };
}

/** Nama jenjang. Fungsi biasa (bukan hook): dipanggil di dalam map. */
export const namaJenjang = (t: number, s: TGodmodeStrings): string =>
  t >= TINGKAT_DIREKTUR
    ? s.members.level_director
    : t >= TINGKAT_MANAGER
      ? s.members.level_manager
      : t >= TINGKAT_SUPERVISOR
        ? s.members.level_supervisor
        : s.members.level_staff;

/** Orang tanpa departemen dan tanpa divisi (di bawah Direktur). */
export const belumDitempatkan = (o: TAnggotaHierarki): boolean => {
  const p = posisiDari(o);
  return p.tingkat < TINGKAT_DIREKTUR && p.departemen_ids.length === 0 && p.divisi_ids.length === 0;
};
