/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: indikator kehadiran obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Siapa sedang online, away, atau offline di satu workspace.
 *
 * BENTUKNYA
 * Tiap tab peramban membuka SATU soket kehadiran (lihat `use-kehadiran.ts` di
 * apps/web) dan mengirim detak tiap ~25 detik berisi statusnya sendiri:
 * "online" kalau tab terlihat dan ada gerakan dalam 5 menit, selain itu "away".
 * Satu orang bisa punya banyak tab; status orangnya = status terbaik di antara
 * tab-tabnya yang masih berdetak. Tidak berdetak lebih dari BATAS_DETAK_MS =
 * dianggap mati (tab tertutup paksa, proses live mati), jadi tidak ada yang
 * tersangkut "online" selamanya.
 *
 * Penyimpanan per workspace adalah SATU hash Redis: medan `<user>:<tab>`, nilai
 * `<status>:<epoch ms>`. Dengan begitu replika `live` mana pun melihat tab dari
 * replika lain. Perubahan status orang disiarkan lewat kanal Redis
 * `kehadiran:<slug>`, dan setiap jawaban detak membawa potret lengkap, sehingga
 * siaran yang hilang pun pulih sendiri dalam satu detak.
 *
 * Tidak ada penarikan per orang. Biaya per tab per detak: satu HSET, satu
 * HGETALL atas hash berisi beberapa ratus medan.
 */

export type TStatusHadir = "online" | "away";

/** Detak dari peramban tiap 25 detik; tiga kali terlewat = dianggap pergi. */
export const BATAS_DETAK_MS = 75_000;
/** Hash dibuang Redis kalau sehari tidak ada detak sama sekali. */
export const UMUR_HASH_DETIK = 86_400;

export const AWALAN_KANAL_HADIR = "kehadiran:";
export const POLA_KANAL_HADIR = "kehadiran:*";
const AWALAN_HASH = "obrolan-kehadiran:";

export const kunciHash = (slug: string) => `${AWALAN_HASH}${slug}`;

/** Tempat menyimpan detak. Redis di produksi, Map di memori kalau Redis mati. */
export interface PenyimpanKehadiran {
  catat(slug: string, medan: string, nilai: string): Promise<void>;
  hapus(slug: string, ...medan: string[]): Promise<void>;
  semua(slug: string): Promise<Record<string, string>>;
}

export class PenyimpanMemori implements PenyimpanKehadiran {
  private data = new Map<string, Map<string, string>>();

  async catat(slug: string, medan: string, nilai: string) {
    const isi = this.data.get(slug) ?? new Map<string, string>();
    isi.set(medan, nilai);
    this.data.set(slug, isi);
  }

  async hapus(slug: string, ...medan: string[]) {
    const isi = this.data.get(slug);
    if (!isi) return;
    medan.forEach((m) => isi.delete(m));
    if (isi.size === 0) this.data.delete(slug);
  }

  async semua(slug: string) {
    return Object.fromEntries(this.data.get(slug) ?? []);
  }
}

/** Bagian ioredis yang dipakai; ditulis sempit supaya mudah dipalsukan di uji. */
type KlienRedisHadir = {
  hset(key: string, field: string, value: string): Promise<unknown>;
  hdel(key: string, ...fields: string[]): Promise<unknown>;
  hgetall(key: string): Promise<Record<string, string>>;
  expire(key: string, seconds: number): Promise<unknown>;
};

export class PenyimpanRedis implements PenyimpanKehadiran {
  constructor(private redis: KlienRedisHadir) {}

  async catat(slug: string, medan: string, nilai: string) {
    await this.redis.hset(kunciHash(slug), medan, nilai);
    await this.redis.expire(kunciHash(slug), UMUR_HASH_DETIK);
  }

  async hapus(slug: string, ...medan: string[]) {
    if (medan.length > 0) await this.redis.hdel(kunciHash(slug), ...medan);
  }

  async semua(slug: string) {
    return (await this.redis.hgetall(kunciHash(slug))) ?? {};
  }
}

const PERINGKAT: Record<TStatusHadir, number> = { online: 2, away: 1 };

export const statusSah = (nilai: unknown): nilai is TStatusHadir => nilai === "online" || nilai === "away";

/**
 * Ringkas isi hash jadi status per orang, sekaligus daftar medan basi.
 *
 * Fungsi murni: satu-satunya tempat aturan "status terbaik dari tab yang masih
 * berdetak" ditulis, dan itu yang diuji.
 */
export function ringkasKehadiran(
  isi: Record<string, string>,
  sekarang: number
): { peta: Record<string, TStatusHadir>; basi: string[] } {
  const peta: Record<string, TStatusHadir> = {};
  const basi: string[] = [];
  for (const [medan, nilai] of Object.entries(isi)) {
    const pemisahMedan = medan.lastIndexOf(":");
    const pemisahNilai = nilai.lastIndexOf(":");
    const userId = pemisahMedan > 0 ? medan.slice(0, pemisahMedan) : "";
    const status = nilai.slice(0, pemisahNilai);
    const waktu = Number(nilai.slice(pemisahNilai + 1));
    if (!userId || !statusSah(status) || !Number.isFinite(waktu) || sekarang - waktu > BATAS_DETAK_MS) {
      basi.push(medan);
      continue;
    }
    const lama = peta[userId];
    if (!lama || PERINGKAT[status] > PERINGKAT[lama]) peta[userId] = status;
  }
  return { peta, basi };
}
