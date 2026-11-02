/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pemilih divisi multi God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * CustomSearchSelect upstream dalam mode multiple: tombol ringkas ("3 divisi
 * dipilih"), kolom cari, daftar bercentang. Pilih-semua/bersihkan ada di kaki
 * daftar. 31 divisi tidak muat sebagai checkbox gelar maupun select-native.
 * Daftar dirender lewat portal, jadi aman di dalam modal yang bergulir.
 */

// plane imports
import { CustomSearchSelect } from "@plane/ui";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";

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

const NAMA_KOSONG: Record<string, string> = {};

export function DivisiPicker({ opsi, dipilih, onUbah, nama = NAMA_KOSONG, placeholder, disabled = false }: Props) {
  const { s, fill } = useGodmodeStrings();
  const label = (d: string): string => nama[d] ?? d;

  const ringkas =
    dipilih.length === 0 ? (
      <span className="text-placeholder">{placeholder ?? s.picker.default_placeholder}</span>
    ) : dipilih.length <= 2 ? (
      dipilih.map(label).join(", ")
    ) : (
      fill(s.picker.chosen_count, { n: dipilih.length })
    );

  return (
    <CustomSearchSelect
      multiple
      value={dipilih}
      onChange={(v: string[]) => onUbah(v)}
      label={<span className="truncate">{ringkas}</span>}
      disabled={disabled}
      buttonClassName="w-full rounded-md border-subtle bg-layer-2"
      className="w-full"
      input
      maxHeight="lg"
      noResultsMessage={s.picker.empty}
      options={opsi.map((d) => ({
        value: d,
        query: `${d} ${label(d)}`,
        content: (
          <span className="flex w-full items-center justify-between gap-2">
            <span className="truncate">{label(d)}</span>
            {nama[d] && <span className="shrink-0 text-11 text-tertiary">{d}</span>}
          </span>
        ),
      }))}
      footerOption={
        <div className="flex items-center justify-between border-t border-subtle px-2 pt-1.5">
          <button type="button" onClick={() => onUbah([...opsi])} className="text-11 font-medium text-accent-primary">
            {s.picker.select_all}
          </button>
          <button type="button" onClick={() => onUbah([])} className="text-11 font-medium text-secondary">
            {s.picker.clear}
          </button>
        </div>
      }
    />
  );
}
