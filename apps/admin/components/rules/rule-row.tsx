/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: one rule on the All rules screen
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Registry rules are editable here (RuleControl). Older settings are read-only:
 * the row shows the value, the default, and a link to the tab that edits it.
 */

import { useId } from "react";
import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import { Button } from "@plane/propel/button";
import type { TParadiseRuleValue, TRegistryRule, TRuleRisk } from "@plane/types";
import { cn } from "@plane/utils";
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { settingAnchor } from "@/components/command-palette/entries";
import { RuleControl } from "./rule-control";
import { RULE_KIND_CONTROLS, formatLegacyValue, formatRuleValue, kepLabel } from "./rules-model";
import type { TRuleEntry } from "./rules-model";

const badgeClass = "inline-flex items-center gap-1 rounded-control border px-2 py-0.5 text-11 font-medium";

export function RiskBadge({ risk }: { risk: TRuleRisk }) {
  const { s } = useGodmodeStrings();
  const label = s.settings.allRules.badge_risk[risk];
  return (
    <span
      className={cn(badgeClass, {
        "border-subtle bg-layer-1 text-tertiary": risk === "low",
        "border-warning-subtle bg-warning-subtle text-warning-primary": risk === "medium",
        "border-danger-strong bg-danger-subtle text-danger-primary": risk === "high",
      })}
    >
      {risk === "high" && <ShieldAlert aria-hidden className="size-3" />}
      {label}
    </span>
  );
}

export function ChangedBadge() {
  const { s } = useGodmodeStrings();
  return (
    <span className={cn(badgeClass, "border-accent-strong-40 bg-accent-subtle text-accent-primary")}>
      {s.settings.allRules.badge_changed}
    </span>
  );
}

type Props = {
  entry: TRuleEntry;
  /** Registry rules: the value on screen (draft or saved). */
  value: TParadiseRuleValue;
  /** Is the value on screen different from the default? */
  isChanged: boolean;
  /** Is there an unsaved edit on this rule? */
  hasDraft: boolean;
  error?: string | null;
  disabled: boolean;
  onChange: (value: TParadiseRuleValue) => void;
  onReset: () => void;
  onApply: () => void;
};

const actionClass = "min-h-11";

export function RuleRow({ entry, value, isChanged, hasDraft, error, disabled, onChange, onReset, onApply }: Props) {
  const { s, fill } = useGodmodeStrings();
  const t = s.settings;
  const a = t.allRules;
  const uid = useId();
  const controlId = `${uid}-control`;
  const helpId = `${uid}-help`;
  const errorId = `${uid}-error`;
  const { rule } = entry;
  const describedBy = [entry.help ? helpId : "", error ? errorId : ""].filter(Boolean).join(" ") || undefined;

  const registry: TRegistryRule | null = rule.source === "registry" ? rule : null;
  const labelable = registry ? ["number", "select", "text"].includes(RULE_KIND_CONTROLS[registry.kind]) : false;
  const canApply = registry?.store === "member_default" && Boolean(registry.apply_section);

  const defaultText =
    rule.source === "registry"
      ? formatRuleValue(rule, rule.default, a)
      : formatLegacyValue(rule, rule.default, t, entry.unit);
  const legacyValue = rule.source === "legacy" ? formatLegacyValue(rule, rule.value, t, entry.unit) : "";

  return (
    <div
      id={settingAnchor(rule.key)}
      className="flex scroll-mt-20 flex-col items-stretch gap-3 px-4 py-4 transition-colors duration-500 data-[highlight=true]:bg-accent-subtle md:flex-row md:items-start md:justify-between md:gap-6"
    >
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <h3 className="text-13 font-medium text-primary">
            {labelable ? <label htmlFor={controlId}>{entry.name}</label> : entry.name}
          </h3>
          {isChanged && <ChangedBadge />}
          <RiskBadge risk={rule.risk} />
        </div>
        {entry.help && (
          <p id={helpId} className="text-11 leading-5 text-tertiary">
            {entry.help}
          </p>
        )}
        <p className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-11 text-tertiary">
          <span>
            <span className="sr-only">{a.key_label}: </span>
            <code className="break-all">{rule.key}</code>
          </span>
          {registry && <span>{a.applies[registry.applies]}</span>}
          {registry?.kep && <span>{kepLabel(registry.kep, a)}</span>}
        </p>
        {isChanged && <p className="text-11 text-tertiary">{fill(a.default_prefix, { value: defaultText })}</p>}
        {error && (
          <p id={errorId} className="text-11 text-danger-primary" role="alert">
            {error}
          </p>
        )}
      </div>

      <div className="min-w-0 space-y-2 md:w-72 md:shrink-0">
        {registry ? (
          <>
            <RuleControl
              rule={registry}
              value={value}
              onChange={onChange}
              label={entry.name}
              controlId={controlId}
              describedBy={describedBy}
              invalid={Boolean(error)}
              disabled={disabled}
            />
            <div className="flex flex-wrap items-center gap-2">
              <Button
                variant="secondary"
                size="lg"
                className={actionClass}
                disabled={disabled || (!registry.changed && !hasDraft)}
                aria-label={fill(a.reset_name, { name: entry.name })}
                onClick={onReset}
              >
                {a.reset}
              </Button>
              {canApply && (
                <Button
                  variant="secondary"
                  size="lg"
                  className={actionClass}
                  disabled={disabled || hasDraft}
                  aria-label={fill(a.apply_all_name, { name: entry.name })}
                  onClick={onApply}
                >
                  {a.apply_all}
                </Button>
              )}
            </div>
            {canApply && <p className="text-11 text-tertiary">{hasDraft ? a.apply_save_first : a.apply_all_note}</p>}
          </>
        ) : (
          <>
            <p className="text-13 text-primary">
              <span className="sr-only">{a.current_label}: </span>
              {legacyValue}
            </p>
            {entry.editOn && (
              <Link
                href={`${entry.editOn.href}#${settingAnchor(rule.key)}`}
                className="inline-flex min-h-11 items-center text-13 font-medium text-accent-primary hover:underline focus-visible:rounded-field focus-visible:ring-2 focus-visible:ring-accent-strong focus-visible:outline-none"
              >
                {fill(a.edit_on, { tab: entry.editOn.title })}
              </Link>
            )}
          </>
        )}
      </div>
    </div>
  );
}
