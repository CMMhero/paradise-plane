/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tabel daftar God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tabel ala spreadsheet work item: kepala lengket, klik kepala kolom untuk
 * mengurutkan (klik lagi membalik arah), kolom bisa disembunyikan dari menu
 * Display. Opsional: kelompok baris (judul per hari) dan baris yang bisa dibuka.
 */

import { Fragment } from "react";
import type { ReactNode } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { cn } from "@plane/utils";
import type { TSort, TSortValue } from "./model";

export type TColumn<Row> = {
  key: string;
  label: string;
  render: (row: Row) => ReactNode;
  /** Nilai urut di klien. Halaman yang mengurutkan di server cukup `sortable: true`. */
  sortValue?: (row: Row) => TSortValue;
  sortable?: boolean;
  /** Kolom yang tak boleh disembunyikan (nama, aksi). */
  locked?: boolean;
  /** Kolom tanpa judul yang tampil (aksi). */
  srOnlyLabel?: boolean;
  className?: string;
  headClassName?: string;
};

type TProps<Row> = {
  rows: Row[];
  columns: TColumn<Row>[];
  hidden: string[];
  sort: TSort;
  onSort: (sort: TSort) => void;
  rowKey: (row: Row) => string;
  rowClassName?: (row: Row) => string | undefined;
  onRowClick?: (row: Row) => void;
  /** Baris tambahan di bawah baris yang sedang dibuka. */
  renderExpanded?: (row: Row) => ReactNode;
  /** Judul kelompok; baris berurutan dengan kunci yang sama digabung. */
  groupBy?: (row: Row) => { key: string; label: ReactNode } | null;
  minWidth?: number;
};

const visibleColumns = <Row,>(columns: TColumn<Row>[], hidden: string[]): TColumn<Row>[] =>
  columns.filter((c) => c.locked || !hidden.includes(c.key));

export function DataTable<Row>({
  rows,
  columns,
  hidden,
  sort,
  onSort,
  rowKey,
  rowClassName,
  onRowClick,
  renderExpanded,
  groupBy,
  minWidth = 720,
}: TProps<Row>) {
  const kolom = visibleColumns(columns, hidden);

  const kelompok: { key: string; label: ReactNode; rows: Row[] }[] = [];
  for (const row of rows) {
    const g = groupBy?.(row) ?? { key: "", label: null };
    const akhir = kelompok[kelompok.length - 1];
    if (akhir && akhir.key === g.key) akhir.rows.push(row);
    else kelompok.push({ key: g.key, label: g.label, rows: [row] });
  }

  return (
    <div className="max-h-[calc(100vh-17rem)] overflow-auto rounded-md border border-subtle">
      <table className="w-full text-13" style={{ minWidth }}>
        <thead className="sticky top-0 z-[1] bg-layer-1 text-tertiary">
          <tr>
            {kolom.map((c) => (
              <KepalaKolom key={c.key} column={c} sort={sort} onSort={onSort} />
            ))}
          </tr>
        </thead>
        <tbody>
          {kelompok.map((g) => (
            // Baris pertama unik, jadi kunci tetap unik walau satu hari muncul dua kali.
            <Fragment key={`${g.key}:${rowKey(g.rows[0])}`}>
              {g.label !== null && (
                <tr className="border-t border-subtle bg-layer-1">
                  <td colSpan={kolom.length} className="px-3 py-1.5 text-11 font-semibold tracking-wide text-tertiary">
                    {g.label} · {g.rows.length}
                  </td>
                </tr>
              )}
              {g.rows.map((row) => {
                const isi = renderExpanded?.(row);
                return (
                  <Fragment key={rowKey(row)}>
                    <tr
                      onClick={onRowClick ? () => onRowClick(row) : undefined}
                      className={cn(
                        "border-t border-subtle transition-colors hover:bg-layer-1-hover",
                        { "cursor-pointer": Boolean(onRowClick), "bg-layer-1": Boolean(isi) },
                        rowClassName?.(row)
                      )}
                    >
                      {kolom.map((c) => (
                        <td key={c.key} className={cn("px-3 py-2 align-middle", c.className)}>
                          {c.render(row)}
                        </td>
                      ))}
                    </tr>
                    {isi && (
                      <tr className="bg-layer-1">
                        <td colSpan={kolom.length} className="px-3 pt-1 pb-3">
                          {isi}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function KepalaKolom<Row>({
  column: c,
  sort,
  onSort,
}: {
  column: TColumn<Row>;
  sort: TSort;
  onSort: (s: TSort) => void;
}) {
  const bisaUrut = c.sortable || Boolean(c.sortValue);
  const aktif = sort.key === c.key;
  const Ikon = !aktif ? ArrowUpDown : sort.dir === "asc" ? ArrowUp : ArrowDown;

  return (
    <th
      className={cn("px-3 py-2 text-left font-medium whitespace-nowrap", c.headClassName)}
      aria-sort={aktif ? (sort.dir === "asc" ? "ascending" : "descending") : undefined}
    >
      {c.srOnlyLabel ? (
        <span className="sr-only">{c.label}</span>
      ) : bisaUrut ? (
        <button
          type="button"
          onClick={() => onSort({ key: c.key, dir: aktif && sort.dir === "asc" ? "desc" : "asc" })}
          className={cn("group -mx-1 inline-flex items-center gap-1 rounded-sm px-1 hover:text-secondary", {
            "text-primary": aktif,
          })}
        >
          {c.label}
          <Ikon className={cn("size-3 shrink-0", { "opacity-0 group-hover:opacity-100": !aktif })} aria-hidden />
        </button>
      ) : (
        c.label
      )}
    </th>
  );
}
