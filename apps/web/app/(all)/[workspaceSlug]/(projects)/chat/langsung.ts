/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: sambungan real-time obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { LIVE_BASE_PATH, LIVE_BASE_URL } from "@plane/constants";

/** Kejadian yang disiarkan Django lewat Redis. */
export type TKejadian = {
  tipe: "siap" | "pesan" | "sunting" | "hapus" | "reaksi" | "sinyal" | "pergi";
  ruang?: string;
  saya?: string;
  oleh?: string | null;
  dari?: string;
  ke?: string;
  muatan?: unknown;
};

/** Jeda sambung ulang, naik bertahap lalu berhenti naik.
 *
 * Tanpa tangga ini, server yang sedang dideploy akan dihujani seluruh peramban
 * yang terbuka sekaligus, tepat saat ia paling rapuh. */
const TANGGA_SAMBUNG_ULANG = [1000, 2000, 5000, 10000, 30000];

type Opsi = {
  slug?: string;
  ruangId?: string | null;
  /** Dipanggil saat ada perubahan isi ruang. Yang memanggil menarik ulang
   * sendiri; muatan pesannya sengaja tidak dikirim lewat soket. */
  onPerubahan?: () => void;
  /** Sinyal panggilan dari orang lain di ruang yang sama. */
  onSinyal?: (dari: string, muatan: unknown) => void;
  /** Lawan bicara menutup tab atau berpindah ruang. */
  onPergi?: (dari: string) => void;
};

/**
 * Sambungan real-time ke `apps/live` untuk satu ruang.
 *
 * ponytail: ini LAPISAN CEPAT, bukan satu-satunya. Penarikan berkala di halaman
 * Obrolan sengaja dipertahankan sebagai jaring pengaman, cuma diperlambat.
 * Kalau soket ini gagal menyambung, obrolan tetap jalan dan orang hanya melihat
 * pesan datang lebih lambat, bukan tidak datang sama sekali.
 */
export function useObrolanLangsung({ slug, ruangId, onPerubahan, onSinyal, onPergi }: Opsi) {
  const [tersambung, setTersambung] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const percobaanRef = useRef(0);
  const waktuRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hidupRef = useRef(true);

  // Callback disimpan di ref supaya berubahnya identitas fungsi milik pemanggil
  // tidak memutus lalu menyambung ulang soket pada setiap render.
  const cbRef = useRef({ onPerubahan, onSinyal, onPergi });
  cbRef.current = { onPerubahan, onSinyal, onPergi };

  useEffect(() => {
    if (!slug || !ruangId) return;

    hidupRef.current = true;

    const sambung = () => {
      if (!hidupRef.current) return;

      let url: URL;
      try {
        const dasar = LIVE_BASE_URL?.trim() || window.location.origin;
        url = new URL(dasar);
        url.protocol = window.location.protocol === "https:" ? "wss" : "ws";
        url.pathname = `${LIVE_BASE_PATH}/obrolan/`;
        url.searchParams.set("workspace", slug);
        url.searchParams.set("ruang", ruangId);
      } catch {
        // Alamat live tidak sah. Diam saja: penarikan berkala menutupinya.
        return;
      }

      const ws = new WebSocket(url.toString());
      socketRef.current = ws;

      ws.addEventListener("open", () => {
        percobaanRef.current = 0;
        setTersambung(true);
      });

      ws.addEventListener("message", (ev) => {
        let kejadian: TKejadian;
        try {
          kejadian = JSON.parse(ev.data as string);
        } catch {
          return;
        }
        if (kejadian.tipe === "siap") return;
        if (kejadian.tipe === "sinyal" && kejadian.dari) {
          cbRef.current.onSinyal?.(kejadian.dari, kejadian.muatan);
          return;
        }
        if (kejadian.tipe === "pergi" && kejadian.dari) {
          cbRef.current.onPergi?.(kejadian.dari);
          return;
        }
        cbRef.current.onPerubahan?.();
      });

      ws.addEventListener("close", () => {
        setTersambung(false);
        socketRef.current = null;
        if (!hidupRef.current) return;
        const jeda = TANGGA_SAMBUNG_ULANG[Math.min(percobaanRef.current, TANGGA_SAMBUNG_ULANG.length - 1)];
        percobaanRef.current += 1;
        waktuRef.current = setTimeout(sambung, jeda);
      });

      // Penutupan ditangani listener `close`, yang selalu menyusul `error`.
      // Menangani keduanya membuat sambung ulang berjalan dua kali.
      ws.addEventListener("error", () => ws.close());
    };

    sambung();

    return () => {
      hidupRef.current = false;
      if (waktuRef.current) clearTimeout(waktuRef.current);
      socketRef.current?.close();
      socketRef.current = null;
      setTersambung(false);
    };
  }, [slug, ruangId]);

  /** Kirim sinyal panggilan ke satu orang di ruang yang sama.
   *
   * `dari` sengaja tidak diisi di sini. Server yang menuliskannya dari identitas
   * yang sudah diperiksa, supaya tidak ada yang bisa menelepon sambil menyamar. */
  const kirimSinyal = useCallback((ke: string, muatan: unknown) => {
    const ws = socketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    ws.send(JSON.stringify({ tipe: "sinyal", ke, muatan }));
    return true;
  }, []);

  return { tersambung, kirimSinyal };
}
