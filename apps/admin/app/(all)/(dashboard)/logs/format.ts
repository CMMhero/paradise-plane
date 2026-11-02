/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: format perubahan jejak audit
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * django-auditlog menyimpan {field: [lama, baru]} dengan nama kolom database
 * dan nilai berbentuk teks ("None", "True", UUID, ISO datetime). Modul ini
 * mengubahnya jadi baris yang bisa dibaca orang. Murni, tanpa hook, supaya
 * aman dipanggil di dalam .map().
 */

import type { TAuditLogEntry } from "@plane/services";

/** Kolom yang berubah di hampir setiap simpan dan jarang menjawab "apa yang diubah". */
const KOLOM_TEKNIS = new Set([
  "updated_at",
  "created_at",
  "updated_by",
  "created_by",
  "updated_by_id",
  "created_by_id",
  "sort_order",
  "sequence_id",
  "id",
  "completed_at",
  "last_workspace_id",
  "view_props",
  "default_props",
  "preferences",
]);

/** Nama tampil untuk kolom yang sering muncul. Sisanya diturunkan dari nama kolom. */
const NAMA_KOLOM: Record<string, string> = {
  name: "Name",
  description: "Description",
  description_html: "Description",
  description_stripped: "Description (text)",
  state: "State",
  state_id: "State",
  priority: "Priority",
  start_date: "Start date",
  target_date: "Due date",
  assignees: "Assignees",
  labels: "Labels",
  parent: "Parent",
  parent_id: "Parent",
  project: "Project",
  project_id: "Project",
  workspace: "Workspace",
  workspace_id: "Workspace",
  member: "Member",
  member_id: "Member",
  role: "Role",
  is_active: "Active",
  archived_at: "Archived",
  deleted_at: "Deleted",
  identifier: "Identifier",
  network: "Visibility",
  estimate_point: "Estimate",
  estimate_point_id: "Estimate",
  owned_by: "Owner",
  owned_by_id: "Owner",
  access: "Access",
  is_locked: "Locked",
  type: "Type",
  type_id: "Type",
  cycle: "Cycle",
  module: "Module",
  point: "Estimate",
};

const PERAN: Record<string, string> = { "20": "Admin", "15": "Member", "5": "Guest" };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ISO_WAKTU = /^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}/;
const ISO_TANGGAL = /^\d{4}-\d{2}-\d{2}$/;

export const namaKolom = (field: string): string => {
  if (NAMA_KOLOM[field]) return NAMA_KOLOM[field];
  const dasar = field.replace(/_id$/, "").replace(/_/g, " ").trim();
  return dasar.charAt(0).toUpperCase() + dasar.slice(1);
};

export type TNilaiAudit =
  | { jenis: "kosong" }
  | { jenis: "teks"; teks: string }
  | { jenis: "id"; teks: string; pendek: string };

/** Satu nilai mentah jadi bentuk tampil. `ya`/`tidak` dioper supaya kamus tetap di godmode.tsx. */
export const nilaiAudit = (field: string, mentah: unknown, ya: string, tidak: string): TNilaiAudit => {
  const teks = mentah === null || mentah === undefined ? "" : String(mentah).trim();
  if (teks === "" || teks === "None" || teks === "null" || teks === "[]" || teks === "{}") return { jenis: "kosong" };
  if (teks === "True") return { jenis: "teks", teks: ya };
  if (teks === "False") return { jenis: "teks", teks: tidak };
  if (field === "role" && PERAN[teks]) return { jenis: "teks", teks: PERAN[teks] };
  if (UUID.test(teks)) return { jenis: "id", teks, pendek: teks.slice(0, 8) };
  if (ISO_WAKTU.test(teks)) {
    const d = new Date(teks.replace(" ", "T"));
    if (!Number.isNaN(d.getTime()))
      return {
        jenis: "teks",
        teks: d.toLocaleString("en-GB", {
          day: "2-digit",
          month: "short",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        }),
      };
  }
  if (ISO_TANGGAL.test(teks)) {
    const d = new Date(`${teks}T00:00:00`);
    if (!Number.isNaN(d.getTime()))
      return {
        jenis: "teks",
        teks: d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }),
      };
  }
  // HTML deskripsi editor: tampilkan teksnya saja, markup tidak berguna di sini.
  if (teks.startsWith("<")) {
    const polos = teks
      .replace(/<[^>]*>/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    return polos ? { jenis: "teks", teks: polos } : { jenis: "kosong" };
  }
  return { jenis: "teks", teks };
};

export type TObjekAudit = { utama: string; konteks: string | null; jenisKonteks: "di" | "oleh" };

/**
 * object_repr berasal dari `__str__` model upstream yang berbentuk "A <B>":
 * Issue "nama <project>", Project "nama <workspace>", Member "email <tempat>",
 * Page "email pemilik <nama>". Teks itu dibekukan saat entri ditulis, jadi
 * dirapikan di sini, bukan dengan mengubah `__str__` (entri lama tetap kurung).
 */
export const objekAudit = (model: string | null, repr: string): TObjekAudit => {
  const cocok = /^(.*?)\s*<([^<>]*)>$/.exec(repr.trim());
  if (!cocok) return { utama: repr, konteks: null, jenisKonteks: "di" };
  const [, depan, dalam] = cocok;
  // Page menaruh nama di dalam kurung dan pemilik di depan, kebalikan model lain.
  if (model === "page") return { utama: dalam || depan, konteks: dalam ? depan || null : null, jenisKonteks: "oleh" };
  return { utama: depan || dalam, konteks: depan ? dalam || null : null, jenisKonteks: "di" };
};

export type TBarisPerubahan = { field: string; label: string; lama: unknown; baru: unknown; teknis: boolean };

/** Peta perubahan jadi baris berurutan: kolom bermakna dulu, kolom teknis di belakang. */
export const barisPerubahan = (changes: TAuditLogEntry["changes"]): TBarisPerubahan[] => {
  if (!changes) return [];
  const semua = Object.entries(changes).map(([field, nilai]): TBarisPerubahan => {
    const [lama, baru] = Array.isArray(nilai) ? nilai : ["", nilai];
    return { field, label: namaKolom(field), lama, baru, teknis: KOLOM_TEKNIS.has(field) };
  });
  return [...semua.filter((b) => !b.teknis), ...semua.filter((b) => b.teknis)];
};

export type TAksiAudit = "create" | "update" | "delete" | "other";

export const aksiAudit = (action: string): TAksiAudit => {
  const a = action.toLowerCase();
  if (a.startsWith("create")) return "create";
  if (a.startsWith("update")) return "update";
  if (a.startsWith("delete")) return "delete";
  return "other";
};

/** Kolom yang punya nama tampil, ditawarkan sebagai pilihan filter "Changed field". */
export const kolomDikenal = (): { value: string; label: string }[] => {
  const hasil = Object.entries(NAMA_KOLOM).map(([value, label]) => ({ value, label: `${label} · ${value}` }));
  hasil.sort((a, b) => a.label.localeCompare(b.label));
  return hasil;
};
