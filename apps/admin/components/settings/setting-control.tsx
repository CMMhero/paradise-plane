/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: one control per registry setting kind
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * toggle, number, choice, time, day_list, weekday_set, timezone. The control
 * edits a string draft; validation messages and the default hint are shown by
 * the row around it (setting-row.tsx).
 */

import { Button } from "@plane/propel/button";
import type { TInstanceSetting } from "@plane/types";
import { CustomSearchSelect, CustomSelect, Input, ToggleSwitch } from "@plane/ui";
import { cn } from "@plane/utils";
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { useZonaWaktu } from "@/app/(all)/(dashboard)/members/bidang-profil";
import { inputClass } from "@/components/common/paradise-styles";
import { choiceLabel, formatWeekdays, parseWeekdays } from "./setting-utils";

type Props = {
  def: TInstanceSetting;
  value: string;
  onChange: (value: string) => void;
  label: string;
  unit?: string;
  invalid: boolean;
  disabled: boolean;
};

function TimezoneControl({
  value,
  onChange,
  label,
  disabled,
}: Pick<Props, "value" | "onChange" | "label" | "disabled">) {
  const { s } = useGodmodeStrings();
  const zones = useZonaWaktu();
  // The saved value may be missing from the list (or the list failed to load): keep it selectable.
  const options = zones.some((z) => z.value === value) ? zones : [{ value, label: value, utc_offset: "" }, ...zones];
  return (
    <CustomSearchSelect
      value={value}
      label={options.find((z) => z.value === value)?.label ?? (value || s.settings.controls.choose_timezone)}
      onChange={(v: string) => onChange(v)}
      buttonClassName="w-full md:w-72"
      input
      disabled={disabled}
      maxHeight="lg"
      options={options.map((z) => ({
        value: z.value,
        query: `${z.label} ${z.value} ${z.utc_offset}`,
        content: (
          <span className="flex w-full items-center justify-between gap-2">
            <span className="truncate">{z.label}</span>
            {z.utc_offset && <span className="shrink-0 text-11 text-tertiary">{z.utc_offset}</span>}
          </span>
        ),
      }))}
      aria-label={label}
    />
  );
}

export function SettingControl({ def, value, onChange, label, unit, invalid, disabled }: Props) {
  const { s } = useGodmodeStrings();
  const t = s.settings;

  switch (def.kind) {
    case "toggle":
      return (
        <ToggleSwitch
          value={value === "1"}
          onChange={() => onChange(value === "1" ? "0" : "1")}
          size="sm"
          disabled={disabled}
          label={label}
        />
      );

    case "number":
      return (
        <div className="flex items-center gap-2">
          <Input
            type="number"
            inputMode="numeric"
            min={def.min ?? undefined}
            max={def.max ?? undefined}
            value={value}
            aria-label={label}
            aria-invalid={invalid}
            disabled={disabled}
            onChange={(e) => onChange(e.target.value)}
            className={cn(inputClass, "w-24 text-right", { "border-danger-strong": invalid })}
          />
          {unit && <span className="w-20 text-13 text-tertiary">{unit}</span>}
        </div>
      );

    case "choice":
      return (
        <CustomSelect
          value={Number(value)}
          label={choiceLabel(t, def.key, Number(value))}
          onChange={(v: number) => onChange(String(v))}
          buttonClassName="w-full md:w-72"
          disabled={disabled}
          input
        >
          {(def.choices ?? []).map((n) => (
            <CustomSelect.Option key={n} value={n}>
              {choiceLabel(t, def.key, n)}
            </CustomSelect.Option>
          ))}
        </CustomSelect>
      );

    case "time":
      return (
        <Input
          type="time"
          // The scheduler ticks every 5 minutes; the server rejects other minutes and
          // anything after 23:50 (setelan_instance._jam).
          step={300}
          max="23:50"
          value={value}
          aria-label={label}
          aria-invalid={invalid}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          className={cn(inputClass, "w-full md:w-32", { "border-danger-strong": invalid })}
        />
      );

    case "day_list":
      return (
        <Input
          type="text"
          value={value}
          placeholder={t.controls.day_list_placeholder}
          aria-label={label}
          aria-invalid={invalid}
          disabled={disabled}
          onChange={(e) => onChange(e.target.value)}
          className={cn(inputClass, "w-full md:w-56", { "border-danger-strong": invalid })}
        />
      );

    case "weekday_set": {
      const selected = parseWeekdays(value);
      return (
        <fieldset className="m-0 flex flex-wrap gap-1 border-0 p-0 md:justify-end">
          <legend className="sr-only">{label}</legend>
          {t.weekdays.map((name, i) => {
            const day = i + 1;
            const isOn = selected.includes(day);
            return (
              <Button
                key={name}
                variant={isOn ? "primary" : "secondary"}
                size="base"
                aria-pressed={isOn}
                disabled={disabled}
                onClick={() => onChange(formatWeekdays(isOn ? selected.filter((d) => d !== day) : [...selected, day]))}
              >
                {name}
              </Button>
            );
          })}
        </fieldset>
      );
    }

    case "timezone":
      return <TimezoneControl value={value} onChange={onChange} label={label} disabled={disabled} />;

    default:
      return null;
  }
}
