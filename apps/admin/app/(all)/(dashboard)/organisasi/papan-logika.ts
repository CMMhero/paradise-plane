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
 * - Dari tempat mana pun di struktur ke tempat LAIN = PINDAH, termasuk lintas
 *   jenis (departemen ke divisi dan sebaliknya, 5 Nov 2026): satu POST
 *   `departemen_ids` / `divisi_ids` pengganti, jadi atomik. Ctrl/Alt saat
 *   melepas = tambah. Dari People (dan lajur Levels, yang bukan tempat) = tambah.
 * - Diseret kembali ke daftar People = CABUT dari tempat asalnya saja. Jenjang
 *   tetap, KECUALI supervisor/manager yang jadi tanpa tempat sama sekali: jatuh ke
 *   Staf (KEP-86, cermin `tingkat_sesudah_cabut` di server).
 * - Memimpin divisi menaikkan jenjang ke Manager; turun di bawah Manager
 *   melepas divisinya. Direktur tidak ditempatkan (KEP-23, sama dengan
 *   `calonAnggota`).
 *
 * KEP-93 (peran per tempat): tidak ada "manager departemen". Manager yang
 * diseret ke departemen di divisi yang ia pimpin = ditolak (`divisi-sendiri`);
 * ke departemen divisi lain = minta konfirmasi peran di sana (`peran`: Staf atau
 * Supervisor). Jenjang Manager-nya tidak berubah.
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

/** `direktur`: chip direktur tanpa tempat; diseret ke People = turun ke Staf. */
export type TDataSeret = { orangId: string; asal?: TAsal; direktur?: boolean };

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

export type TPosisi = {
  tingkat: number;
  departemen_ids: string[];
  divisi_ids: string[];
  /** KEP-93: peran per departemen (Staf/Supervisor). Di bawah Manager = jenjangnya. */
  peran_departemen: Record<string, number>;
};

/** Peran di departemen untuk jenjang `tingkat` (cermin `setel_penempatan`). */
/**
 * Peran per departemen, cermin `setel_penempatan` (KEP-93): yang diminta, lalu
 * (jenjang dipilih eksplisit di bawah Manager = `seragam`) jenjangnya, lalu peran
 * lama, lalu jenjangnya. Selalu Staf atau Supervisor, tidak pernah Manager.
 */
const susunPeran = (
  tingkat: number,
  deps: string[],
  lama: Record<string, number>,
  diminta: Record<string, number> = {},
  seragam = false
): Record<string, number> =>
  Object.fromEntries(
    deps.map((d) => {
      const nilai = diminta[d] ?? (seragam && tingkat < TINGKAT_MANAGER ? tingkat : (lama[d] ?? tingkat));
      return [d, Math.min(nilai, TINGKAT_SUPERVISOR)];
    })
  );

/** Di bawah Manager jenjang orangnya = peran tertingginya di departemen mana pun. */
const tingkatTurunan = (tingkat: number, peran: Record<string, number>): number => {
  const nilai = Object.values(peran);
  return tingkat < TINGKAT_MANAGER && nilai.length > 0 ? Math.max(...nilai) : tingkat;
};

export const posisiDari = (o: TAnggotaHierarki): TPosisi => {
  const tingkat = o.tingkat ?? TINGKAT_MEMBER;
  const departemen_ids = o.departemen_ids ?? (o.departemen_id ? [o.departemen_id] : []);
  return {
    tingkat,
    departemen_ids,
    divisi_ids: tingkat >= TINGKAT_MANAGER ? (o.divisi_ids ?? (o.divisi_id ? [o.divisi_id] : [])) : [],
    peran_departemen: susunPeran(tingkat, departemen_ids, o.peran_departemen ?? {}),
  };
};

/** Divisi induk satu departemen; dari pohon organisasi. */
export type TDivisiDari = (departemenId: string) => string | undefined;

/** Mode yang akan terjadi kalau dilepas di `tujuan` sekarang (untuk label sorotan). */
export const modeLepas = (
  asal: TAsal | undefined,
  tujuan: TTujuan,
  salin: boolean
): "tambah" | "pindah" | "pimpin" | "jenjang" | "lepas" | null => {
  if (tujuan.jenis === "jenjang") return "jenjang";
  // Chip dari daftar People sendiri tidak punya tempat untuk dilepas.
  if (tujuan.jenis === "lepas") return asal ? "lepas" : null;
  // Dari struktur = pindah, juga lintas jenis. Dilepas di tempatnya sendiri
  // (mis. lajur lain di departemen yang sama) bukan pindah: itu ganti peran.
  const pindah = !salin && asal !== undefined && !(asal.jenis === tujuan.jenis && asal.id === tujuan.id);
  if (pindah) return "pindah";
  return tujuan.jenis === "divisi" ? "pimpin" : "tambah";
};

export type TRencanaKirim = {
  hasil: "kirim";
  badan: Omit<TSetJabatan, "member_id">;
  sesudah: TPosisi;
  mode: NonNullable<ReturnType<typeof modeLepas>>;
  /** Divisi yang berhenti ia pimpin karena dipindah ke departemennya (untuk toast). */
  turunDari?: string;
  /** Direktur yang diturunkan karena ditempatkan (untuk toast). */
  turunDirektur?: boolean;
};

export type TRencana =
  | TRencanaKirim
  | { hasil: "sudah" }
  /** KEP-93: manager ke departemen di divisi yang ia pimpin. */
  | { hasil: "divisi-sendiri" }
  /** KEP-93: manager ke departemen divisi lain; peran di sana dipilih dulu. */
  | { hasil: "peran"; bawaan: number; pilih: (peran: number) => TRencanaKirim };

const tanpa = (daftar: string[], id: string | undefined) => daftar.filter((x) => x !== id);
const dengan = (daftar: string[], id: string) => (daftar.includes(id) ? daftar : [...daftar, id]);

export function rencanakan(
  o: TAnggotaHierarki,
  asal: TAsal | undefined,
  tujuan: TTujuan,
  salin: boolean,
  divisiDari: TDivisiDari
): TRencana {
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
        peran_departemen: susunPeran(tujuan.tingkat, awal.departemen_ids, awal.peran_departemen, {}, true),
      },
    };
  }

  if (awal.tingkat >= TINGKAT_DIREKTUR) return rencanaTurunDirektur(awal, tujuan);

  if (tujuan.jenis === "departemen" && awal.tingkat >= TINGKAT_MANAGER)
    return rencanaManagerKeDepartemen(awal, asal, tujuan, mode, divisiDari);

  if (tujuan.jenis === "departemen") {
    // KEP-93: lajur Supervisor/Staf = peran orang itu DI departemen ini saja,
    // bukan jenjangnya di mana-mana. Jenjangnya mengikuti peran tertinggi.
    const deps = dengan(mode === "pindah" ? tanpa(awal.departemen_ids, asal?.id) : awal.departemen_ids, tujuan.id);
    const lajur =
      tujuan.tingkat === TINGKAT_MEMBER || tujuan.tingkat === TINGKAT_SUPERVISOR ? tujuan.tingkat : undefined;
    const peranLama = awal.peran_departemen[tujuan.id];
    const gantiPeran = lajur !== undefined && lajur !== peranLama;
    const tempatSama = deps.length === awal.departemen_ids.length && deps.every((d) => awal.departemen_ids.includes(d));
    if (!gantiPeran && tempatSama) return { hasil: "sudah" };
    const diminta = lajur !== undefined ? { [tujuan.id]: lajur } : {};
    const peran = susunPeran(awal.tingkat, deps, awal.peran_departemen, diminta);
    const badan: Omit<TSetJabatan, "member_id"> = {
      ...(tempatSama ? {} : mode === "pindah" ? { departemen_ids: deps } : { departemen_id: tujuan.id }),
      ...(lajur !== undefined ? { peran_departemen: diminta } : {}),
    };
    return {
      hasil: "kirim",
      mode: tempatSama ? "jenjang" : mode,
      badan,
      sesudah: { ...awal, tingkat: tingkatTurunan(awal.tingkat, peran), departemen_ids: deps, peran_departemen: peran },
    };
  }

  const divs = dengan(mode === "pindah" ? tanpa(awal.divisi_ids, asal?.id) : awal.divisi_ids, tujuan.id);
  // Pindah dari departemen = keluar dari departemen itu.
  const keluarDep = mode === "pindah" && asal?.jenis === "departemen" ? asal.id : undefined;
  if (!keluarDep && divs.length === awal.divisi_ids.length && divs.every((d) => awal.divisi_ids.includes(d)))
    return { hasil: "sudah" };
  const tingkat = Math.max(awal.tingkat, TINGKAT_MANAGER);
  const depsAwal = tanpa(awal.departemen_ids, keluarDep);
  // KEP-93: departemen di dalam divisi yang kini ia pimpin dilepas (server juga).
  const deps = depsAwal.filter((d) => !divs.includes(divisiDari(d) ?? ""));
  return {
    hasil: "kirim",
    mode,
    badan: {
      ...(mode === "pindah" ? { divisi_ids: divs } : { divisi_id: tujuan.id }),
      ...(keluarDep ? { departemen_ids: depsAwal } : {}),
    },
    sesudah: {
      tingkat,
      departemen_ids: deps,
      divisi_ids: divs,
      peran_departemen: susunPeran(tingkat, deps, awal.peran_departemen),
    },
  };
}

/**
 * Manager diseret ke departemen (KEP-93). Divisi yang ia pimpin = ditolak, karena
 * ia sudah memimpin departemen itu lewat divisinya. Divisi lain = ia duduk sebagai
 * Staf atau Supervisor; perannya dipilih di dialog konfirmasi. Lajur tempat ia
 * dilepas (Supervisor/Staf) jadi pilihan bawaan.
 */
function rencanaManagerKeDepartemen(
  awal: TPosisi,
  asal: TAsal | undefined,
  tujuan: Extract<TTujuan, { jenis: "departemen" }>,
  mode: NonNullable<ReturnType<typeof modeLepas>>,
  divisiDari: TDivisiDari
): TRencana {
  const induk = divisiDari(tujuan.id);
  const lajur = tujuan.tingkat === TINGKAT_MEMBER || tujuan.tingkat === TINGKAT_SUPERVISOR ? tujuan.tingkat : undefined;
  if (induk && awal.divisi_ids.includes(induk)) {
    // Dari People (atau Ctrl = tambah): dikunci, tidak ada manager departemen.
    // Dari struktur (pindah): sengaja diturunkan ke departemen divisinya (5 Nov 2026).
    if (mode !== "pindah") return { hasil: "divisi-sendiri" };
    return rencanaTurunKeDepartemen(awal, asal, tujuan, induk, lajur ?? TINGKAT_SUPERVISOR);
  }
  const peranLama = awal.peran_departemen[tujuan.id];
  if (peranLama !== undefined && (lajur === undefined || lajur === peranLama)) return { hasil: "sudah" };
  const deps = dengan(mode === "pindah" ? tanpa(awal.departemen_ids, asal?.id) : awal.departemen_ids, tujuan.id);
  // Pindah dari zona manager divisi lain = berhenti memimpin divisi itu.
  const divs = mode === "pindah" && asal?.jenis === "divisi" ? tanpa(awal.divisi_ids, asal.id) : awal.divisi_ids;
  const lepasDivisi = divs.length !== awal.divisi_ids.length;
  return {
    hasil: "peran",
    bawaan: lajur ?? peranLama ?? TINGKAT_SUPERVISOR,
    pilih: (peran) => ({
      hasil: "kirim",
      mode: peranLama !== undefined ? "jenjang" : mode,
      badan: {
        ...(mode === "pindah" ? { departemen_ids: deps } : { departemen_id: tujuan.id }),
        ...(lepasDivisi ? { divisi_ids: divs } : {}),
        peran_departemen: { [tujuan.id]: peran },
      },
      sesudah: {
        ...awal,
        departemen_ids: deps,
        divisi_ids: divs,
        peran_departemen: susunPeran(awal.tingkat, deps, awal.peran_departemen, { [tujuan.id]: peran }),
      },
    }),
  };
}

/**
 * Direktur ditempatkan = diturunkan (5 Nov 2026, dulu ditolak "Directors are not
 * placed"): ke lajur departemen jadi peran lajur itu, ke divisi jadi Manager-nya.
 * Jenjangnya dikirim eksplisit supaya baris direktur tanpa tempat ikut hilang.
 */
function rencanaTurunDirektur(
  awal: TPosisi,
  tujuan: Extract<TTujuan, { jenis: "departemen" } | { jenis: "divisi" }>
): TRencanaKirim {
  if (tujuan.jenis === "divisi") {
    return {
      hasil: "kirim",
      mode: "pimpin",
      turunDirektur: true,
      badan: { tingkat: TINGKAT_MANAGER, divisi_ids: [tujuan.id], departemen_ids: [] },
      sesudah: { tingkat: TINGKAT_MANAGER, departemen_ids: [], divisi_ids: [tujuan.id], peran_departemen: {} },
    };
  }
  const peran = tujuan.tingkat === TINGKAT_MEMBER ? TINGKAT_MEMBER : TINGKAT_SUPERVISOR;
  return {
    hasil: "kirim",
    mode: "tambah",
    turunDirektur: true,
    badan: { tingkat: peran, departemen_ids: [tujuan.id], divisi_ids: [], peran_departemen: { [tujuan.id]: peran } },
    sesudah: {
      ...awal,
      tingkat: peran,
      departemen_ids: [tujuan.id],
      divisi_ids: [],
      peran_departemen: { [tujuan.id]: peran },
    },
  };
}

/**
 * Manager diseret DARI STRUKTUR ke departemen di divisi yang ia pimpin: ia berhenti
 * memimpin divisi itu (dan tempat asal seretannya) lalu duduk di departemen itu
 * dengan peran lajurnya. Kalau tak ada divisi tersisa, jenjangnya ikut turun ke
 * peran tertingginya; peran departemen lain tidak diseragamkan (`pertahankan_peran`).
 */
function rencanaTurunKeDepartemen(
  awal: TPosisi,
  asal: TAsal | undefined,
  tujuan: Extract<TTujuan, { jenis: "departemen" }>,
  induk: string,
  peran: number
): TRencanaKirim {
  const divs = tanpa(asal?.jenis === "divisi" ? tanpa(awal.divisi_ids, asal.id) : awal.divisi_ids, induk);
  const deps = dengan(
    asal?.jenis === "departemen" ? tanpa(awal.departemen_ids, asal.id) : awal.departemen_ids,
    tujuan.id
  );
  const peranBaru = susunPeran(awal.tingkat, deps, awal.peran_departemen, { [tujuan.id]: peran });
  const masihManager = divs.length > 0;
  const tingkat = masihManager ? awal.tingkat : Math.max(...Object.values(peranBaru));
  return {
    hasil: "kirim",
    mode: "pindah",
    turunDari: induk,
    badan: {
      departemen_ids: deps,
      divisi_ids: divs,
      peran_departemen: { [tujuan.id]: peran },
      ...(masihManager ? {} : { tingkat, pertahankan_peran: true }),
    },
    sesudah: { tingkat, departemen_ids: deps, divisi_ids: divs, peran_departemen: peranBaru },
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
export function rencanaCabut(o: TAnggotaHierarki, asal: TAsal): TRencanaKirim {
  const awal = posisiDari(o);
  const sisa =
    asal.jenis === "departemen"
      ? { ...awal, departemen_ids: tanpa(awal.departemen_ids, asal.id) }
      : { ...awal, divisi_ids: tanpa(awal.divisi_ids, asal.id) };
  const peran = susunPeran(awal.tingkat, sisa.departemen_ids, awal.peran_departemen);
  const tingkat = tingkatTurunan(tingkatSesudahCabut(awal.tingkat, sisa), peran);
  const sesudah = { ...sisa, tingkat, peran_departemen: peran };
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
  return {
    tingkat: awal.tingkat,
    departemen_ids: awal.departemen_ids,
    divisi_ids: awal.divisi_ids,
    peran_departemen: awal.peran_departemen,
  };
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
            peran_departemen: p.peran_departemen,
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
        // KEP-93: di departemen ia tampil dengan perannya di sana, bukan jenjangnya.
        const peran = p.peran_departemen[d.id] ?? Math.min(p.tingkat, TINGKAT_SUPERVISOR);
        const anggota = [
          ...d.anggota.filter((a) => a.id !== o.id),
          ...(p.departemen_ids.includes(d.id) ? [{ ...entri, tingkat: peran }] : []),
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
