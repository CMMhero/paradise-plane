/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: obrolan real-time & sinyal panggilan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { randomUUID } from "node:crypto";
import type { Request } from "express";
import type Redis from "ioredis";
import type { RawData, WebSocket } from "ws";
// plane imports
import { Controller, WebSocket as WSDecorator } from "@plane/decorators";
import { logger } from "@plane/logger";
// env
import { env } from "@/env";
// redis
import { redisManager } from "@/redis";
// kehadiran
import {
  AWALAN_KANAL_HADIR,
  POLA_KANAL_HADIR,
  PenyimpanMemori,
  PenyimpanRedis,
  ringkasKehadiran,
  statusSah,
  type PenyimpanKehadiran,
  type TStatusHadir,
} from "./kehadiran";

/** Kanal Redis yang dipakai Django. Polanya disamakan dengan
 * `plane/utils/obrolan_siaran.py`; mengubah salah satu tanpa yang lain membuat
 * siarannya hilang tanpa error di mana pun. */
const POLA_KANAL = "obrolan:*";
const AWALAN_KANAL = "obrolan:";

/** Satu peramban yang sedang membuka satu ruang. */
type Klien = {
  ws: WebSocket;
  userId: string;
  ruang: string;
};

/** Satu tab yang melaporkan kehadirannya di satu workspace. */
type KlienHadir = {
  ws: WebSocket;
  userId: string;
  slug: string;
  /** Acak per sambungan: satu orang bisa membuka banyak tab. */
  tab: string;
  status: TStatusHadir;
  /** Cookie tab ini, dipakai memeriksa keanggotaan ruang untuk sinyal panggilan. */
  cookie: string;
  /** Waktu (ms) sinyal panggilan terakhir tab ini, untuk batas laju. */
  sinyal: number[];
};

/** Jenis sinyal panggilan DM yang diterima di soket kehadiran. */
const JENIS_PANGGILAN = new Set(["panggil", "batal", "tolak", "terima", "tutup", "sibuk"]);
const POLA_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const PANJANG_ID_PANGGILAN = 64;
/** Batas laju per tab: terlalu banyak sinyal dalam jendela ini dibuang. */
const BATAS_SINYAL = 20;
const JENDELA_SINYAL_MS = 10_000;
/** Hasil keanggotaan ruang disimpan sebentar supaya tiap sinyal tidak memukul API. */
const MASA_CACHE_ANGGOTA_MS = 3 * 60_000;
const BATAS_CACHE_ANGGOTA = 2000;

/**
 * Obrolan real-time, dan jalur sinyal untuk panggilan suara/video.
 *
 * KENAPA DUA HAL DI SATU SOKET
 * Panggilan selalu terjadi di dalam percakapan yang sedang dibuka, dan haknya
 * sama persis: yang boleh menelepon adalah yang boleh membaca. Soket kedua
 * berarti pemeriksaan hak kedua yang harus dijaga sinkron, dan dua sambungan
 * yang bisa putus sendiri-sendiri sehingga panggilan hidup di ruang yang sudah
 * ditinggalkan.
 *
 * KENAPA ISI PESAN TIDAK DIKIRIM LEWAT SINI
 * Yang disiarkan Django cuma "ada sesuatu terjadi di ruang X". Peramban lalu
 * menarik isinya lewat API biasa, yang sudah menegakkan siapa boleh melihat apa.
 * Mengirim isi pesan lewat soket berarti aturan itu ditegakkan di dua tempat,
 * dan yang kedua pasti tertinggal saat aturannya berubah.
 *
 * ponytail: penarikan berkala di peramban TIDAK dicabut, cuma diperlambat. Soket
 * ini jaringan tercepat, bukan satu-satunya. Kalau Redis mati atau soketnya
 * putus tanpa sempat menyambung lagi, obrolan tetap jalan, sekadar lebih lambat.
 */
@Controller("/obrolan")
export class ObrolanController {
  [key: string]: unknown;

  /** Siapa sedang membuka ruang apa, di proses INI.
   *
   * Sengaja tidak dibagi antar replika: relai sinyal lewat Redis, jadi tiap
   * proses cukup tahu soketnya sendiri. Dengan begitu menambah replika `live`
   * tidak menuntut satu pun perubahan di sini. */
  private klien = new Map<string, Set<Klien>>();
  /** Tab yang melaporkan kehadiran, per workspace, di proses INI. */
  private klienHadir = new Map<string, Set<KlienHadir>>();
  private penyimpanMemori = new PenyimpanMemori();
  /** Anggota ruang per (pengirim, workspace, ruang), dengan masa berlaku. */
  private cacheAnggota = new Map<string, { anggota: Set<string>; sampai: number }>();
  private pelanggan: Redis | null = null;

  @WSDecorator("/")
  async handleConnection(ws: WebSocket, req: Request) {
    const slug = String(req.query.workspace ?? "");
    const ruang = String(req.query.ruang ?? "");
    const cookie = req.headers.cookie;

    // Soket kehadiran: satu per tab, tanpa ruang. Lihat `kehadiran.ts`.
    if (req.query.mode === "kehadiran") {
      await this.sambungKehadiran(ws, slug, cookie);
      return;
    }

    if (!slug || !ruang || !cookie) {
      ws.close(1008, "Parameter tidak lengkap");
      return;
    }

    let userId: string;
    try {
      userId = await this.periksaHak(slug, ruang, cookie);
    } catch {
      // Alasannya sengaja tidak dirinci ke peramban. Membedakan "belum login"
      // dari "bukan anggota ruang" memberi tahu penebak id bahwa ruang itu ada.
      ws.close(1008, "Tidak berhak");
      return;
    }

    const klien: Klien = { ws, userId, ruang };
    this.daftarkan(klien);
    await this.pastikanBerlangganan();

    ws.on("message", (data: RawData) => void this.terimaDariPeramban(klien, data));
    ws.on("close", () => this.lepaskan(klien));
    ws.on("error", (error: Error) => {
      logger.error("OBROLAN: galat soket:", error);
      this.lepaskan(klien);
      ws.close(1011, "Internal server error");
    });

    ws.send(JSON.stringify({ tipe: "siap", ruang, saya: userId }));
  }

  /**
   * Pastikan pemanggil memang boleh membaca ruang ini, dengan bertanya ke API,
   * bukan memutuskannya sendiri.
   *
   * Endpoint anggota dipakai sebagai pemeriksa karena ia sudah menolak yang
   * bukan anggota dengan 404 dan muatannya ringan. Menuliskan ulang aturannya
   * di sini berarti dua definisi hak baca yang harus dijaga sinkron.
   */
  private async periksaHak(slug: string, ruang: string, cookie: string): Promise<string> {
    const kepala = { headers: { Cookie: cookie } };

    const saya = await fetch(`${env.API_BASE_URL}/api/users/me/`, kepala);
    if (!saya.ok) throw new Error("belum login");
    const user = (await saya.json()) as { id?: string };
    if (!user?.id) throw new Error("tanpa id");

    const anggota = await fetch(`${env.API_BASE_URL}/api/workspaces/${slug}/chat/ruang/${ruang}/anggota/`, kepala);
    if (!anggota.ok) throw new Error("bukan anggota");

    return user.id;
  }

  private daftarkan(klien: Klien) {
    const isi = this.klien.get(klien.ruang) ?? new Set<Klien>();
    isi.add(klien);
    this.klien.set(klien.ruang, isi);
  }

  private lepaskan(klien: Klien) {
    const isi = this.klien.get(klien.ruang);
    if (!isi) return;
    isi.delete(klien);
    if (isi.size === 0) this.klien.delete(klien.ruang);

    // Beri tahu lawan bicara supaya panggilan yang sedang jalan tidak
    // menggantung menunggu jawaban dari tab yang sudah ditutup.
    void this.siarkan(klien.ruang, { tipe: "pergi", dari: klien.userId });
  }

  /** Satu langganan pola untuk seluruh proses, bukan satu per ruang.
   *
   * Redis membatasi jumlah langganan, dan satu langganan per ruang akan tumbuh
   * mengikuti jumlah percakapan yang kebetulan sedang dibuka orang. */
  private async pastikanBerlangganan() {
    if (this.pelanggan) return;

    const dasar = redisManager.getClient();
    if (!dasar) {
      logger.warn("OBROLAN: Redis tidak tersedia, real-time mati (penarikan berkala tetap jalan)");
      return;
    }

    // Koneksi terpisah: klien yang sedang berlangganan tidak bisa dipakai
    // perintah biasa lagi, dan klien utama masih dipakai bagian lain.
    this.pelanggan = dasar.duplicate();
    await this.pelanggan.psubscribe(POLA_KANAL, POLA_KANAL_HADIR);
    this.pelanggan.on("pmessage", (pola: string, kanal: string, muatan: string) => {
      if (pola === POLA_KANAL_HADIR) {
        this.teruskanKehadiran(kanal.slice(AWALAN_KANAL_HADIR.length), muatan);
        return;
      }
      const ruang = kanal.slice(AWALAN_KANAL.length);
      this.teruskan(ruang, muatan);
    });
    logger.info(`OBROLAN: berlangganan ${POLA_KANAL} dan ${POLA_KANAL_HADIR}`);
  }

  // ------------------------------------------------------------------------
  // Kehadiran (online / away / offline)
  // ------------------------------------------------------------------------

  private penyimpan(): PenyimpanKehadiran {
    const redis = redisManager.getClient();
    return redis ? new PenyimpanRedis(redis) : this.penyimpanMemori;
  }

  private async sambungKehadiran(ws: WebSocket, slug: string, cookie: string | undefined) {
    if (!slug || !cookie) {
      ws.close(1008, "Parameter tidak lengkap");
      return;
    }
    let userId: string;
    try {
      userId = await this.periksaHakWorkspace(slug, cookie);
    } catch {
      ws.close(1008, "Tidak berhak");
      return;
    }

    const klien: KlienHadir = { ws, userId, slug, tab: randomUUID(), status: "online", cookie, sinyal: [] };
    const isi = this.klienHadir.get(slug) ?? new Set<KlienHadir>();
    isi.add(klien);
    this.klienHadir.set(slug, isi);
    await this.pastikanBerlangganan();

    ws.on("message", (data: RawData) => void this.terimaDetak(klien, data));
    ws.on("close", () => void this.lepaskanKehadiran(klien));
    ws.on("error", (error: Error) => {
      logger.error("OBROLAN: galat soket kehadiran:", error);
      ws.close(1011, "Internal server error");
    });

    await this.catatDetak(klien);
  }

  /** Anggota aktif workspace = boleh melihat dan dilihat kehadirannya.
   * Endpoint belum-dibaca dipakai karena ringan dan sudah menolak bukan anggota. */
  private async periksaHakWorkspace(slug: string, cookie: string): Promise<string> {
    const kepala = { headers: { Cookie: cookie } };
    const saya = await fetch(`${env.API_BASE_URL}/api/users/me/`, kepala);
    if (!saya.ok) throw new Error("belum login");
    const user = (await saya.json()) as { id?: string };
    if (!user?.id) throw new Error("tanpa id");
    const anggota = await fetch(`${env.API_BASE_URL}/api/workspaces/${slug}/chat/belum-dibaca/`, kepala);
    if (!anggota.ok) throw new Error("bukan anggota");
    return user.id;
  }

  private async terimaDetak(klien: KlienHadir, data: RawData) {
    let masuk: { tipe?: string; status?: unknown; ke?: unknown; ruang?: unknown; muatan?: unknown };
    try {
      masuk = JSON.parse(data.toString());
    } catch {
      return;
    }
    if (masuk.tipe === "panggilan") {
      await this.terimaPanggilan(klien, masuk);
      return;
    }
    if (masuk.tipe !== "hadir") return;
    if (statusSah(masuk.status)) klien.status = masuk.status;
    await this.catatDetak(klien);
  }

  /** Simpan detak tab ini, siarkan kalau status ORANGNYA berubah, lalu kirim
   * potret lengkap ke tab ini (penambal siaran yang terlewat). */
  private async catatDetak(klien: KlienHadir) {
    try {
      const penyimpan = this.penyimpan();
      const sebelum = ringkasKehadiran(await penyimpan.semua(klien.slug), Date.now()).peta[klien.userId];
      await penyimpan.catat(klien.slug, `${klien.userId}:${klien.tab}`, `${klien.status}:${Date.now()}`);
      const { peta, basi } = ringkasKehadiran(await penyimpan.semua(klien.slug), Date.now());
      if (basi.length > 0) await penyimpan.hapus(klien.slug, ...basi);
      if (peta[klien.userId] !== sebelum) await this.umumkanKehadiran(klien.slug, klien.userId, peta[klien.userId]);
      if (klien.ws.readyState === klien.ws.OPEN) klien.ws.send(JSON.stringify({ tipe: "kehadiran_semua", peta }));
    } catch (error) {
      // Kehadiran adalah hiasan: galatnya tidak boleh memutus apa pun.
      logger.warn("OBROLAN: gagal mencatat kehadiran", error);
    }
  }

  private async lepaskanKehadiran(klien: KlienHadir) {
    const isi = this.klienHadir.get(klien.slug);
    isi?.delete(klien);
    if (isi && isi.size === 0) this.klienHadir.delete(klien.slug);
    try {
      const penyimpan = this.penyimpan();
      await penyimpan.hapus(klien.slug, `${klien.userId}:${klien.tab}`);
      // Tab lain milik orang yang sama mungkin masih hidup: status dihitung ulang.
      const { peta } = ringkasKehadiran(await penyimpan.semua(klien.slug), Date.now());
      await this.umumkanKehadiran(klien.slug, klien.userId, peta[klien.userId]);
    } catch (error) {
      logger.warn("OBROLAN: gagal melepas kehadiran", error);
    }
  }

  private async umumkanKehadiran(slug: string, userId: string, status: TStatusHadir | undefined) {
    const muatan = JSON.stringify({ tipe: "kehadiran", user: userId, status: status ?? "offline" });
    const redis = redisManager.getClient();
    if (!redis) {
      this.teruskanKehadiran(slug, muatan);
      return;
    }
    await redis.publish(`${AWALAN_KANAL_HADIR}${slug}`, muatan);
  }

  private teruskanKehadiran(slug: string, muatan: string) {
    const klienLokal = this.klienHadir.get(slug) ?? [];
    // Siaran kehadiran biasa tidak berisi `_tab`; hanya sinyal panggilan yang
    // perlu diurai, sisanya langsung diteruskan apa adanya.
    if (muatan.includes('"tipe":"panggilan"')) {
      let sinyal: { tipe?: string; dari?: string; ke?: string; _tab?: string };
      try {
        sinyal = JSON.parse(muatan);
      } catch {
        return;
      }
      if (sinyal.tipe === "panggilan") {
        const { _tab: tabPengirim, ...untukPeramban } = sinyal;
        const kirim = JSON.stringify(untukPeramban);
        for (const klien of klienLokal) {
          // Tujuan, atau tab LAIN milik pengirim (sinkron antar tab). Tab
          // pengirim sendiri dilewati: ia sudah tahu apa yang barusan dikirimnya.
          const sah = klien.userId === sinyal.ke || klien.userId === sinyal.dari;
          if (!sah || klien.tab === tabPengirim) continue;
          if (klien.ws.readyState === klien.ws.OPEN) klien.ws.send(kirim);
        }
        return;
      }
    }
    for (const klien of klienLokal) {
      if (klien.ws.readyState === klien.ws.OPEN) klien.ws.send(muatan);
    }
  }

  /** Sinyal panggilan DM lewat soket kehadiran, supaya yang ditelepon berdering
   * di tab mana pun tanpa harus membuka percakapannya. Semua yang tidak sah
   * dibuang diam-diam: membalas galat memberi tahu penebak apa yang ada. */
  private async terimaPanggilan(klien: KlienHadir, masuk: { ke?: unknown; ruang?: unknown; muatan?: unknown }) {
    const { ke, ruang, muatan } = masuk;
    if (typeof ke !== "string" || ke.length === 0 || ke.length > 64) return;
    if (typeof ruang !== "string" || !POLA_UUID.test(ruang)) return;
    if (!muatan || typeof muatan !== "object") return;
    const { jenis, id, video } = muatan as { jenis?: unknown; id?: unknown; video?: unknown };
    if (typeof jenis !== "string" || !JENIS_PANGGILAN.has(jenis)) return;
    if (typeof id !== "string" || id.length === 0 || id.length > PANJANG_ID_PANGGILAN) return;
    if (video !== undefined && typeof video !== "boolean") return;

    // Batas laju dihitung sebelum pemeriksaan hak, supaya spam tak memukul API.
    const sekarang = Date.now();
    klien.sinyal = klien.sinyal.filter((t) => sekarang - t < JENDELA_SINYAL_MS);
    if (klien.sinyal.length >= BATAS_SINYAL) return;
    klien.sinyal.push(sekarang);

    const anggota = await this.anggotaRuang(klien, ruang);
    if (!anggota || !anggota.has(klien.userId) || !anggota.has(ke)) return;

    // Hanya bidang yang dikenal yang diteruskan. `dari` diisi server.
    const bersih = { jenis, id, ...(video === undefined ? {} : { video }) };
    const isi = JSON.stringify({ tipe: "panggilan", dari: klien.userId, ke, ruang, muatan: bersih, _tab: klien.tab });
    const redis = redisManager.getClient();
    try {
      if (!redis) this.teruskanKehadiran(klien.slug, isi);
      else await redis.publish(`${AWALAN_KANAL_HADIR}${klien.slug}`, isi);
    } catch (error) {
      logger.warn("OBROLAN: gagal menyiarkan sinyal panggilan", error);
    }
  }

  /** Anggota satu ruang menurut API, dengan cookie tab pemanggil. `null` kalau
   * pemanggil sendiri bukan anggota (API menjawab 404) atau API gagal. Hanya
   * hasil positif yang disimpan. */
  private async anggotaRuang(klien: KlienHadir, ruang: string): Promise<Set<string> | null> {
    const kunci = `${klien.userId}:${klien.slug}:${ruang}`;
    const sekarang = Date.now();
    const ada = this.cacheAnggota.get(kunci);
    if (ada && ada.sampai > sekarang) return ada.anggota;
    try {
      const balas = await fetch(`${env.API_BASE_URL}/api/workspaces/${klien.slug}/chat/ruang/${ruang}/anggota/`, {
        headers: { Cookie: klien.cookie },
      });
      if (!balas.ok) return null;
      const daftar = (await balas.json()) as unknown;
      if (!Array.isArray(daftar)) return null;
      const anggota = new Set(daftar.filter((x): x is string => typeof x === "string"));
      if (this.cacheAnggota.size >= BATAS_CACHE_ANGGOTA) {
        for (const [k, v] of this.cacheAnggota) if (v.sampai <= sekarang) this.cacheAnggota.delete(k);
        if (this.cacheAnggota.size >= BATAS_CACHE_ANGGOTA) this.cacheAnggota.clear();
      }
      this.cacheAnggota.set(kunci, { anggota, sampai: sekarang + MASA_CACHE_ANGGOTA_MS });
      return anggota;
    } catch (error) {
      logger.warn("OBROLAN: gagal memeriksa anggota ruang", error);
      return null;
    }
  }

  /** Teruskan satu siaran ke soket lokal yang berhak menerimanya. */
  private teruskan(ruang: string, muatan: string) {
    const isi = this.klien.get(ruang);
    if (!isi || isi.size === 0) return;

    let pesan: { oleh?: string | null; ke?: string | null };
    try {
      pesan = JSON.parse(muatan);
    } catch {
      logger.warn("OBROLAN: siaran bukan JSON, diabaikan");
      return;
    }

    for (const klien of isi) {
      // Sinyal panggilan hanya untuk satu orang.
      if (pesan.ke && pesan.ke !== klien.userId) continue;
      // Gaung kiriman sendiri dibuang: pengirim sudah memperbarui layarnya saat
      // menekan kirim, dan menarik ulang sekali lagi membuat pesannya berkedip.
      if (!pesan.ke && pesan.oleh && pesan.oleh === klien.userId) continue;
      if (klien.ws.readyState !== klien.ws.OPEN) continue;
      klien.ws.send(muatan);
    }
  }

  /** Pesan dari peramban. HANYA sinyal panggilan yang diterima di sini.
   *
   * Pesan obrolan sengaja TIDAK boleh lewat soket: Django harus tetap jadi
   * satu-satunya penulis, supaya batas panjang, pemeriksaan lampiran, dan
   * penjaga kutipan tidak punya jalan memutar.
   */
  private async terimaDariPeramban(klien: Klien, data: RawData) {
    let masuk: { tipe?: string; ke?: string; muatan?: unknown };
    try {
      masuk = JSON.parse(data.toString());
    } catch {
      return;
    }
    if (masuk.tipe !== "sinyal") return;

    // `dari` diisi server dari identitas yang sudah diperiksa, BUKAN dari isi
    // pesan. Kalau peramban yang menentukannya, siapa pun di ruang ini bisa
    // menelepon sambil menyamar jadi orang lain.
    //
    // `ke` kosong berarti SIARAN ke seluruh ruang, dan itu sah: undangan
    // konferensi kanal memang ditujukan ke semua anggota yang sedang membukanya,
    // bukan ke satu orang. `oleh` diisi supaya pengirimnya tidak menerima
    // gaung undangannya sendiri.
    const menyiar = !masuk.ke;
    await this.siarkan(klien.ruang, {
      tipe: "sinyal",
      dari: klien.userId,
      ...(menyiar ? { oleh: klien.userId } : { ke: masuk.ke }),
      muatan: masuk.muatan,
    });
  }

  /** Lewat Redis, bukan langsung ke soket lokal, supaya dua orang yang kebetulan
   * terhubung ke replika `live` berbeda tetap bisa saling menelepon. */
  private async siarkan(ruang: string, isi: Record<string, unknown>) {
    const klienRedis = redisManager.getClient();
    if (!klienRedis) {
      // Tanpa Redis, relai lokal masih menyelamatkan kasus yang paling umum:
      // satu replika, dua orang, satu kantor.
      this.teruskan(ruang, JSON.stringify(isi));
      return;
    }
    await klienRedis.publish(`${AWALAN_KANAL}${ruang}`, JSON.stringify(isi));
  }
}
