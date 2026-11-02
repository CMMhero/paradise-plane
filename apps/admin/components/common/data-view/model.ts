/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: model filter, urutan, dan kolom God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu bahasa filter untuk semua daftar God Mode, meniru rich filters work item
 * di apps/web: tiap kondisi = properti + operator + nilai, satu kondisi per
 * properti, semua kondisi digabung AND.
 *
 * Halaman kecil (Accounts, Trash) menyaring di klien lewat `field.get`; halaman
 * besar (Audit log, riwayat masuk) menerjemahkan kondisi jadi query string
 * lewat `toServerParams`. Berkas ini sengaja tanpa komponen (Fast Refresh).
 */

import type { LucideIcon } from "lucide-react";

export type TFilterKind = "select" | "date" | "text";

export type TFilterOperator = "is" | "is_not" | "between" | "after" | "before" | "contains" | "not_contains";

/** Operator bawaan per jenis; field boleh mempersempitnya (`operators`). */
export const OPERATOR_BAWAAN: Record<TFilterKind, TFilterOperator[]> = {
  select: ["is", "is_not"],
  date: ["between", "after", "before"],
  text: ["contains", "not_contains"],
};

export type TFilterOption = { value: string; label: string };

export type TFilterField<Row = unknown> = {
  key: string;
  label: string;
  icon: LucideIcon;
  kind: TFilterKind;
  /** Pilihan untuk `select`. */
  options?: TFilterOption[];
  operators?: TFilterOperator[];
  /** Penyaringan di klien: nilai baris untuk field ini. `select` boleh banyak nilai. */
  get?: (row: Row) => string | string[] | null | undefined;
  /** Penyaringan di server: nama parameter query. `date` memakai `date_from`/`date_to`. */
  param?: string;
};

export type TCondition = { field: string; operator: TFilterOperator; value: string[] };

export type TSortDir = "asc" | "desc";
export type TSort = { key: string; dir: TSortDir };

export type TViewState = {
  search: string;
  conditions: TCondition[];
  sort: TSort;
  /** Kolom yang disembunyikan pengguna. */
  hidden: string[];
  perPage: number;
};

export const PER_PAGE_OPTIONS = [25, 50, 100];

export const operatorsFor = <Row>(field: TFilterField<Row>): TFilterOperator[] =>
  field.operators ?? OPERATOR_BAWAAN[field.kind];

/** Kondisi tanpa nilai tetap tampil sebagai chip, tapi belum menyaring apa pun (sama dengan apps/web). */
export const isConditionActive = (c: TCondition): boolean => c.value.some((v) => v !== "");

export const activeConditions = (conditions: TCondition[]): TCondition[] => conditions.filter(isConditionActive);

/** Tanggal lokal YYYY-MM-DD dari ISO, untuk membandingkan per hari kalender. */
export const localDay = (iso: string): string => {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return toDayString(d);
};

export const toDayString = (d: Date): string =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

const asArray = (raw: string | string[] | null | undefined): string[] =>
  raw === null || raw === undefined ? [] : Array.isArray(raw) ? raw : [raw];

/** Satu baris lolos satu kondisi? Kondisi kosong selalu lolos. */
export const matchCondition = <Row>(field: TFilterField<Row>, c: TCondition, row: Row): boolean => {
  if (!isConditionActive(c) || !field.get) return true;
  const raw = field.get(row);

  if (field.kind === "select") {
    const nilai = asArray(raw);
    const kena = nilai.some((v) => c.value.includes(v));
    return c.operator === "is_not" ? !kena : kena;
  }

  if (field.kind === "date") {
    const hari = typeof raw === "string" && raw ? localDay(raw) : "";
    if (!hari) return false;
    const [dari = "", sampai = ""] = c.value;
    if (c.operator === "after") return !dari || hari >= dari;
    if (c.operator === "before") return !dari || hari <= dari;
    return (!dari || hari >= dari) && (!sampai || hari <= sampai);
  }

  const teks = asArray(raw).join(" ").toLowerCase();
  const kata = (c.value[0] ?? "").trim().toLowerCase();
  const ada = teks.includes(kata);
  return c.operator === "not_contains" ? !ada : ada;
};

export const applyConditions = <Row>(rows: Row[], fields: TFilterField<Row>[], conditions: TCondition[]): Row[] => {
  const aktif = activeConditions(conditions)
    .map((c) => ({ c, f: fields.find((f) => f.key === c.field) }))
    .filter((x): x is { c: TCondition; f: TFilterField<Row> } => Boolean(x.f));
  if (aktif.length === 0) return rows;
  return rows.filter((row) => aktif.every(({ c, f }) => matchCondition(f, c, row)));
};

export const applySearch = <Row>(rows: Row[], search: string, text: (row: Row) => string): Row[] => {
  const kata = search.trim().toLowerCase();
  if (!kata) return rows;
  return rows.filter((row) => text(row).toLowerCase().includes(kata));
};

export type TSortValue = string | number | boolean | null | undefined;

/** Urut stabil; nilai kosong selalu di akhir, apa pun arahnya. */
export const sortRows = <Row>(rows: Row[], sort: TSort, value: ((row: Row) => TSortValue) | undefined): Row[] => {
  if (!value) return rows;
  const arah = sort.dir === "asc" ? 1 : -1;
  // Salinan sendiri, lalu diurutkan di tempat: `rows` milik pemanggil tetap utuh.
  const salinan = rows.map((row, i) => ({ row, i, v: value(row) }));
  salinan.sort((a, b) => {
    const kosongA = a.v === null || a.v === undefined || a.v === "";
    const kosongB = b.v === null || b.v === undefined || b.v === "";
    if (kosongA || kosongB) return kosongA === kosongB ? a.i - b.i : kosongA ? 1 : -1;
    const banding =
      typeof a.v === "string" && typeof b.v === "string"
        ? a.v.localeCompare(b.v, undefined, { sensitivity: "base", numeric: true })
        : Number(a.v) - Number(b.v);
    return banding === 0 ? a.i - b.i : banding * arah;
  });
  return salinan.map((x) => x.row);
};

export const paginate = <Row>(rows: Row[], page: number, perPage: number) => {
  const totalPages = Math.max(1, Math.ceil(rows.length / perPage));
  const halaman = Math.min(Math.max(page, 1), totalPages);
  return { rows: rows.slice((halaman - 1) * perPage, halaman * perPage), page: halaman, totalPages };
};

/**
 * Kondisi -> query string untuk endpoint yang menyaring di server:
 * `select` -> `param=a,b` atau `param_not=a,b`; `date` -> `date_from`/`date_to`;
 * `text` -> `param=teks`.
 */
export const toServerParams = <Row>(fields: TFilterField<Row>[], conditions: TCondition[]): Record<string, string> => {
  const hasil: Record<string, string> = {};
  for (const c of activeConditions(conditions)) {
    const f = fields.find((x) => x.key === c.field);
    if (!f?.param) continue;
    if (f.kind === "select") {
      hasil[c.operator === "is_not" ? `${f.param}_not` : f.param] = c.value.join(",");
    } else if (f.kind === "date") {
      const [dari = "", sampai = ""] = c.value;
      if (c.operator === "after" && dari) hasil.date_from = dari;
      else if (c.operator === "before" && dari) hasil.date_to = dari;
      else {
        if (dari) hasil.date_from = dari;
        if (sampai) hasil.date_to = sampai;
      }
    } else if (c.value[0]?.trim()) {
      hasil[f.param] = c.value[0].trim();
    }
  }
  return hasil;
};

/** Rentang cepat untuk filter tanggal. `[from, to]` dalam YYYY-MM-DD. */
export type TDatePreset = { key: string; label: string; range: () => [string, string] };

const geser = (hari: number): Date => {
  const d = new Date();
  d.setDate(d.getDate() + hari);
  return d;
};

export const DATE_PRESETS: TDatePreset[] = [
  { key: "today", label: "Today", range: () => [toDayString(new Date()), toDayString(new Date())] },
  { key: "yesterday", label: "Yesterday", range: () => [toDayString(geser(-1)), toDayString(geser(-1))] },
  { key: "7d", label: "Last 7 days", range: () => [toDayString(geser(-6)), toDayString(new Date())] },
  { key: "30d", label: "Last 30 days", range: () => [toDayString(geser(-29)), toDayString(new Date())] },
  {
    key: "month",
    label: "This month",
    range: () => {
      const n = new Date();
      return [toDayString(new Date(n.getFullYear(), n.getMonth(), 1)), toDayString(n)];
    },
  },
  {
    key: "last_month",
    label: "Last month",
    range: () => {
      const n = new Date();
      return [
        toDayString(new Date(n.getFullYear(), n.getMonth() - 1, 1)),
        toDayString(new Date(n.getFullYear(), n.getMonth(), 0)),
      ];
    },
  },
];

const formatHari = (day: string): string =>
  new Date(`${day}T00:00:00`).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });

/** Teks nilai chip tanggal: nama preset kalau cocok, kalau tidak tanggalnya. */
export const describeDate = (c: TCondition): string => {
  const [dari = "", sampai = ""] = c.value;
  if (!dari && !sampai) return "";
  if (c.operator === "between") {
    const preset = DATE_PRESETS.find((p) => {
      const [a, b] = p.range();
      return a === dari && b === sampai;
    });
    if (preset) return preset.label;
    if (dari && sampai) return dari === sampai ? formatHari(dari) : `${formatHari(dari)} – ${formatHari(sampai)}`;
    return dari ? `from ${formatHari(dari)}` : `until ${formatHari(sampai)}`;
  }
  return dari ? formatHari(dari) : "";
};

/** Baca state tersimpan, buang yang tidak sah (field dihapus, bentuk lama). */
export const sanitizeViewState = (raw: unknown, defaults: TViewState, fieldKeys: string[]): TViewState => {
  if (!raw || typeof raw !== "object") return defaults;
  const r = raw as Partial<TViewState>;
  const conditions = Array.isArray(r.conditions)
    ? r.conditions.filter(
        (c): c is TCondition =>
          Boolean(c) &&
          typeof c.field === "string" &&
          fieldKeys.includes(c.field) &&
          typeof c.operator === "string" &&
          Array.isArray(c.value)
      )
    : defaults.conditions;
  const sort =
    r.sort && typeof r.sort.key === "string" && (r.sort.dir === "asc" || r.sort.dir === "desc")
      ? r.sort
      : defaults.sort;
  return {
    search: typeof r.search === "string" ? r.search : defaults.search,
    conditions,
    sort,
    hidden: Array.isArray(r.hidden) ? r.hidden.filter((h) => typeof h === "string") : defaults.hidden,
    perPage: PER_PAGE_OPTIONS.includes(Number(r.perPage)) ? Number(r.perPage) : defaults.perPage,
  };
};

export const OPERATOR_LABEL: Record<TFilterOperator, string> = {
  is: "is",
  is_not: "is not",
  between: "between",
  after: "on or after",
  before: "on or before",
  contains: "contains",
  not_contains: "does not contain",
};
