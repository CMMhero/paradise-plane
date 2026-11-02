/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: setelan angka di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { Button } from "@plane/propel/button";
import { cn } from "@plane/utils";
import { inputClass } from "@/components/common/paradise-styles";
import { useGodmodeStrings } from "@/app/i18n/godmode";

type Props = {
  value: number;
  min: number;
  max: number;
  unit: string;
  label: string;
  isDisabled: boolean;
  onSave: (value: number) => Promise<void>;
};

/**
 * Kotak angka + tombol Save yang hanya aktif kalau nilainya berubah dan sah.
 * Rentang yang sama dijaga server (SETELAN_ANGKA di saklar_instance.py); di
 * sini hanya supaya orang tahu salahnya sebelum menekan Save.
 */
export function InputAngka({ value, min, max, unit, label, isDisabled, onSave }: Props) {
  const { s, fill } = useGodmodeStrings();
  const [draft, setDraft] = useState(String(value));
  const [lastValue, setLastValue] = useState(value);
  // Nilai server berubah (mis. disimpan di tab lain) -> ikuti, tanpa efek.
  if (value !== lastValue) {
    setLastValue(value);
    setDraft(String(value));
  }

  const angka = Number(draft);
  const isValid = /^\d+$/.test(draft.trim()) && angka >= min && angka <= max;
  const isDirty = draft.trim() !== String(value);

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-2">
        <input
          type="number"
          inputMode="numeric"
          min={min}
          max={max}
          value={draft}
          aria-label={label}
          aria-invalid={!isValid}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && isValid && isDirty) void onSave(angka);
          }}
          className={cn(inputClass, "w-24 text-right", { "border-danger-strong": !isValid })}
        />
        <span className="w-14 text-13 text-tertiary">{unit}</span>
        <Button
          variant="secondary"
          size="sm"
          disabled={isDisabled || !isValid || !isDirty}
          onClick={() => void onSave(angka)}
        >
          {s.common.save}
        </Button>
      </div>
      {!isValid && <p className="text-11 text-danger-primary">{fill(s.fitur.out_of_range, { min, max })}</p>}
    </div>
  );
}
