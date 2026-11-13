/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: penjaga i18n untuk layar onboarding
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Usage (run from packages/i18n, where tsx is installed):
//   pnpm run check:onboarding
//
// Fails (exit 1) when:
//   1. The onboarding-facing sections (onboarding_ui, login_ui, shared_ui) differ in keys or
//      {placeholders} between locales, hold empty values, or are English copies in a locale that
//      should be translated.
//   2. An onboarding component uses a translation key that is missing in some locale.
//   3. An onboarding_ui key is not used anywhere in apps/web (dead keys rot in 19 files).
//   4. An onboarding component contains a user-facing string literal (JSX text, title/placeholder/
//      alt/label attributes, toast title/message, form `required`/`message`) that is not an i18n key.
//      Escape hatch for truly language-neutral text: a `// i18n-ignore` comment on the same or the
//      previous line.
//   5. A file excluded as "legacy and unused" gets imported again.

import fs from "node:fs";
import path from "node:path";
import ts from "typescript";
import { listLocales, loadLocale, readJsonFile, LOCALES_DIR } from "./lib/locale-io.js";

const REPO = path.resolve(import.meta.dirname, "../../..");
const WEB = path.join(REPO, "apps/web");

/** Directories and files that make up the onboarding surface (relative to apps/web). */
const SCOPE = [
  "core/components/onboarding",
  "ce/components/onboarding",
  "core/components/home/user-greetings.tsx",
  "core/components/user/user-greetings.tsx",
  "core/components/core/modals/user-image-upload-modal.tsx",
  "core/components/instance/not-ready-view.tsx",
  "core/components/account/auth-forms/auth-header.tsx",
  "core/hooks/use-password-labels.ts",
];

/**
 * Upstream's old single-page onboarding. Nothing imports these (the step-based flow in
 * `onboarding/steps` replaced them), so their English literals are never shown. They are excluded
 * from the literal scan ONLY while they stay unreferenced (check 5).
 */
const LEGACY_UNUSED = [
  "core/components/onboarding/profile-setup.tsx",
  "core/components/onboarding/invite-members.tsx",
  "core/components/onboarding/create-or-join-workspaces.tsx",
  "core/components/onboarding/create-workspace.tsx",
  "core/components/onboarding/invitations.tsx",
  "core/components/onboarding/step-indicator.tsx",
];

/** Sections that must be fully translated in every locale. */
const GUARDED_SECTIONS = ["onboarding_ui", "login_ui"] as const;
/** shared_ui also holds unrelated email-digest texts; only these keys are onboarding/invite related. */
const GUARDED_SHARED_UI = [
  "workspace_not_found",
  "invite_inactive_title",
  "invite_inactive_description",
  "sign_in_to_continue",
  "back_to_home",
  "onboarding_usecase_title",
  "onboarding_role_description",
  "onboarding_profile_description",
];
/** Locales whose copy may legitimately equal English for these language-neutral values. */
const SAME_AS_ENGLISH_OK = new Set([
  "onboarding_ui.invite_email_placeholder",
  "onboarding_ui.role_developer",
  "onboarding_ui.role_designer",
  "onboarding_ui.role_product_manager",
  "onboarding_ui.role_engineering_manager",
  "onboarding_ui.skip",
  "onboarding_ui.tour_work_items_title",
]);

const problems: string[] = [];
const fail = (msg: string) => problems.push(msg);

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

function get(obj: unknown, dotted: string): unknown {
  return dotted.split(".").reduce<unknown>((o, k) => (o as Record<string, unknown> | undefined)?.[k], obj);
}

function flatten(obj: Record<string, unknown>, prefix = ""): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object") Object.assign(out, flatten(v as Record<string, unknown>, key));
    else out[key] = String(v);
  }
  return out;
}

const placeholders = (s: string) =>
  [...s.matchAll(/\{(\w+)/g)]
    .map((m) => m[1])
    .toSorted()
    .join(",");

function walk(target: string): string[] {
  const abs = path.join(WEB, target);
  const stat = fs.statSync(abs);
  if (stat.isFile()) return [abs];
  return fs
    .readdirSync(abs, { recursive: true, withFileTypes: true })
    .filter((e) => e.isFile() && /\.(ts|tsx)$/.test(e.name))
    .map((e) => path.join(e.parentPath, e.name));
}

const rel = (abs: string) => path.relative(WEB, abs).replaceAll("\\", "/");

// ---------------------------------------------------------------------------
// 1. locale parity of the guarded sections
// ---------------------------------------------------------------------------

const locales = listLocales();
const paradise = Object.fromEntries(
  locales.map((l) => [l, readJsonFile(path.join(LOCALES_DIR, l, "paradise.json"))])
) as Record<string, Record<string, unknown>>;
const en = paradise["en"];

const guardedKeys: string[] = [];
for (const section of GUARDED_SECTIONS) {
  for (const k of Object.keys(flatten({ [section]: get(en, section) as Record<string, unknown> }))) guardedKeys.push(k);
}
for (const k of GUARDED_SHARED_UI) guardedKeys.push(`shared_ui.${k}`);

for (const locale of locales) {
  const flat = flatten(paradise[locale]);
  const flatEn = flatten(en);
  for (const key of guardedKeys) {
    const value = flat[key];
    if (value === undefined) {
      fail(`[parity] ${locale}: missing ${key}`);
      continue;
    }
    if (value.trim() === "") fail(`[parity] ${locale}: empty ${key}`);
    if (placeholders(value) !== placeholders(flatEn[key] ?? "")) {
      fail(
        `[placeholders] ${locale}: ${key} has {${placeholders(value)}} but en has {${placeholders(flatEn[key] ?? "")}}`
      );
    }
    if (
      locale !== "en" &&
      value === flatEn[key] &&
      !SAME_AS_ENGLISH_OK.has(key) &&
      !(locale === "id" && /^[A-Za-z]+$/.test(value))
    ) {
      fail(`[untranslated] ${locale}: ${key} is still the English text "${value}"`);
    }
  }
  // extra keys in a locale that en does not have (typos, leftovers)
  for (const section of GUARDED_SECTIONS) {
    for (const key of Object.keys(flat)) {
      if (key.startsWith(`${section}.`) && !(key in flatEn)) fail(`[parity] ${locale}: extra key ${key} not in en`);
    }
  }
}

// ---------------------------------------------------------------------------
// 2 + 3 + 4. scan the onboarding components
// ---------------------------------------------------------------------------

const allKeysByLocale = new Map(locales.map((l) => [l, loadLocale(l).allKeys]));
const topLevelEn = new Set([...(allKeysByLocale.get("en") ?? [])].map((k) => k.split(".")[0]));
const KEY_SHAPE = /^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$/;
const HAS_LETTER = /\p{L}/u;
const TEXT_PROPS = new Set([
  "title",
  "message",
  "description",
  "placeholder",
  "label",
  "required",
  "header",
  "subHeader",
]);
const TEXT_ATTRS = new Set([
  "title",
  "placeholder",
  "alt",
  "aria-label",
  "label",
  "description",
  "tooltipContent",
  "subHeader",
  "header",
]);

const usedKeys = new Set<string>();
const usedPrefixes = new Set<string>();

function isKeyLike(text: string): boolean {
  return KEY_SHAPE.test(text) && topLevelEn.has(text.split(".")[0] ?? "");
}

function registerKey(file: string, line: number, key: string) {
  usedKeys.add(key);
  for (const [locale, keys] of allKeysByLocale) {
    if (!keys.has(key)) fail(`[missing-key] ${file}:${line} uses "${key}" which ${locale} does not have`);
  }
}

function scan(abs: string, checkLiterals: boolean) {
  const file = rel(abs);
  const source = fs.readFileSync(abs, "utf8");
  const sf = ts.createSourceFile(
    abs,
    source,
    ts.ScriptTarget.Latest,
    true,
    abs.endsWith("x") ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  );
  const lines = source.split(/\r?\n/);
  const lineOf = (node: ts.Node) => sf.getLineAndCharacterOfPosition(node.getStart(sf)).line;
  const ignored = (node: ts.Node) => {
    const i = lineOf(node);
    return /i18n-ignore/.test(lines[i] ?? "") || /i18n-ignore/.test(lines[i - 1] ?? "");
  };
  const flag = (node: ts.Node, what: string, text: string) => {
    if (!checkLiterals || ignored(node)) return;
    fail(`[hardcoded] ${file}:${lineOf(node) + 1} ${what}: "${text.trim().replace(/\s+/g, " ").slice(0, 60)}"`);
  };

  const visit = (node: ts.Node) => {
    if (ts.isStringLiteralLike(node) && isKeyLike(node.text)) registerKey(file, lineOf(node) + 1, node.text);
    if (ts.isTemplateExpression(node)) {
      const head = node.head.text;
      if (/^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*\.?[a-z0-9_]*$/.test(head) && head.includes(".")) usedPrefixes.add(head);
    }
    if (ts.isJsxText(node)) {
      const text = node.text.replace(/&(nbsp|apos|quot|amp|lt|gt);/g, " ");
      if (HAS_LETTER.test(text)) flag(node, "JSX text", text);
    }
    if (ts.isJsxAttribute(node) && node.initializer && ts.isStringLiteral(node.initializer)) {
      const name = node.name.getText(sf);
      const text = node.initializer.text;
      if (TEXT_ATTRS.has(name) && HAS_LETTER.test(text) && !isKeyLike(text)) flag(node, `attribute ${name}`, text);
    }
    if (ts.isPropertyAssignment(node) && (ts.isIdentifier(node.name) || ts.isStringLiteral(node.name))) {
      const name = ts.isIdentifier(node.name) ? node.name.text : node.name.text;
      const init = node.initializer;
      if (TEXT_PROPS.has(name) && ts.isStringLiteralLike(init) && HAS_LETTER.test(init.text) && !isKeyLike(init.text)) {
        flag(node, `property ${name}`, init.text);
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
}

const legacyAbs = new Set(LEGACY_UNUSED.map((f) => path.join(WEB, f)));
const scoped = SCOPE.flatMap(walk);
for (const abs of scoped) scan(abs, !legacyAbs.has(abs));

// the whole web app may use onboarding_ui keys (e.g. greetings on the home page)
for (const abs of walk("core").concat(walk("ce"), walk("app"))) {
  if (scoped.includes(abs)) continue;
  const src = fs.readFileSync(abs, "utf8");
  for (const m of src.matchAll(/["'`](onboarding_ui\.[a-z0-9_.${}]+)["'`]/g)) {
    const text = m[1] ?? "";
    if (text.includes("${")) usedPrefixes.add(text.slice(0, text.indexOf("${")));
    else usedKeys.add(text);
  }
}

// 3. dead onboarding_ui keys
for (const key of Object.keys(flatten({ onboarding_ui: en["onboarding_ui"] as Record<string, unknown> }))) {
  const used = usedKeys.has(key) || [...usedPrefixes].some((p) => key.startsWith(p));
  if (!used) fail(`[unused-key] ${key} is not used by any component (delete it from all locales)`);
}

// ---------------------------------------------------------------------------
// 5. legacy files must stay unreferenced
// ---------------------------------------------------------------------------

// Escapes every regex metacharacter, backslash included.
const escapeRegExp = (value: string): string => value.replace(/[.*+?^${}()|[\]\\-]/g, "\\$&");

const everything = walk("core").concat(walk("ce"), walk("app"));
for (const legacy of LEGACY_UNUSED) {
  const stem = escapeRegExp(path.basename(legacy).replace(/\.tsx?$/, ""));
  const importer = new RegExp(`from\\s+["'][^"']*/${stem}["']|from\\s+["']\\./${stem}["']`);
  for (const abs of everything) {
    if (legacyAbs.has(abs)) continue;
    if (importer.test(fs.readFileSync(abs, "utf8"))) {
      fail(
        `[legacy] ${legacy} is excluded as unused but ${rel(abs)} imports it; remove it from LEGACY_UNUSED and translate it`
      );
    }
  }
}

// ---------------------------------------------------------------------------

if (problems.length > 0) {
  console.error(`check-onboarding: ${problems.length} problem(s)\n`);
  for (const p of problems) console.error(`  - ${p}`);
  process.exit(1);
}
console.log(
  `check-onboarding: OK (${locales.length} locales, ${guardedKeys.length} guarded keys, ${scoped.length} files scanned, ${LEGACY_UNUSED.length} legacy files excluded)`
);
