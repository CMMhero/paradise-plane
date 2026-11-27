/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: cache pengumuman
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { mutate } from "swr";
// services
import { KUNCI_BELUM_DIBACA } from "@/services/chat.service";
import type { TDaftarSematan, TPesan } from "@/services/chat.service";

/** Isi kanal Announcements, dipakai bersama halaman Pengumuman dan widget Home. */
export const kunciPengumuman = (slug: string, kanalId: string) => `PENGUMUMAN_${slug}_${kanalId}`;

/**
 * Sesudah satu pengumuman disunting atau dihapus: halaman, widget Home, isi Obrolan,
 * bilah sematan, daftar percakapan, dan lencana.
 *
 * Cache diubah langsung, bukan hanya ditarik ulang: yang sedang tidak tampil tidak
 * menarik apa pun, dan widget Home menahan tarikan ulang selama semenit.
 */
export const segarkanPengumuman = (slug: string, kanalId: string, pesanId: string, hasil: TPesan | "dihapus") => {
  const terapkan = (daftar?: TPesan[]) =>
    daftar?.map((p) => {
      if (p.id !== pesanId) return p;
      if (hasil !== "dihapus") return { ...p, isi: hasil.isi, muatan: hasil.muatan, disunting: hasil.disunting };
      return { ...p, dihapus: true, isi: "", lampiran: [], reaksi: [], balasan_ke: null, disematkan: false };
    });
  void mutate(kunciPengumuman(slug, kanalId), terapkan);
  void mutate(`CHAT_ISI_${slug}_${kanalId}`, terapkan);
  const sematan = `CHAT_SEMATAN_${slug}_${kanalId}`;
  if (hasil === "dihapus")
    void mutate(
      sematan,
      (data?: TDaftarSematan) => data && { ...data, pesan: data.pesan.filter((p) => p.id !== pesanId) }
    );
  else void mutate(sematan);
  void mutate(`CHAT_PERCAKAPAN_${slug}`);
  void mutate(KUNCI_BELUM_DIBACA);
};
