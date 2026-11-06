/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: bentuk muatan kartu obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Pembaca muatan kartu yang tidak percaya begitu saja pada server.
 *
 * `muatan` datang sebagai JSON bebas dan bentuknya bisa berubah antar versi
 * (kartu lama tetap tersimpan selamanya). Setiap medan dibaca lewat penjaga
 * tipe; yang hilang jadi nilai kosong, bukan galat render yang menjatuhkan
 * seluruh percakapan.
 */

type TObjek = Record<string, unknown>;

const objek = (v: unknown): TObjek => (v && typeof v === "object" && !Array.isArray(v) ? (v as TObjek) : {});
const teks = (v: unknown): string => (typeof v === "string" ? v : "");
const angka = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);

export type TJenisEntri = "Added" | "Changed" | "Fixed";

export type TCatatanRilis = {
  versi: string;
  tanggal: string;
  entri: { type: TJenisEntri; text: string }[];
};

export const bacaCatatanRilis = (muatan: unknown): TCatatanRilis => {
  const m = objek(muatan);
  const entri = Array.isArray(m.entri) ? m.entri : [];
  return {
    versi: teks(m.versi),
    tanggal: teks(m.tanggal),
    entri: entri
      .map((e) => objek(e))
      .filter((e) => ["Added", "Changed", "Fixed"].includes(teks(e.type)) && teks(e.text))
      .map((e) => ({ type: teks(e.type) as TJenisEntri, text: teks(e.text) })),
  };
};

/** Urutan tampil: yang baru dulu, lalu perubahan, lalu perbaikan. */
export const URUTAN_ENTRI: TJenisEntri[] = ["Added", "Changed", "Fixed"];

export type TStatusPanggilan = "berlangsung" | "selesai" | "tak_terjawab";

export type TLogPanggilan = {
  status: TStatusPanggilan;
  video: boolean;
  konferensi: boolean;
  oleh: string;
  durasi: number | null;
};

export const bacaLogPanggilan = (muatan: unknown): TLogPanggilan => {
  const m = objek(muatan);
  const status = teks(m.status);
  return {
    status: status === "selesai" || status === "tak_terjawab" ? status : "berlangsung",
    video: m.video === true,
    konferensi: m.konferensi === true,
    oleh: teks(m.oleh),
    durasi: angka(m.durasi),
  };
};

/** `75` jadi `1:15`, `3725` jadi `1:02:05`. */
export const formatDurasi = (detik: number): string => {
  const j = Math.floor(detik / 3600);
  const m = Math.floor((detik % 3600) / 60);
  const d = Math.floor(detik % 60);
  const dd = String(d).padStart(2, "0");
  return j > 0 ? `${j}:${String(m).padStart(2, "0")}:${dd}` : `${m}:${dd}`;
};

export type TStatusPersetujuan = "menunggu" | "disetujui" | "ditolak";

export type TKartuTugas = {
  aksi: string;
  aktor: string;
  /** Siapa yang diberi kabar; kosong di kartu lama. */
  penerima: string;
  slug: string;
  project: { id: string; nama: string; identifier: string };
  tugas: {
    id: string;
    nomor: string;
    judul: string;
    state: string;
    stateGroup: string;
    tenggat: string;
    assignees: string[];
  } | null;
  detail: { komentar: string; field: string; verb: string; deskripsi: string };
  persetujuan: { id: string; projectId: string; status: TStatusPersetujuan; pemohon: string } | null;
};

export const bacaKartuTugas = (muatan: unknown): TKartuTugas => {
  const m = objek(muatan);
  const project = objek(m.project);
  const tugas = objek(m.tugas);
  const detail = objek(m.detail);
  const persetujuan = objek(m.persetujuan);
  const status = teks(persetujuan.status);
  return {
    aksi: teks(m.aksi),
    aktor: teks(m.aktor),
    penerima: teks(m.penerima),
    slug: teks(m.workspace_slug),
    project: { id: teks(project.id), nama: teks(project.nama), identifier: teks(project.identifier) },
    tugas: teks(tugas.id)
      ? {
          id: teks(tugas.id),
          nomor: teks(tugas.nomor),
          judul: teks(tugas.judul),
          state: teks(tugas.state),
          stateGroup: teks(tugas.state_group),
          tenggat: teks(tugas.tenggat),
          assignees: Array.isArray(tugas.assignees) ? tugas.assignees.map(teks).filter(Boolean) : [],
        }
      : null,
    detail: {
      komentar: teks(detail.komentar),
      field: teks(detail.field),
      verb: teks(detail.verb),
      deskripsi: teks(detail.deskripsi),
    },
    persetujuan: teks(persetujuan.id)
      ? {
          id: teks(persetujuan.id),
          projectId: teks(persetujuan.project_id) || teks(project.id),
          status: status === "disetujui" || status === "ditolak" ? status : "menunggu",
          pemohon: teks(persetujuan.pemohon),
        }
      : null,
  };
};
