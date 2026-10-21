/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: obrolan real-time & sinyal panggilan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

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
  private pelanggan: Redis | null = null;

  @WSDecorator("/")
  async handleConnection(ws: WebSocket, req: Request) {
    const slug = String(req.query.workspace ?? "");
    const ruang = String(req.query.ruang ?? "");
    const cookie = req.headers.cookie;

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
    await this.pelanggan.psubscribe(POLA_KANAL);
    this.pelanggan.on("pmessage", (_pola: string, kanal: string, muatan: string) => {
      const ruang = kanal.slice(AWALAN_KANAL.length);
      this.teruskan(ruang, muatan);
    });
    logger.info("OBROLAN: berlangganan " + POLA_KANAL);
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
