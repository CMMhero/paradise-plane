/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: state tampilan daftar God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Cari, filter, urutan, kolom tersembunyi, dan jumlah baris per halaman,
 * disimpan per halaman di localStorage supaya bertahan saat pindah tab, sama
 * seperti tampilan work item yang mengingat filternya. Halaman (page) sengaja
 * TIDAK disimpan, dan kembali ke 1 setiap kali filter atau urutan berubah.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import type { TCondition, TFilterField, TSort, TViewState } from "./model";
import { operatorsFor, sanitizeViewState } from "./model";

const PREFIX = "godmode:view:";

const baca = <Row>(key: string, defaults: TViewState, fields: TFilterField<Row>[]): TViewState => {
  if (typeof window === "undefined") return defaults;
  try {
    const raw = window.localStorage.getItem(PREFIX + key);
    return raw
      ? sanitizeViewState(
          JSON.parse(raw),
          defaults,
          fields.map((f) => f.key)
        )
      : defaults;
  } catch {
    // Isi rusak atau storage diblokir: mulai dari bawaan, jangan memecah halaman.
    return defaults;
  }
};

export type TViewController = TViewState & {
  page: number;
  setPage: (page: number) => void;
  setSearch: (search: string) => void;
  addCondition: (field: string) => void;
  updateCondition: (field: string, patch: Partial<Omit<TCondition, "field">>) => void;
  removeCondition: (field: string) => void;
  clearConditions: () => void;
  setSort: (sort: TSort) => void;
  toggleColumn: (key: string) => void;
  setPerPage: (perPage: number) => void;
  reset: () => void;
  /** Ada cari atau filter berisi nilai, untuk tombol "Clear all" dan teks kosong. */
  isFiltered: boolean;
};

export function useViewState<Row>(key: string, defaults: TViewState, fields: TFilterField<Row>[]): TViewController {
  const [state, setState] = useState<TViewState>(() => baca(key, defaults, fields));
  const [page, setPage] = useState(1);

  useEffect(() => {
    try {
      window.localStorage.setItem(PREFIX + key, JSON.stringify(state));
    } catch {
      // Storage penuh atau diblokir: tampilan tetap jalan, hanya tidak diingat.
    }
  }, [key, state]);

  // Setiap perubahan yang mengubah isi daftar mengembalikan ke halaman 1,
  // menyaring dari halaman 5 bisa mendarat di halaman kosong padahal datanya ada.
  const ubah = useCallback((fn: (s: TViewState) => TViewState) => {
    setState(fn);
    setPage(1);
  }, []);

  const addCondition = useCallback(
    (fieldKey: string) => {
      const field = fields.find((f) => f.key === fieldKey);
      if (!field) return;
      ubah((s) =>
        s.conditions.some((c) => c.field === fieldKey)
          ? s
          : { ...s, conditions: [...s.conditions, { field: fieldKey, operator: operatorsFor(field)[0], value: [] }] }
      );
    },
    [fields, ubah]
  );

  return useMemo(
    () => ({
      ...state,
      page,
      setPage,
      setSearch: (search) => ubah((s) => ({ ...s, search })),
      addCondition,
      updateCondition: (fieldKey, patch) =>
        ubah((s) => ({
          ...s,
          conditions: s.conditions.map((c) => (c.field === fieldKey ? { ...c, ...patch } : c)),
        })),
      removeCondition: (fieldKey) =>
        ubah((s) => ({ ...s, conditions: s.conditions.filter((c) => c.field !== fieldKey) })),
      clearConditions: () => ubah((s) => ({ ...s, search: "", conditions: [] })),
      setSort: (sort) => ubah((s) => ({ ...s, sort })),
      toggleColumn: (col) =>
        setState((s) => ({
          ...s,
          hidden: s.hidden.includes(col) ? s.hidden.filter((h) => h !== col) : [...s.hidden, col],
        })),
      setPerPage: (perPage) => ubah((s) => ({ ...s, perPage })),
      reset: () => ubah(() => defaults),
      isFiltered: state.search.trim() !== "" || state.conditions.some((c) => c.value.some((v) => v !== "")),
    }),
    [state, page, ubah, addCondition, defaults]
  );
}

/** Nilai yang baru ikut berubah sesudah `delay` ms tanpa ketikan, untuk cari di server. */
export function useDebounced<T>(value: T, delay = 300): T {
  const [nilai, setNilai] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setNilai(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return nilai;
}
