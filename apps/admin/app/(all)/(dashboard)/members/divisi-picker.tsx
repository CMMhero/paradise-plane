/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pemilih divisi multi God Mode 
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Dropdown multi-pilih dengan cari: tombol ringkas ("3 divisi dipilih") yang
 * membuka panel berisi kolom cari + daftar checkbox + pilih-semua/bersihkan.
 * 31 divisi tidak muat sebagai checkbox gelar maupun select-native (tanpa cari).
 *
 * Tanpa dependensi baru: tombol + panel absolut + penutup klik-di-luar
 * (pointerdown di document). Panel menutup juga dengan Escape.
 */

import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
// local
import { inputClass } from "./constants";

type Props = {
  /** Semua opsi (identifier divisi). */
  opsi: string[];
  dipilih: string[];
  onUbah: (baru: string[]) => void;
  /** Identifier → nama tampil. Tanpa entri = tampil identifier apa adanya. */
  nama?: Record<string, string>;
  placeholder?: string;
  disabled?: boolean;
};

export function DivisiPicker({ opsi, dipilih, onUbah, nama = {}, placeholder = "Pilih…", disabled = false }: Props) {
  const [terbuka, setTerbuka] = useState(false);
  const [cari, setCari] = useState("");
  const wadah = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!terbuka) return;
    const tutupLuar = (e: PointerEvent) => {
      if (wadah.current && !wadah.current.contains(e.target as Node)) setTerbuka(false);
    };
    const tutupEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTerbuka(false);
    };
    document.addEventListener("pointerdown", tutupLuar);
    document.addEventListener("keydown", tutupEsc);
    return () => {
      document.removeEventListener("pointerdown", tutupLuar);
      document.removeEventListener("keydown", tutupEsc);
    };
  }, [terbuka]);

  const q = cari.trim().toLowerCase();
  const label = (d: string): string => nama[d] ?? d;
  const saring = q ? opsi.filter((d) => `${d} ${label(d)}`.toLowerCase().includes(q)) : opsi;

  const toggle = (d: string) =>
    dipilih.includes(d) ? onUbah(dipilih.filter((x) => x !== d)) : onUbah([...dipilih, d]);

  const ringkas =
    dipilih.length === 0
      ? placeholder
      : dipilih.length <= 2
        ? dipilih.map(label).join(", ")
        : `${dipilih.length} divisi dipilih`;

  return (
    <div ref={wadah} className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setTerbuka((v) => !v)}
        className={`${inputClass} flex w-full items-center justify-between gap-2 text-left disabled:opacity-60`}
      >
        <span className={dipilih.length === 0 ? "text-placeholder" : "text-primary"}>{ringkas}</span>
        <ChevronDown className="size-4 shrink-0 text-tertiary" />
      </button>

      {terbuka && !disabled && (
        <div className="shadow-lg absolute z-20 mt-1 max-h-64 w-full min-w-56 overflow-hidden rounded border border-subtle bg-layer-1">
          <div className="border-b border-subtle p-2">
            <input
              // eslint-disable-next-line jsx-a11y/no-autofocus -- panel dibuka lewat klik eksplisit; fokus langsung ke cari menghemat satu Tab per buka
              autoFocus
              className={`${inputClass} w-full`}
              value={cari}
              onChange={(e) => setCari(e.target.value)}
            />
          </div>
          <div className="flex items-center justify-between border-b border-subtle px-3 py-1.5">
            <button type="button" onClick={() => onUbah([...opsi])} className="text-11 font-medium text-accent-primary">
              Pilih semua
            </button>
            <button type="button" onClick={() => onUbah([])} className="text-11 font-medium text-secondary">
              Bersihkan
            </button>
          </div>
          <div className="max-h-44 overflow-y-auto p-1">
            {saring.length === 0 ? (
              <p className="px-2 py-3 text-center text-11 text-tertiary">Tidak ada divisi yang cocok.</p>
            ) : (
              saring.map((d) => (
                <label
                  key={d}
                  className="flex w-full cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-left text-body-sm-regular text-primary hover:bg-layer-2"
                >
                  <input
                    type="checkbox"
                    checked={dipilih.includes(d)}
                    onChange={() => toggle(d)}
                    className="accent-accent-primary size-4 shrink-0"
                  />
                  {label(d)}
                </label>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
