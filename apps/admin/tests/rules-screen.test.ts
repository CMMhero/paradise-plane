/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: the All rules screen shows every rule the server declares
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * The rules are declared in Python (apps/api/plane/utils/aturan/area_*.py) and
 * the topics in grup.py. These tests read those files, build the response the
 * server would send, and prove the screen's grouping lists every rule once.
 * Pure functions only: the admin app has no DOM test setup.
 */

import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vite-plus/test";
import type { TLegacyRule, TRegistryRule, TRule, TRuleGroup, TRuleKind, TRulesResponse } from "@plane/types";
import { settingsStrings } from "@/app/i18n/godmode-settings";
import { MENU_TABS } from "@/components/common/menu-tree";
import {
  OTHER_SECTION_ID,
  RULE_KIND_CONTROLS,
  buildRuleSections,
  countEntries,
  effectiveValue,
  filterSections,
  formatRuleValue,
  isRuleChanged,
  matchesQuery,
  moveItem,
  needsConfirm,
  pendingChanges,
  pendingValues,
  pruneDraft,
  validateRuleValue,
  valuesEqual,
} from "@/components/rules/rules-model";
import type { TRuleEntry } from "@/components/rules/rules-model";
import { SETTINGS_LAYOUT } from "@/components/settings/layouts";
import type { TSettingsTabId } from "@/components/settings/layouts";

const ATURAN_DIR = fileURLToPath(new URL("../../api/plane/utils/aturan/", import.meta.url));
// oxlint-disable-next-line unicorn/no-array-sort -- lib ES2022 has no toSorted; the array is a local copy
const sorted = (list: string[]): string[] => [...list].sort();
const read = (name: string) => readFileSync(`${ATURAN_DIR}${name}`, "utf8");

// ---- reading the Python declarations ---------------------------------------

type TDeclared = { key: string; group: string; file: string };

/** Every `Rule(` block of every area file: its `key=` (a string or a constant) and its `group=`. */
function declaredRules(): TDeclared[] {
  const out: TDeclared[] = [];
  const files = sorted(readdirSync(ATURAN_DIR).filter((f) => /^area_.+\.py$/.test(f)));
  for (const file of files) {
    const source = read(file)
      .split("\n")
      .filter((line) => !line.trimStart().startsWith("#"))
      .join("\n");
    const constants = new Map<string, string>();
    for (const m of source.matchAll(/^([A-Z][A-Z0-9_]*)\s*=\s*"([^"]+)"/gm)) constants.set(m[1], m[2]);
    const starts = [...source.matchAll(/(?<![A-Za-z_])Rule\(/g)].map((m) => m.index ?? 0);
    starts.forEach((start, i) => {
      const block = source.slice(start, starts[i + 1] ?? source.length);
      const keyMatch = /\bkey\s*=\s*(?:"([^"]+)"|([A-Z][A-Z0-9_]*))/.exec(block);
      const groupMatch = /\bgroup\s*=\s*"([^"]+)"/.exec(block);
      const key = keyMatch?.[1] ?? constants.get(keyMatch?.[2] ?? "");
      if (!key || !groupMatch) throw new Error(`Could not read a Rule( block in ${file}`);
      out.push({ key, group: groupMatch[1], file });
    });
  }
  return out;
}

/** `GRUP = {"id": ("Label", "Description"), ...}` in grup.py, in file order. */
function declaredGroups(): TRuleGroup[] {
  const source = read("grup.py");
  const body = source.slice(source.indexOf("GRUP = {"));
  return [...body.matchAll(/^\s*"([a-z_]+)":\s*\(\s*"((?:[^"\\]|\\.)*)",\s*"((?:[^"\\]|\\.)*)"/gm)].map((m) => ({
    id: m[1],
    label: m[2],
    description: m[3],
  }));
}

/** The kind names in jenis.py (`BOOL = "bool"` and so on). */
function declaredKinds(): string[] {
  const source = read("jenis.py");
  return [...source.matchAll(/^(?:BOOL|INT|CHOICE|TEXT|LEVEL|KEY_LIST)\s*=\s*"(\w+)"/gm)].map((m) => m[1]);
}

// ---- building responses --------------------------------------------------------

const registryRule = (key: string, group: string, over: Partial<TRegistryRule> = {}): TRegistryRule => ({
  key,
  source: "registry",
  kind: "bool",
  value: true,
  default: true,
  changed: false,
  label: `Label of ${key}`,
  help: `Help text of ${key}`,
  group,
  area: "test",
  risk: "low",
  applies: "live",
  web: false,
  kep: null,
  min: null,
  max: null,
  max_length: null,
  choices: null,
  ordered: false,
  store: "instance",
  apply_section: null,
  ...over,
});

const legacyRule = (key: string, over: Partial<TLegacyRule> = {}): TLegacyRule => ({
  key,
  source: "legacy",
  kind: "toggle",
  value: "1",
  default: "1",
  changed: false,
  label: null,
  help: null,
  group: null,
  area: null,
  risk: "low",
  applies: null,
  web: false,
  kep: null,
  min: null,
  max: null,
  max_length: null,
  choices: null,
  ordered: false,
  store: "instance",
  apply_section: null,
  ...over,
});

const layoutKeys = (): string[] =>
  Object.values(SETTINGS_LAYOUT)
    .flat()
    .flatMap((section) => section.rows.map((row) => row.key));

const serverResponse = (): { response: TRulesResponse; declared: TDeclared[]; groups: TRuleGroup[] } => {
  const declared = declaredRules();
  const groups = declaredGroups();
  const registry = declared.map((d) => registryRule(d.key, d.group));
  const legacy = [...new Set(layoutKeys())].map((key) => legacyRule(key));
  return {
    response: {
      groups,
      rules: [...registry, ...legacy, legacyRule("NOT_IN_ANY_TAB")],
      confirm_phrase: "CHANGE RULES",
    },
    declared,
    groups,
  };
};

const entriesOf = (sections: ReturnType<typeof buildRuleSections>): TRuleEntry[] => sections.flatMap((s) => s.entries);

// ---- (a) grouping ------------------------------------------------------------------

describe("All rules: grouping", () => {
  const { response, declared, groups } = serverResponse();
  const sections = buildRuleSections(response, settingsStrings);

  it("reads the Python declarations", () => {
    expect(declared.length).toBeGreaterThan(0);
    expect(groups.length).toBeGreaterThan(0);
    expect(new Set(declared.map((d) => d.key)).size).toBe(declared.length);
  });

  it("every topic in grup.py has a label and a description", () => {
    for (const group of groups) {
      expect(group.label, group.id).not.toBe("");
      expect(group.description, group.id).not.toBe("");
    }
  });

  it("every declared rule uses a topic that grup.py lists", () => {
    const ids = new Set(groups.map((g) => g.id));
    for (const d of declared) expect(ids, `${d.key} in ${d.file}`).toContain(d.group);
  });

  it("lists every registry rule exactly once, under its own topic label", () => {
    const registry = sections.filter((s) => s.source === "registry");
    const keys = registry.flatMap((s) => s.entries.map((e) => e.rule.key));
    expect(sorted(keys)).toEqual(sorted(declared.map((d) => d.key)));
    for (const d of declared) {
      const section = registry.find((s) => s.entries.some((e) => e.rule.key === d.key));
      expect(section?.id, d.key).toBe(`group:${d.group}`);
      expect(section?.title, d.key).toBe(groups.find((g) => g.id === d.group)?.label);
    }
  });

  it("lists every rule of the response exactly once, registry and legacy together", () => {
    const keys = entriesOf(sections).map((e) => e.rule.key);
    expect(keys).toHaveLength(response.rules.length);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("orders the registry topics like `groups`", () => {
    const order = groups.map((g) => `group:${g.id}`);
    const shown = sections.filter((s) => s.source === "registry").map((s) => s.id);
    expect(shown).toEqual(order.filter((id) => shown.includes(id)));
  });

  it("puts registry sections before legacy ones and leaves empty topics out", () => {
    const sources = sections.map((s) => s.source);
    expect(sources.lastIndexOf("registry")).toBeLessThan(sources.indexOf("legacy"));
    for (const section of sections) expect(section.entries.length, section.id).toBeGreaterThan(0);
  });

  it("shows a rule whose topic the server did not list", () => {
    const stray = registryRule("STRAY_RULE", "brand_new_topic");
    const result = buildRuleSections({ ...response, rules: [...response.rules, stray] }, settingsStrings);
    expect(entriesOf(result).filter((e) => e.rule.key === "STRAY_RULE")).toHaveLength(1);
  });

  it("links every legacy rule to the tab that edits it", () => {
    const tabs = Object.values(MENU_TABS).flat();
    const legacy = sections.filter((s) => s.source === "legacy");
    for (const layoutId of Object.keys(SETTINGS_LAYOUT) as TSettingsTabId[]) {
      const tab = tabs.find((t) => t.id === layoutId);
      for (const row of SETTINGS_LAYOUT[layoutId].flatMap((s) => s.rows)) {
        const entry = entriesOf(legacy).find((e) => e.rule.key === row.key);
        expect(entry?.editOn?.href, row.key).toBeDefined();
        // A key listed on two tabs goes to the first; the rest must at least point at a real tab.
        expect(
          tabs.map((t) => t.href),
          row.key
        ).toContain(entry?.editOn?.href);
        if (entry?.editOn?.title === settingsStrings.tabs[layoutId].title) expect(entry.editOn.href).toBe(tab?.href);
      }
    }
  });

  it("keeps legacy rules that no tab lists under Other settings", () => {
    const other = sections.find((s) => s.id === OTHER_SECTION_ID);
    expect(other?.entries.map((e) => e.rule.key)).toEqual(["NOT_IN_ANY_TAB"]);
    expect(other?.entries[0].editOn).toBeNull();
  });

  it("names legacy rows from the God Mode strings", () => {
    const entry = entriesOf(sections).find((e) => e.rule.key === "TASK_DELETE_RULE");
    expect(entry?.name).not.toBe("TASK_DELETE_RULE");
    expect(entry?.help).not.toBe("");
  });

  it("is the last tab of the Work rules menu", () => {
    expect(MENU_TABS.rules.at(-1)).toEqual({ id: "rules_all", href: "/rules/all/" });
  });
});

// ---- (b) search and changed filter ---------------------------------------------------

describe("All rules: search and changed filter", () => {
  const rules: TRule[] = [
    registryRule("DIRECTOR_SIDEBAR_HIDES", "visibility", {
      label: "What directors see in the sidebar",
      help: "Menus hidden from directors.",
    }),
    registryRule("CHAT_PINS_MAX", "chat", {
      kind: "int",
      value: 30,
      default: 20,
      changed: true,
      label: "Pinned messages per conversation",
      help: "How many messages a channel can pin.",
    }),
    legacyRule("OFFICE_TIMEZONE", { value: "Asia/Jakarta", default: "UTC", changed: true, kind: "timezone" }),
  ];
  const groups: TRuleGroup[] = [
    { id: "visibility", label: "What each level sees", description: "d" },
    { id: "chat", label: "Chat", description: "d" },
  ];
  const sections = buildRuleSections({ groups, rules, confirm_phrase: "CHANGE RULES" }, settingsStrings);
  const noDraft = {};
  const isChanged = (e: TRuleEntry) => isRuleChanged(e.rule, noDraft);
  const keysOf = (query: string, changedOnly = false) =>
    entriesOf(filterSections(sections, { query, changedOnly }, isChanged)).map((e) => e.rule.key);

  it("returns everything without a filter", () => {
    expect(countEntries(filterSections(sections, { query: "", changedOnly: false }, isChanged))).toBe(3);
    expect(countEntries(filterSections(sections, { query: "   ", changedOnly: false }, isChanged))).toBe(3);
  });

  it("matches the key, with or without underscores", () => {
    expect(keysOf("CHAT_PINS")).toEqual(["CHAT_PINS_MAX"]);
    expect(keysOf("chat pins")).toEqual(["CHAT_PINS_MAX"]);
  });

  it("matches the label and the help text, ignoring case and accents", () => {
    expect(keysOf("SIDEBAR")).toEqual(["DIRECTOR_SIDEBAR_HIDES"]);
    expect(keysOf("channel can pin")).toEqual(["CHAT_PINS_MAX"]);
    expect(matchesQuery(entriesOf(sections)[0], "dïrectors")).toBe(true);
  });

  it("needs every word to match", () => {
    expect(keysOf("directors sidebar")).toEqual(["DIRECTOR_SIDEBAR_HIDES"]);
    expect(keysOf("directors pinned")).toEqual([]);
  });

  it("drops sections that end up empty", () => {
    const result = filterSections(sections, { query: "pinned", changedOnly: false }, isChanged);
    expect(result.map((s) => s.id)).toEqual(["group:chat"]);
  });

  it("keeps only rules that differ from the default", () => {
    expect(sorted(keysOf("", true))).toEqual(["CHAT_PINS_MAX", "OFFICE_TIMEZONE"]);
    expect(keysOf("pinned", true)).toEqual(["CHAT_PINS_MAX"]);
    expect(keysOf("sidebar", true)).toEqual([]);
  });

  it("counts an unsaved edit as changed, and an edit back to the default as not changed", () => {
    const sidebar = rules[0] as TRegistryRule;
    expect(isRuleChanged(sidebar, {})).toBe(false);
    expect(isRuleChanged(sidebar, { DIRECTOR_SIDEBAR_HIDES: false })).toBe(true);
    const pins = rules[1] as TRegistryRule;
    expect(isRuleChanged(pins, { CHAT_PINS_MAX: 20 })).toBe(false);
  });
});

// ---- (c) one control per kind -----------------------------------------------------------

describe("All rules: controls", () => {
  const kinds: TRuleKind[] = ["bool", "int", "choice", "text", "level", "list_of_keys"];

  it("has a control for every TRuleKind", () => {
    expect(sorted(Object.keys(RULE_KIND_CONTROLS))).toEqual(sorted(kinds));
    for (const kind of kinds) expect(RULE_KIND_CONTROLS[kind], kind).toBeTruthy();
  });

  it("covers every kind the server declares in jenis.py", () => {
    const serverKinds = declaredKinds();
    expect(sorted(serverKinds)).toEqual(sorted(kinds));
    for (const kind of serverKinds) expect(Object.hasOwn(RULE_KIND_CONTROLS, kind), kind).toBe(true);
  });

  it("maps to the controls the spec asks for", () => {
    expect(RULE_KIND_CONTROLS).toEqual({
      bool: "switch",
      int: "number",
      choice: "select",
      level: "select",
      text: "text",
      list_of_keys: "checkbox-list",
    });
  });
});

// ---- (d) pending changes and the confirmation phrase ---------------------------------------

describe("All rules: pending changes", () => {
  const low = registryRule("CHAT_PINS_MAX", "chat", {
    kind: "int",
    value: 20,
    default: 20,
    min: 1,
    max: 100,
    label: "Pinned messages",
  });
  const high = registryRule("APPROVER_MIN_LEVEL", "approvals", {
    kind: "level",
    value: 20,
    default: 20,
    risk: "high",
    choices: [
      { value: 20, label: "Supervisor (20)" },
      { value: 30, label: "Manager (30)" },
    ],
  });
  const list = registryRule("PICKED", "chat", {
    kind: "list_of_keys",
    value: ["a", "b"],
    default: ["a"],
    choices: [
      { value: "a", label: "Alpha" },
      { value: "b", label: "Beta" },
      { value: "c", label: "Gamma" },
    ],
  });
  const text = registryRule("NOTE", "chat", { kind: "text", value: "hi", default: "", max_length: 5 });
  const rules: TRule[] = [low, high, list, text, legacyRule("OFFICE_TIMEZONE")];
  const t = settingsStrings.allRules;

  it("has no change before anything is edited", () => {
    expect(pendingChanges(rules, {})).toEqual([]);
    expect(needsConfirm(pendingChanges(rules, {}))).toBe(false);
  });

  it("a low-risk change does not ask for the phrase", () => {
    const changes = pendingChanges(rules, { CHAT_PINS_MAX: 25 });
    expect(changes.map((r) => r.key)).toEqual(["CHAT_PINS_MAX"]);
    expect(needsConfirm(changes)).toBe(false);
  });

  it("a high-risk change asks for the phrase, alone or among others", () => {
    expect(needsConfirm(pendingChanges(rules, { APPROVER_MIN_LEVEL: 30 }))).toBe(true);
    expect(needsConfirm(pendingChanges(rules, { CHAT_PINS_MAX: 25, APPROVER_MIN_LEVEL: 30 }))).toBe(true);
  });

  it("a high-risk edit that went back to the saved value is not a change", () => {
    const changes = pendingChanges(rules, { APPROVER_MIN_LEVEL: 20, CHAT_PINS_MAX: 25 });
    expect(changes.map((r) => r.key)).toEqual(["CHAT_PINS_MAX"]);
    expect(needsConfirm(changes)).toBe(false);
  });

  it("ignores drafts of legacy rules and unknown keys", () => {
    expect(pendingChanges(rules, { OFFICE_TIMEZONE: "UTC", NOPE: 1 })).toEqual([]);
  });

  it("sends only the changed values", () => {
    const draft = { CHAT_PINS_MAX: 25, NOTE: "hi" };
    expect(pendingValues(pendingChanges(rules, draft), draft)).toEqual({ CHAT_PINS_MAX: 25 });
  });

  it("prunes drafts that equal the saved value", () => {
    expect(pruneDraft(rules, { CHAT_PINS_MAX: 20, NOTE: "hello", GONE: 1 })).toEqual({ NOTE: "hello" });
  });

  it("compares lists as sets and choices by text", () => {
    expect(valuesEqual("list_of_keys", ["b", "a"], ["a", "b"])).toBe(true);
    expect(valuesEqual("list_of_keys", ["a"], ["a", "b"])).toBe(false);
    expect(valuesEqual("level", 20, "20")).toBe(true);
    expect(pendingChanges(rules, { PICKED: ["b", "a"] })).toEqual([]);
  });

  it("compares ordered lists in order", () => {
    expect(valuesEqual("list_of_keys", ["b", "a"], ["a", "b"], true)).toBe(false);
    expect(valuesEqual("list_of_keys", ["a", "b"], ["a", "b"], true)).toBe(true);
    expect(valuesEqual("list_of_keys", ["a"], ["a", "b"], true)).toBe(false);
    expect(valuesEqual("list_of_keys", [], [], true)).toBe(true);
    // The flag defaults to unordered, as before.
    expect(valuesEqual("list_of_keys", ["b", "a"], ["a", "b"])).toBe(true);
  });

  it("treats a reordered ordered list as a change in every caller", () => {
    const ordered = registryRule("WIDGETS", "chat", {
      kind: "list_of_keys",
      ordered: true,
      value: ["a", "b"],
      default: ["a", "b"],
      choices: [
        { value: "a", label: "Alpha" },
        { value: "b", label: "Beta" },
      ],
    });
    const all: TRule[] = [ordered];
    const draft = { WIDGETS: ["b", "a"] };
    expect(isRuleChanged(ordered, draft)).toBe(true);
    expect(pendingChanges(all, draft)).toEqual([ordered]);
    expect(pruneDraft(all, draft)).toEqual(draft);
    // Back to the saved order: no change, and the draft is dropped.
    expect(isRuleChanged(ordered, { WIDGETS: ["a", "b"] })).toBe(false);
    expect(pendingChanges(all, { WIDGETS: ["a", "b"] })).toEqual([]);
    expect(pruneDraft(all, { WIDGETS: ["a", "b"] })).toEqual({});
  });

  it("moves an item one place and stops at the ends", () => {
    expect(moveItem(["a", "b", "c"], 1, -1)).toEqual(["b", "a", "c"]);
    expect(moveItem(["a", "b", "c"], 1, 1)).toEqual(["a", "c", "b"]);
    const items = ["a", "b"];
    expect(moveItem(items, 0, -1)).toBe(items);
    expect(moveItem(items, 1, 1)).toBe(items);
    expect(moveItem(items, 5, 1)).toBe(items);
    expect(items).toEqual(["a", "b"]);
  });

  it("reads the value on screen from the draft first", () => {
    expect(effectiveValue(low, {})).toBe(20);
    expect(effectiveValue(low, { CHAT_PINS_MAX: 7 })).toBe(7);
  });

  it("validates ints against min and max", () => {
    expect(validateRuleValue(low, 25, t)).toBeNull();
    expect(validateRuleValue(low, 0, t)).toBe("Enter a whole number from 1 to 100.");
    expect(validateRuleValue(low, 101, t)).toBe("Enter a whole number from 1 to 100.");
    expect(validateRuleValue(low, "abc", t)).toBe("Enter a whole number from 1 to 100.");
    expect(validateRuleValue(low, "", t)).toBe("Enter a whole number from 1 to 100.");
    expect(validateRuleValue(low, 2.5, t)).toBe("Enter a whole number from 1 to 100.");
  });

  it("validates choices, levels, lists, and text length", () => {
    expect(validateRuleValue(high, 30, t)).toBeNull();
    expect(validateRuleValue(high, 99, t)).toBe(t.validation.choice);
    expect(validateRuleValue(list, ["a", "c"], t)).toBeNull();
    expect(validateRuleValue(list, ["a", "zzz"], t)).toBe(t.validation.list);
    expect(validateRuleValue(text, "12345", t)).toBeNull();
    expect(validateRuleValue(text, "123456", t)).toBe("Use at most 5 characters.");
  });

  it("describes values the way the dialog and the default line show them", () => {
    expect(formatRuleValue(high, 30, t)).toBe("Manager (30)");
    expect(formatRuleValue(list, ["a", "c"], t)).toBe("Alpha, Gamma");
    expect(formatRuleValue(list, [], t)).toBe(t.none_selected);
    expect(formatRuleValue(registryRule("B", "chat"), false, t)).toBe(t.off);
    expect(formatRuleValue(low, 25, t)).toBe("25");
  });
});
