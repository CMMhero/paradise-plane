/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: God Mode rule registry (apps/api/plane/utils/aturan)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** A rule value as JSON: bool, int, choice (string or number), text, level (number), list_of_keys (string[]). */
export type TParadiseRuleValue = boolean | number | string | string[];

/** `config.paradise_rules` from GET /api/instances/: values of the rules declared with `web=True`. */
export type TParadiseRulesPayload = Record<string, TParadiseRuleValue>;

/** Kinds of registry rules. Legacy rows keep their own kinds (`TInstanceSettingKind`). */
export type TRuleKind = "bool" | "int" | "choice" | "text" | "level" | "list_of_keys";

export type TRuleRisk = "low" | "medium" | "high";

export type TRuleApplies = "live" | "next_run" | "restart";

export type TRuleChoice = { value: string | number; label: string };

/** A rule declared in the registry: editable on the Rules screen. */
export type TRegistryRule = {
  key: string;
  source: "registry";
  kind: TRuleKind;
  value: TParadiseRuleValue;
  default: TParadiseRuleValue;
  changed: boolean;
  label: string;
  help: string;
  group: string;
  area: string;
  risk: TRuleRisk;
  applies: TRuleApplies;
  web: boolean;
  kep: string | null;
  min: number | null;
  max: number | null;
  max_length: number | null;
  choices: TRuleChoice[] | null;
  /** `member_default` = stored in New member defaults; new accounts get it, `apply_section` applies it to everyone. */
  store: "instance" | "member_default";
  apply_section: string | null;
};

/**
 * A setting of the older registry (`/api/instances/settings/`), listed read-only.
 * Values are canonical strings and labels come from the God Mode strings.
 */
export type TLegacyRule = {
  key: string;
  source: "legacy";
  kind: string;
  value: string;
  default: string;
  changed: boolean;
  label: null;
  help: null;
  group: null;
  area: null;
  risk: TRuleRisk;
  applies: null;
  web: false;
  kep: null;
  min: number | null;
  max: number | null;
  max_length: null;
  choices: TRuleChoice[] | null;
  store: "instance";
  apply_section: null;
};

export type TRule = TRegistryRule | TLegacyRule;

export type TRuleGroup = { id: string; label: string; description: string };

/** GET /api/instances/rules/ (also the body of every successful PATCH and reset). */
export type TRulesResponse = {
  groups: TRuleGroup[];
  rules: TRule[];
  confirm_phrase: string;
};

/** PATCH /api/instances/rules/. `confirm` is required when a high-risk rule changes. */
export type TRulesUpdate = {
  values: Record<string, TParadiseRuleValue>;
  confirm?: string;
};

/** POST /api/instances/rules/reset/. */
export type TRulesReset = {
  keys: string[];
  confirm?: string;
};

/** 400 bodies: invalid values per key, or a high-risk change without the phrase. */
export type TRulesError =
  | { errors: Record<string, string> }
  | { error: "confirm_required"; keys: string[] }
  | { error: string };
