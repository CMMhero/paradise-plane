/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pure logic of the All rules screen
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * No React here. The screen only renders what these functions return, so the
 * grouping, the filters, the draft diff and the confirmation rule are tested
 * without a DOM (tests/rules-screen.test.ts).
 */

import type {
  TInstanceSetting,
  TInstanceSettingKind,
  TLegacyRule,
  TParadiseRuleValue,
  TRegistryRule,
  TRule,
  TRuleKind,
  TRulesResponse,
} from "@plane/types";
import type { TGodmodeStrings } from "@/app/i18n/godmode";
import { MENU_TABS } from "@/components/common/menu-tree";
import type { TTabId } from "@/components/common/menu-tree";
import { SETTINGS_LAYOUT } from "@/components/settings/layouts";
import type { TSettingsTabId } from "@/components/settings/layouts";
import { describeField, formatSettingValue } from "@/components/settings/setting-utils";

type TSettingStrings = TGodmodeStrings["settings"];
type TAllRulesStrings = TSettingStrings["allRules"];

/** One control per registry kind. The screen switches on this, so a new kind cannot ship without one. */
export type TRuleControl = "switch" | "number" | "select" | "text" | "checkbox-list";

export const RULE_KIND_CONTROLS: Record<TRuleKind, TRuleControl> = {
  bool: "switch",
  int: "number",
  choice: "select",
  level: "select",
  text: "text",
  list_of_keys: "checkbox-list",
};

/** Where a legacy rule is edited. */
export type TEditLink = { title: string; href: string };

export type TRuleEntry = {
  rule: TRule;
  /** Registry rules carry their own label; legacy rows take it from the God Mode strings. */
  name: string;
  help: string;
  /** Legacy rules only: the tab that owns the control. Null for "Other settings". */
  editOn: TEditLink | null;
  /** Legacy rules only: display unit of a number, from the layout row. */
  unit?: string;
};

export type TRuleSection = {
  id: string;
  source: "registry" | "legacy";
  title: string;
  description: string;
  entries: TRuleEntry[];
};

export const OTHER_SECTION_ID = "legacy:other";
export const sectionAnchor = (id: string): string => `rules-section-${id.replace(/[^a-zA-Z0-9_-]/g, "-")}`;

type TLegacyPlace = { tab: TTabId; unit?: string };

/** Which tab (and unit) every layout key lives on. The first tab that lists a key wins. */
function legacyPlaces(): { places: Map<string, TLegacyPlace>; tabOrder: TTabId[] } {
  const places = new Map<string, TLegacyPlace>();
  const tabOrder: TTabId[] = [];
  for (const tabs of Object.values(MENU_TABS)) {
    for (const tab of tabs) {
      if (!Object.hasOwn(SETTINGS_LAYOUT, tab.id)) continue;
      tabOrder.push(tab.id);
      for (const section of SETTINGS_LAYOUT[tab.id as TSettingsTabId]) {
        for (const row of section.rows) {
          if (!places.has(row.key)) places.set(row.key, { tab: tab.id, unit: row.unit });
        }
      }
    }
  }
  return { places, tabOrder };
}

const tabHref = (id: TTabId): string => {
  for (const tabs of Object.values(MENU_TABS)) {
    const tab = tabs.find((t) => t.id === id);
    if (tab) return tab.href;
  }
  return "/";
};

const registryEntry = (rule: TRegistryRule): TRuleEntry => ({
  rule,
  name: rule.label,
  help: rule.help,
  editOn: null,
});

/**
 * Registry rules by topic in the order of `groups`, then the older settings by
 * the tab that edits them, then whatever has no tab. Every rule appears exactly once.
 */
export function buildRuleSections(response: TRulesResponse, t: TSettingStrings): TRuleSection[] {
  const sections: TRuleSection[] = [];

  const registry = response.rules.filter((r): r is TRegistryRule => r.source === "registry");
  const legacy = response.rules.filter((r): r is TLegacyRule => r.source === "legacy");

  const knownGroups = new Set<string>();
  for (const group of response.groups) {
    knownGroups.add(group.id);
    const entries = registry.filter((r) => r.group === group.id).map(registryEntry);
    if (entries.length === 0) continue;
    sections.push({
      id: `group:${group.id}`,
      source: "registry",
      title: group.label,
      description: group.description,
      entries,
    });
  }

  // A rule whose topic the server did not list still has to show up.
  const strays = registry.filter((r) => !knownGroups.has(r.group));
  const strayIds = [...new Set(strays.map((r) => r.group))];
  for (const id of strayIds) {
    sections.push({
      id: `group:${id}`,
      source: "registry",
      title: id || t.allRules.groups_fallback,
      description: "",
      entries: strays.filter((r) => r.group === id).map(registryEntry),
    });
  }

  const { places, tabOrder } = legacyPlaces();
  const legacyEntry = (rule: TLegacyRule, tab: TTabId | null, unit?: string): TRuleEntry => {
    const { name, help } = describeField(t, rule.key);
    return {
      rule,
      name,
      help,
      editOn: tab ? { title: t.tabs[tab].title, href: tabHref(tab) } : null,
      unit: unit ? (t.units[unit] ?? unit) : undefined,
    };
  };

  const byKey = new Map(legacy.map((r) => [r.key, r]));
  const placed = new Set<string>();
  for (const tab of tabOrder) {
    const entries: TRuleEntry[] = [];
    for (const section of SETTINGS_LAYOUT[tab as TSettingsTabId]) {
      for (const row of section.rows) {
        const rule = byKey.get(row.key);
        if (!rule || placed.has(row.key) || places.get(row.key)?.tab !== tab) continue;
        placed.add(row.key);
        entries.push(legacyEntry(rule, tab, row.unit));
      }
    }
    if (entries.length === 0) continue;
    sections.push({
      id: `legacy:${tab}`,
      source: "legacy",
      title: t.tabs[tab].title,
      description: t.allRules.legacy_section_hint,
      entries,
    });
  }

  const others = legacy.filter((r) => !placed.has(r.key));
  if (others.length > 0) {
    sections.push({
      id: OTHER_SECTION_ID,
      source: "legacy",
      title: t.allRules.other_settings,
      description: t.allRules.other_settings_hint,
      entries: others.map((r) => legacyEntry(r, null)),
    });
  }

  return sections;
}

// ---- search and filters ----------------------------------------------------

export type TRuleFilter = { query: string; changedOnly: boolean };

const fold = (text: string): string => text.toLowerCase().normalize("NFKD").replace(/\p{M}/gu, "");

/** Every word of the query must appear in the key, the label, or the help text. */
export function matchesQuery(entry: TRuleEntry, query: string): boolean {
  const words = fold(query).split(/\s+/).filter(Boolean);
  if (words.length === 0) return true;
  const key = entry.rule.key.toLowerCase();
  const haystack = `${key} ${key.replaceAll("_", " ")} ${fold(entry.name)} ${fold(entry.help)}`;
  return words.every((w) => haystack.includes(w));
}

export function filterSections(
  sections: TRuleSection[],
  filter: TRuleFilter,
  isChanged: (entry: TRuleEntry) => boolean
): TRuleSection[] {
  const isFiltering = filter.query.trim() !== "" || filter.changedOnly;
  if (!isFiltering) return sections;
  return sections
    .map((section) => ({
      ...section,
      entries: section.entries.filter(
        (entry) => matchesQuery(entry, filter.query) && (!filter.changedOnly || isChanged(entry))
      ),
    }))
    .filter((section) => section.entries.length > 0);
}

export const countEntries = (sections: TRuleSection[]): number => sections.reduce((n, s) => n + s.entries.length, 0);

// ---- drafts ----------------------------------------------------------------

/** Unsaved edits by key. An int the person is still typing may be a string until it parses. */
export type TDraft = Record<string, TParadiseRuleValue>;

const sortedList = (v: TParadiseRuleValue): string =>
  Array.isArray(v)
    ? [...v]
        // oxlint-disable-next-line unicorn/no-array-sort -- lib ES2022 has no toSorted; array is already a local copy
        .sort()
        .join("\u0000")
    : "";

/** Same value? Lists compare as sets; choices compare by their text so 20 and "20" agree. */
export function valuesEqual(kind: TRuleKind, a: TParadiseRuleValue, b: TParadiseRuleValue): boolean {
  if (kind === "list_of_keys") return sortedList(a) === sortedList(b);
  if (kind === "choice" || kind === "level") return String(a) === String(b);
  return Object.is(a, b);
}

export const effectiveValue = (rule: TRegistryRule, draft: TDraft): TParadiseRuleValue =>
  Object.hasOwn(draft, rule.key) ? draft[rule.key] : rule.value;

/** Does the value on screen (draft or saved) differ from the default? Legacy rows use the server's flag. */
export function isRuleChanged(rule: TRule, draft: TDraft): boolean {
  if (rule.source === "legacy") return rule.changed;
  return !valuesEqual(rule.kind, effectiveValue(rule, draft), rule.default);
}

/** Registry rules whose draft differs from the saved value, in list order. */
export function pendingChanges(rules: TRule[], draft: TDraft): TRegistryRule[] {
  return rules.filter(
    (r): r is TRegistryRule =>
      r.source === "registry" && Object.hasOwn(draft, r.key) && !valuesEqual(r.kind, draft[r.key], r.value)
  );
}

export const pendingValues = (changes: TRegistryRule[], draft: TDraft): Record<string, TParadiseRuleValue> =>
  Object.fromEntries(changes.map((r) => [r.key, draft[r.key]]));

/** A high-risk rule among the changes means the typed phrase comes first. */
export const needsConfirm = (changes: TRegistryRule[]): boolean => changes.some((r) => r.risk === "high");

/** Drops drafts that equal the saved value, so a typed-and-reverted edit never counts as a change. */
export function pruneDraft(rules: TRule[], draft: TDraft): TDraft {
  const byKey = new Map(rules.map((r) => [r.key, r]));
  return Object.fromEntries(
    Object.entries(draft).filter(([key, value]) => {
      const rule = byKey.get(key);
      return rule?.source === "registry" && !valuesEqual(rule.kind, value, rule.value);
    })
  );
}

// ---- validation and display --------------------------------------------------

const fillText = (template: string, vars: Record<string, string | number>): string =>
  template.replace(/\{(\w+)\}/g, (_, key) => String(vars[key] ?? `{${key}}`));

export const choiceValue = (rule: TRegistryRule, raw: string): string | number | undefined =>
  rule.choices?.find((c) => String(c.value) === raw)?.value;

/** An early message for a draft the server would refuse. The server validates again and wins. */
export function validateRuleValue(rule: TRegistryRule, value: TParadiseRuleValue, t: TAllRulesStrings): string | null {
  const v = t.validation;
  switch (rule.kind) {
    case "bool":
      return typeof value === "boolean" ? null : v.bool;
    case "int": {
      if (typeof value !== "number" || !Number.isInteger(value)) {
        return rule.min !== null && rule.max !== null ? fillText(v.int_range, { min: rule.min, max: rule.max }) : v.int;
      }
      if ((rule.min !== null && value < rule.min) || (rule.max !== null && value > rule.max)) {
        return fillText(v.int_range, { min: rule.min ?? value, max: rule.max ?? value });
      }
      return null;
    }
    case "choice":
    case "level":
      return rule.choices?.some((c) => String(c.value) === String(value)) ? null : v.choice;
    case "text":
      if (typeof value !== "string") return v.text_too_long.replace("{max}", String(rule.max_length ?? 0));
      return rule.max_length !== null && value.length > rule.max_length
        ? fillText(v.text_too_long, { max: rule.max_length })
        : null;
    case "list_of_keys": {
      const allowed = new Set((rule.choices ?? []).map((c) => String(c.value)));
      return Array.isArray(value) && value.every((x) => allowed.has(x)) ? null : v.list;
    }
    default:
      return null;
  }
}

/** Text for the default line and the confirmation dialog. */
export function formatRuleValue(rule: TRegistryRule, value: TParadiseRuleValue, t: TAllRulesStrings): string {
  switch (rule.kind) {
    case "bool":
      return value === true ? t.on : t.off;
    case "choice":
    case "level":
      return rule.choices?.find((c) => String(c.value) === String(value))?.label ?? String(value);
    case "list_of_keys": {
      if (!Array.isArray(value) || value.length === 0) return t.none_selected;
      return value.map((x) => rule.choices?.find((c) => String(c.value) === x)?.label ?? x).join(", ");
    }
    default:
      return String(value);
  }
}

/** Value text of a read-only legacy row, in the same words its own tab uses. */
export function formatLegacyValue(
  rule: TLegacyRule,
  raw: string,
  t: TSettingStrings,
  unit: string | undefined
): string {
  const def: TInstanceSetting = {
    key: rule.key,
    kind: rule.kind as TInstanceSettingKind,
    default: rule.default,
    value: rule.value,
    min: rule.min,
    max: rule.max,
    choices: rule.choices ? rule.choices.map((c) => Number(c.value)) : null,
    sensitive: rule.risk === "high",
  };
  return formatSettingValue(def, raw, t, unit);
}

/** "KEP P29" or "KEP-48" as written; a bare number gets the prefix. */
export const kepLabel = (kep: string, t: TAllRulesStrings): string =>
  /^kep/i.test(kep) ? kep : fillText(t.kep, { kep });
