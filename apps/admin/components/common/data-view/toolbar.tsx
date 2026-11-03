/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: toolbar daftar God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Cari + Filters + Display di satu baris, baris filter aktif di bawahnya.
 * Menu Display meniru header work item: Ordering, Display properties (pil
 * kolom), dan jumlah baris per halaman.
 */

import type { ReactNode } from "react";
import { ArrowDownWideNarrow, ArrowUpNarrowWide, Search, SlidersHorizontal, X } from "lucide-react";
// plane imports
import { Button } from "@plane/propel/button";
import { Popover } from "@plane/propel/popover";
import { CustomSelect, Input } from "@plane/ui";
import { cn } from "@plane/utils";
// local
import { AddFilterButton, FiltersRow } from "./filter-bar";
import type { TFilterField, TSortDir } from "./model";
import { PER_PAGE_OPTIONS } from "./model";
import type { TViewController } from "./use-view-state";

export type TColumnToggle = { key: string; label: string };
export type TSortOption = { key: string; label: string };

export function SearchBox({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  return (
    <div className="flex h-8 min-w-[220px] flex-1 items-center gap-1.5 search-field border border-subtle bg-layer-2 px-2 focus-within:border-accent-strong sm:max-w-sm">
      <Search className="size-3.5 shrink-0 text-placeholder" aria-hidden />
      <Input
        type="text"
        mode="true-transparent"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Escape" && onChange("")}
        placeholder={placeholder}
        aria-label={placeholder}
        className="w-full p-0 text-primary placeholder:text-placeholder"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          aria-label="Clear search"
          className="text-placeholder hover:text-tertiary"
        >
          <X className="size-3.5" />
        </button>
      )}
    </div>
  );
}

function JudulBagian({ children }: { children: ReactNode }) {
  return <div className="text-caption-sm-medium text-placeholder">{children}</div>;
}

const pil = (aktif: boolean) =>
  cn("rounded-control border px-2 py-0.5 text-11 transition-all", {
    "border-accent-strong bg-accent-primary text-on-color": aktif,
    "border-subtle text-secondary hover:bg-layer-1": !aktif,
  });

export function DisplayMenu({
  view,
  sortOptions,
  columns,
  showPerPage = true,
}: {
  view: TViewController;
  sortOptions: TSortOption[];
  columns: TColumnToggle[];
  showPerPage?: boolean;
}) {
  const urutan = sortOptions.find((o) => o.key === view.sort.key);
  const arah = (dir: TSortDir) => view.setSort({ ...view.sort, dir });
  const diubah = view.hidden.length > 0;

  return (
    <Popover>
      <Popover.Button
        render={
          <Button variant="secondary" size="lg" prependIcon={<SlidersHorizontal />}>
            Display
          </Button>
        }
      />
      <Popover.Panel
        side="bottom"
        align="end"
        positionerClassName="z-30"
        className="w-[18.75rem] space-y-4 rounded-popover border border-subtle bg-surface-1 p-3 shadow-raised-200"
      >
        {sortOptions.length > 0 && (
          <div className="space-y-1.5">
            <JudulBagian>Ordering</JudulBagian>
            <div className="flex items-center gap-2">
              <CustomSelect
                value={view.sort.key}
                label={urutan?.label ?? "—"}
                onChange={(key: string) => view.setSort({ ...view.sort, key })}
                className="flex-1"
                input
              >
                {sortOptions.map((o) => (
                  <CustomSelect.Option key={o.key} value={o.key}>
                    {o.label}
                  </CustomSelect.Option>
                ))}
              </CustomSelect>
              <div className="flex overflow-hidden rounded-button border border-subtle">
                {(["asc", "desc"] as const).map((dir) => {
                  const Ikon = dir === "asc" ? ArrowUpNarrowWide : ArrowDownWideNarrow;
                  return (
                    <button
                      key={dir}
                      type="button"
                      aria-label={dir === "asc" ? "Ascending" : "Descending"}
                      aria-pressed={view.sort.dir === dir}
                      onClick={() => arah(dir)}
                      className={cn("grid size-7 place-items-center", {
                        "bg-layer-transparent-active text-primary": view.sort.dir === dir,
                        "text-tertiary hover:bg-layer-1-hover": view.sort.dir !== dir,
                      })}
                    >
                      <Ikon className="size-3.5" />
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {columns.length > 0 && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <JudulBagian>Display properties</JudulBagian>
              {diubah && (
                <button
                  type="button"
                  className="text-11 text-accent-primary hover:underline"
                  onClick={() => view.hidden.forEach((h) => view.toggleColumn(h))}
                >
                  Show all
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {columns.map((c) => (
                <button
                  key={c.key}
                  type="button"
                  aria-pressed={!view.hidden.includes(c.key)}
                  className={pil(!view.hidden.includes(c.key))}
                  onClick={() => view.toggleColumn(c.key)}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {showPerPage && (
          <div className="space-y-1.5">
            <JudulBagian>Rows per page</JudulBagian>
            <div className="flex flex-wrap gap-2">
              {PER_PAGE_OPTIONS.map((n) => (
                <button
                  key={n}
                  type="button"
                  aria-pressed={view.perPage === n}
                  className={pil(view.perPage === n)}
                  onClick={() => view.setPerPage(n)}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
        )}
      </Popover.Panel>
    </Popover>
  );
}

/** Toolbar lengkap: cari, Filters, Display, ringkasan di kanan, lalu baris filter aktif. */
export function ViewToolbar<Row>({
  view,
  fields,
  searchPlaceholder,
  sortOptions,
  columns,
  summary,
  extra,
  showPerPage,
}: {
  view: TViewController;
  fields: TFilterField<Row>[];
  searchPlaceholder: string;
  sortOptions: TSortOption[];
  columns: TColumnToggle[];
  /** Mis. "42 of 79 accounts". */
  summary?: ReactNode;
  /** Kontrol tambahan khusus halaman, di kiri tombol Filters. */
  extra?: ReactNode;
  showPerPage?: boolean;
}) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <SearchBox value={view.search} onChange={view.setSearch} placeholder={searchPlaceholder} />
        {extra}
        <div className="ml-auto flex items-center gap-2">
          {summary && <span className="text-13 whitespace-nowrap text-tertiary">{summary}</span>}
          <AddFilterButton fields={fields} conditions={view.conditions} onAdd={view.addCondition} label="Filters" />
          <DisplayMenu view={view} sortOptions={sortOptions} columns={columns} showPerPage={showPerPage} />
        </div>
      </div>
      <FiltersRow
        fields={fields}
        conditions={view.conditions}
        onAdd={view.addCondition}
        onChange={view.updateCondition}
        onRemove={view.removeCondition}
        onClear={view.clearConditions}
      />
    </div>
  );
}
