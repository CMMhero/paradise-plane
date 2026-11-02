/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: baris filter God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tampilan dan perilaku mengikuti rich filters work item di apps/web
 * (components/rich-filters): chip `properti | operator | nilai | x`, tombol
 * tambah filter yang hanya menawarkan properti yang belum dipakai, dan nilai
 * yang langsung terbuka saat chip baru ditambahkan.
 */

import { useState } from "react";
import { CalendarDays, ListFilter, ListFilterPlus, X } from "lucide-react";
// plane imports
import { Button, getButtonStyling } from "@plane/propel/button";
import { Popover } from "@plane/propel/popover";
import { CustomSearchSelect } from "@plane/ui";
import { cn } from "@plane/utils";
// local
import type { TCondition, TFilterField, TFilterOperator } from "./model";
import { DATE_PRESETS, OPERATOR_LABEL, describeDate, operatorsFor } from "./model";

const GARIS = "border-r border-subtle";
const KOSONG = "--";

type TAddFilterProps<Row> = {
  fields: TFilterField<Row>[];
  conditions: TCondition[];
  onAdd: (field: string) => void;
  /** Tanpa label = tombol ikon saja (dipakai di dalam baris filter). */
  label?: string;
  size?: "sm" | "base";
};

export function AddFilterButton<Row>({ fields, conditions, onAdd, label, size = "base" }: TAddFilterProps<Row>) {
  const dipakai = new Set(conditions.map((c) => c.field));
  const sisa = fields.filter((f) => !dipakai.has(f.key));
  const options =
    sisa.length === 0
      ? [
          {
            value: "__all__",
            query: "all filters applied",
            content: <span className="text-placeholder italic">All filters applied</span>,
            disabled: true,
          },
        ]
      : sisa.map((f) => ({
          value: f.key,
          query: f.label.toLowerCase(),
          content: (
            <span className="flex items-center gap-2 text-secondary">
              <f.icon className="size-3.5 text-tertiary" />
              {f.label}
            </span>
          ),
        }));
  const Ikon = label ? ListFilter : ListFilterPlus;

  return (
    <CustomSearchSelect
      value=""
      onChange={(v: string) => v !== "__all__" && onAdd(v)}
      options={options}
      optionsClassName="w-56"
      maxHeight="2xl"
      placement="bottom-start"
      customButtonClassName={cn(getButtonStyling("secondary", size), "py-[5px]")}
      customButton={
        <span className="flex items-center gap-1" aria-label={label ?? "Add filter"}>
          <Ikon className="size-3.5 text-secondary" />
          {label}
        </span>
      }
    />
  );
}

type TChipProps<Row> = {
  field: TFilterField<Row>;
  condition: TCondition;
  onChange: (patch: Partial<Omit<TCondition, "field">>) => void;
  onRemove: () => void;
};

export function FilterChip<Row>({ field, condition, onChange, onRemove }: TChipProps<Row>) {
  const operators = operatorsFor(field);
  const Ikon = field.icon;

  return (
    <div className="flex h-7 items-stretch overflow-hidden rounded-sm border border-subtle bg-surface-1">
      <div className={cn("flex items-center gap-1 px-2 text-11 text-tertiary", GARIS)}>
        <Ikon className="size-3.5 shrink-0" />
        <span className="truncate">{field.label}</span>
      </div>

      {operators.length > 1 ? (
        <CustomSearchSelect
          value={condition.operator}
          onChange={(op: TFilterOperator) => onChange({ operator: op })}
          options={operators.map((op) => ({ value: op, query: OPERATOR_LABEL[op], content: OPERATOR_LABEL[op] }))}
          className={GARIS}
          customButtonClassName="h-full px-2 text-13"
          optionsClassName="w-40"
          customButton={<span className="flex h-full items-center">{OPERATOR_LABEL[condition.operator]}</span>}
        />
      ) : (
        <span className={cn("flex items-center px-2 text-13", GARIS)}>{OPERATOR_LABEL[condition.operator]}</span>
      )}

      {field.kind === "select" && <NilaiPilihan field={field} condition={condition} onChange={onChange} />}
      {field.kind === "date" && <NilaiTanggal condition={condition} onChange={onChange} />}
      {field.kind === "text" && <NilaiTeks condition={condition} onChange={onChange} />}

      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove ${field.label} filter`}
        className="px-1.5 text-placeholder hover:bg-layer-transparent-hover hover:text-tertiary focus:outline-none"
      >
        <X className="size-3.5" />
      </button>
    </div>
  );
}

function NilaiPilihan<Row>({
  field,
  condition,
  onChange,
}: {
  field: TFilterField<Row>;
  condition: TCondition;
  onChange: TChipProps<Row>["onChange"];
}) {
  const options = field.options ?? [];
  const terpilih = condition.value.map((v) => options.find((o) => o.value === v)?.label ?? v);
  const tampil =
    terpilih.length === 0 ? (
      <span className="text-placeholder">{KOSONG}</span>
    ) : (
      <span className="flex items-center gap-1 whitespace-nowrap">
        <span className="max-w-48 truncate">{terpilih.slice(0, 2).join(", ")}</span>
        {terpilih.length > 2 && <span className="text-tertiary">+{terpilih.length - 2} more</span>}
      </span>
    );

  return (
    <CustomSearchSelect
      multiple
      value={condition.value}
      onChange={(v: string[]) => onChange({ value: v })}
      options={options.map((o) => ({ value: o.value, query: o.label.toLowerCase(), content: o.label }))}
      className={GARIS}
      customButtonClassName="h-full w-full px-2 text-13"
      optionsClassName="w-60"
      maxHeight="md"
      defaultOpen={condition.value.length === 0}
      noResultsMessage="No matching values"
      customButton={<span className="flex h-full items-center">{tampil}</span>}
    />
  );
}

function NilaiTanggal({
  condition,
  onChange,
}: {
  condition: TCondition;
  onChange: (patch: Partial<Omit<TCondition, "field">>) => void;
}) {
  const [buka, setBuka] = useState(condition.value.length === 0);
  const [dari = "", sampai = ""] = condition.value;
  const rentang = condition.operator === "between";
  const teks = describeDate(condition);

  return (
    <Popover open={buka} onOpenChange={setBuka}>
      <Popover.Button
        className={cn("flex h-full items-center gap-1 px-2 text-13 hover:bg-layer-transparent-hover", GARIS)}
      >
        <CalendarDays className="size-3.5 text-tertiary" />
        {teks ? <span className="whitespace-nowrap">{teks}</span> : <span className="text-placeholder">{KOSONG}</span>}
      </Popover.Button>
      <Popover.Panel
        side="bottom"
        align="start"
        positionerClassName="z-30"
        className="w-64 space-y-3 rounded-md border border-subtle bg-surface-1 p-3 shadow-raised-100"
      >
        {rentang && (
          <div className="grid grid-cols-2 gap-1">
            {DATE_PRESETS.map((p) => (
              <button
                key={p.key}
                type="button"
                className="rounded-sm px-2 py-1 text-left text-12 text-secondary hover:bg-layer-transparent-hover"
                onClick={() => {
                  onChange({ value: p.range() });
                  setBuka(false);
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
        )}
        <div className="space-y-2">
          <label className="block space-y-1 text-11 text-tertiary">
            <span>{rentang ? "From" : "Date"}</span>
            <input
              type="date"
              value={dari}
              max={rentang ? sampai || undefined : undefined}
              onChange={(e) => onChange({ value: rentang ? [e.target.value, sampai] : [e.target.value] })}
              className="w-full rounded-sm border border-subtle bg-layer-1 px-2 py-1 text-13 text-primary"
            />
          </label>
          {rentang && (
            <label className="block space-y-1 text-11 text-tertiary">
              <span>To</span>
              <input
                type="date"
                value={sampai}
                min={dari || undefined}
                onChange={(e) => onChange({ value: [dari, e.target.value] })}
                className="w-full rounded-sm border border-subtle bg-layer-1 px-2 py-1 text-13 text-primary"
              />
            </label>
          )}
        </div>
      </Popover.Panel>
    </Popover>
  );
}

function NilaiTeks({
  condition,
  onChange,
}: {
  condition: TCondition;
  onChange: (patch: Partial<Omit<TCondition, "field">>) => void;
}) {
  return (
    <input
      type="text"
      value={condition.value[0] ?? ""}
      onChange={(e) => onChange({ value: [e.target.value] })}
      placeholder="Type a value"
      aria-label="Filter value"
      // oxlint-disable-next-line jsx-a11y/no-autofocus -- chip baru langsung diketik, sama dengan apps/web
      autoFocus={condition.value.length === 0}
      className={cn("w-36 bg-transparent px-2 text-13 text-primary outline-none placeholder:text-placeholder", GARIS)}
    />
  );
}

type TFiltersRowProps<Row> = {
  fields: TFilterField<Row>[];
  conditions: TCondition[];
  onAdd: (field: string) => void;
  onChange: (field: string, patch: Partial<Omit<TCondition, "field">>) => void;
  onRemove: (field: string) => void;
  onClear: () => void;
};

/** Baris kondisi aktif di bawah toolbar. Tidak tampil kalau belum ada kondisi. */
export function FiltersRow<Row>({ fields, conditions, onAdd, onChange, onRemove, onClear }: TFiltersRowProps<Row>) {
  const tampil = conditions
    .map((c) => ({ c, f: fields.find((f) => f.key === c.field) }))
    .filter((x): x is { c: TCondition; f: TFilterField<Row> } => Boolean(x.f));
  if (tampil.length === 0) return null;

  return (
    <div className="flex w-full items-start gap-2 rounded-lg bg-layer-1 px-3 py-2">
      <div className="flex w-full flex-wrap items-center gap-2">
        {tampil.map(({ c, f }) => (
          <FilterChip
            key={c.field}
            field={f}
            condition={c}
            onChange={(patch) => onChange(c.field, patch)}
            onRemove={() => onRemove(c.field)}
          />
        ))}
        <AddFilterButton fields={fields} conditions={conditions} onAdd={onAdd} size="sm" />
      </div>
      <div className="flex shrink-0 items-center border-l border-subtle pl-3">
        <Button variant="secondary" size="sm" className="py-1" onClick={onClear}>
          Clear all
        </Button>
      </div>
    </div>
  );
}
