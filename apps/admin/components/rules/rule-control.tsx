/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: one control per registry rule kind
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * bool = switch, int = number input, choice and level = select, text = text
 * input, list_of_keys = checkbox list (an ordered list also shows its selected
 * items first, each with Move up and Move down buttons). Which kind gets which control is the
 * table RULE_KIND_CONTROLS in rules-model.ts. The row around the control owns
 * the label, the help text and the error line; the control only points at them
 * with aria-describedby.
 */

import { Checkbox, ToggleSwitch } from "@plane/ui";
import type { TParadiseRuleValue, TRegistryRule } from "@plane/types";
import { cn } from "@plane/utils";
import { ArrowDown, ArrowUp } from "lucide-react";
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { inputClass } from "@/components/common/paradise-styles";
import { RULE_KIND_CONTROLS, choiceValue, moveItem } from "./rules-model";

type Props = {
  rule: TRegistryRule;
  value: TParadiseRuleValue;
  onChange: (value: TParadiseRuleValue) => void;
  /** Name of the rule, for the control's accessible name. */
  label: string;
  /** DOM id of the control, so the row's label can point at it. */
  controlId: string;
  describedBy?: string;
  invalid: boolean;
  disabled: boolean;
};

const fieldClass = (invalid: boolean) =>
  cn(inputClass, "min-h-11 w-full focus-visible:ring-2 focus-visible:ring-accent-strong focus-visible:outline-none", {
    "border-danger-strong": invalid,
  });

const focusRingClass = "focus-visible:ring-2 focus-visible:ring-accent-strong focus-visible:outline-none";

const moveButtonClass = cn(
  "inline-flex size-11 shrink-0 items-center justify-center rounded-field text-secondary hover:bg-layer-1 disabled:cursor-not-allowed disabled:opacity-40",
  focusRingClass
);

/** Digits (and a leading minus) become a number; anything else stays text so the row can flag it. */
const parseIntDraft = (raw: string): TParadiseRuleValue => (/^-?\d+$/.test(raw.trim()) ? Number(raw.trim()) : raw);

export function RuleControl({ rule, value, onChange, label, controlId, describedBy, invalid, disabled }: Props) {
  const { s, fill } = useGodmodeStrings();
  const t = s.settings.allRules;

  switch (RULE_KIND_CONTROLS[rule.kind]) {
    case "switch": {
      const on = value === true;
      return (
        <div className="flex min-h-11 items-center gap-3">
          <ToggleSwitch value={on} onChange={(next) => onChange(next)} size="md" disabled={disabled} label={label} />
          <span className="w-8 text-13 text-secondary" aria-hidden>
            {on ? t.on : t.off}
          </span>
        </div>
      );
    }

    case "number":
      return (
        <input
          id={controlId}
          type="number"
          inputMode="numeric"
          min={rule.min ?? undefined}
          max={rule.max ?? undefined}
          value={typeof value === "number" ? String(value) : String(value ?? "")}
          aria-invalid={invalid}
          aria-describedby={describedBy}
          disabled={disabled}
          onChange={(e) => onChange(parseIntDraft(e.target.value))}
          className={cn(fieldClass(invalid), "sm:w-32 sm:text-right")}
        />
      );

    case "select": {
      const choices = rule.choices ?? [];
      // A saved value the server no longer offers stays visible instead of silently jumping to the first option.
      const known = choices.some((c) => String(c.value) === String(value));
      return (
        <select
          id={controlId}
          value={String(value)}
          aria-invalid={invalid}
          aria-describedby={describedBy}
          disabled={disabled}
          onChange={(e) => {
            const next = choiceValue(rule, e.target.value);
            if (next !== undefined) onChange(next);
          }}
          className={cn(fieldClass(invalid), "sm:w-72")}
        >
          {!known && <option value={String(value)}>{String(value)}</option>}
          {choices.map((c) => (
            <option key={String(c.value)} value={String(c.value)}>
              {c.label}
            </option>
          ))}
        </select>
      );
    }

    case "text": {
      const text = typeof value === "string" ? value : String(value ?? "");
      return (
        <div className="space-y-1">
          <input
            id={controlId}
            type="text"
            value={text}
            aria-invalid={invalid}
            aria-describedby={describedBy}
            disabled={disabled}
            onChange={(e) => onChange(e.target.value)}
            className={cn(fieldClass(invalid), "sm:w-72")}
          />
          {rule.max_length !== null && (
            <p className="text-11 text-tertiary sm:text-right">
              {t.text_counter.replace("{used}", String(text.length)).replace("{max}", String(rule.max_length))}
            </p>
          )}
        </div>
      );
    }

    case "checkbox-list": {
      const selected = Array.isArray(value) ? value : [];
      const choices = rule.choices ?? [];
      const labelOf = (key: string): string => choices.find((c) => String(c.value) === key)?.label ?? key;
      const optionClass =
        "flex min-h-11 min-w-0 flex-1 cursor-pointer items-center gap-2 text-13 text-primary has-[:focus-visible]:rounded-field has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent-strong";
      const renderOption = (key: string, checked: boolean) => (
        <label className={optionClass}>
          <Checkbox
            checked={checked}
            disabled={disabled}
            onChange={() => onChange(checked ? selected.filter((x) => x !== key) : [...selected, key])}
          />
          {labelOf(key)}
        </label>
      );

      if (rule.ordered) {
        // Selected items first, in value order, then the ones that are off.
        const on = selected.filter((key) => choices.some((c) => String(c.value) === key));
        const off = choices.map((c) => String(c.value)).filter((key) => !selected.includes(key));
        return (
          <fieldset
            id={controlId}
            aria-describedby={describedBy}
            aria-invalid={invalid}
            disabled={disabled}
            className="m-0 flex flex-col border-0 p-0"
          >
            <legend className="sr-only">{label}</legend>
            {on.map((key, index) => (
              <div key={key} className="flex items-center gap-1">
                {renderOption(key, true)}
                <button
                  type="button"
                  className={moveButtonClass}
                  disabled={disabled || index === 0}
                  aria-label={fill(t.move_up, { name: labelOf(key) })}
                  onClick={() => onChange(moveItem(selected, selected.indexOf(key), -1))}
                >
                  <ArrowUp className="size-4" aria-hidden />
                </button>
                <button
                  type="button"
                  className={moveButtonClass}
                  disabled={disabled || index === on.length - 1}
                  aria-label={fill(t.move_down, { name: labelOf(key) })}
                  onClick={() => onChange(moveItem(selected, selected.indexOf(key), 1))}
                >
                  <ArrowDown className="size-4" aria-hidden />
                </button>
              </div>
            ))}
            {off.map((key) => (
              <div key={key} className="flex items-center gap-1">
                {renderOption(key, false)}
              </div>
            ))}
          </fieldset>
        );
      }

      return (
        <fieldset
          id={controlId}
          aria-describedby={describedBy}
          aria-invalid={invalid}
          disabled={disabled}
          className="m-0 flex flex-col border-0 p-0"
        >
          <legend className="sr-only">{label}</legend>
          {choices.map((c) => {
            const key = String(c.value);
            return (
              <div key={key} className="flex items-center">
                {renderOption(key, selected.includes(key))}
              </div>
            );
          })}
        </fieldset>
      );
    }

    default:
      return null;
  }
}
