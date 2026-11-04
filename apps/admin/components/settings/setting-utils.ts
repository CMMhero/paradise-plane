/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: helpers for registry-driven settings
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Values are strings end to end ("0"/"1", "30", "08:30", "-3,0,3", "1,2,3"),
 * exactly as the server stores them. These helpers only parse for display and
 * give early feedback; the server validates again and wins.
 */

import type { TInstanceSetting } from "@plane/types";
import type { TGodmodeStrings } from "@/app/i18n/godmode";

type TSettingStrings = TGodmodeStrings["settings"];

export const DAY_LIST_MIN = -30;
export const DAY_LIST_MAX = 30;
export const DAY_LIST_MAX_ITEMS = 12;

const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;

/** "-3, 0 ,3" -> [-3, 0, 3]; null when any token is not a whole number. */
export function parseDayList(raw: string): number[] | null {
  const tokens = raw
    .split(",")
    .map((t) => t.trim())
    .filter((t) => t !== "");
  if (tokens.length === 0) return [];
  const numbers = tokens.map((t) => (/^-?\d+$/.test(t) ? Number(t) : Number.NaN));
  return numbers.some(Number.isNaN) ? null : numbers;
}

/** Canonical server form: unique, sorted, comma separated without spaces. */
export function normalizeDayList(raw: string): string {
  const parsed = parseDayList(raw);
  if (!parsed) return raw.trim();
  return (
    [...new Set(parsed)]
      // oxlint-disable-next-line unicorn/no-array-sort -- lib ES2022 has no toSorted; array is already a local copy
      .sort((a, b) => a - b)
      .join(",")
  );
}

export function parseWeekdays(raw: string): number[] {
  return raw
    .split(",")
    .map((t) => Number(t.trim()))
    .filter((n) => Number.isInteger(n) && n >= 1 && n <= 7);
}

export function formatWeekdays(days: number[]): string {
  return (
    [...new Set(days)]
      // oxlint-disable-next-line unicorn/no-array-sort -- lib ES2022 has no toSorted; array is already a local copy
      .sort((a, b) => a - b)
      .join(",")
  );
}

/** Canonical form used to compare a draft with the saved value. */
export function normalizeValue(def: TInstanceSetting, raw: string): string {
  switch (def.kind) {
    case "day_list":
      return normalizeDayList(raw);
    case "weekday_set":
      return formatWeekdays(parseWeekdays(raw));
    case "number":
    case "choice":
      return raw.trim();
    default:
      return raw;
  }
}

/** Returns an error message, or null when the draft looks acceptable. */
export function validateValue(def: TInstanceSetting, raw: string, t: TSettingStrings): string | null {
  const v = raw.trim();
  switch (def.kind) {
    case "toggle":
      return null;
    case "number": {
      if (!/^\d+$/.test(v)) {
        return def.min !== null && def.max !== null
          ? t.validation.number.replace("{min}", String(def.min)).replace("{max}", String(def.max))
          : t.validation.number_plain;
      }
      const n = Number(v);
      if ((def.min !== null && n < def.min) || (def.max !== null && n > def.max)) {
        return t.validation.number.replace("{min}", String(def.min ?? 0)).replace("{max}", String(def.max ?? n));
      }
      return null;
    }
    case "choice":
      return def.choices?.includes(Number(v)) ? null : t.validation.choice;
    case "time":
      return TIME_PATTERN.test(v) ? null : t.validation.time;
    case "day_list": {
      const parsed = parseDayList(v);
      const ok =
        parsed !== null &&
        parsed.length >= 1 &&
        parsed.length <= DAY_LIST_MAX_ITEMS &&
        new Set(parsed).size === parsed.length &&
        parsed.every((n) => n >= DAY_LIST_MIN && n <= DAY_LIST_MAX);
      return ok ? null : t.validation.day_list;
    }
    case "weekday_set":
      return parseWeekdays(v).length > 0 ? null : t.validation.weekday_set;
    case "timezone":
      return v ? null : t.validation.timezone;
    default:
      return null;
  }
}

/** Human label of a choice value; unknown values (added by a newer server) get a generic one. */
export function choiceLabel(t: TSettingStrings, key: string, value: number): string {
  const label = t.choices[key]?.[value];
  if (label) return label;
  if (key === "AUTO_ARCHIVE_DONE_DAYS") {
    return value === 0 ? t.controls.archive_off : t.controls.archive_after.replace("{count}", String(value));
  }
  return t.controls.option.replace("{n}", String(value));
}

/** "3d before, on the day, 7d after" for a day list. */
export function describeDayList(t: TSettingStrings, raw: string): string {
  const parsed = parseDayList(raw);
  if (!parsed) return "";
  return (
    [...new Set(parsed)]
      // oxlint-disable-next-line unicorn/no-array-sort -- lib ES2022 has no toSorted; array is already a local copy
      .sort((a, b) => a - b)
      .map((n) =>
        n === 0
          ? t.controls.day_list_summary_on
          : n < 0
            ? t.controls.day_list_summary_before.replace("{n}", String(-n))
            : t.controls.day_list_summary_after.replace("{n}", String(n))
      )
      .join(", ")
  );
}

/** Text shown after "Default:" for a setting's default value. */
export function formatSettingValue(
  def: TInstanceSetting,
  raw: string,
  t: TSettingStrings,
  unit: string | undefined
): string {
  switch (def.kind) {
    case "toggle":
      return raw === "1" ? t.controls.on : t.controls.off;
    case "number":
      return unit ? `${raw} ${unit}` : raw;
    case "choice":
      return choiceLabel(t, def.key, Number(raw));
    case "weekday_set":
      return (
        parseWeekdays(raw)
          // oxlint-disable-next-line unicorn/no-array-sort -- lib ES2022 has no toSorted; array is already a local copy
          .sort((a, b) => a - b)
          .map((d) => t.weekdays[d - 1])
          .join(", ")
      );
    case "day_list":
      return raw;
    default:
      return raw;
  }
}

/** Name and help line of a registry key, including the module switches. */
export function describeField(t: TSettingStrings, key: string): { name: string; help: string } {
  const field = t.fields[key];
  if (field) return field;
  const moduleName = key.startsWith("ENABLE_") ? key.slice("ENABLE_".length).toLowerCase() : "";
  const mod = (t.modules as Record<string, { name: string; desc: string } | undefined>)[moduleName];
  if (mod) return { name: mod.name, help: mod.desc };
  return { name: key, help: "" };
}
