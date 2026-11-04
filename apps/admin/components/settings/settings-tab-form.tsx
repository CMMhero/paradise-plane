/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: draft + save model of a registry settings tab
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * One tab = one draft. Edits stay local until Save in the shared unsaved bar.
 * A sensitive key in the draft opens the typed confirmation first. The server
 * is all-or-nothing: a 400 with `errors` marks the rows and nothing is saved.
 */

import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { INSTANCE_SETTINGS_CONFIRM_PHRASE } from "@plane/constants";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TInstanceSetting, TInstanceSettingsError } from "@plane/types";
import { Loader } from "@plane/ui";
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { Section } from "@/components/common/paradise";
import { useUnsavedChanges } from "@/components/common/unsaved-changes";
import { useInstanceSettings } from "@/hooks/use-instance-settings";
import { ConfirmRulesModal } from "./confirm-rules-modal";
import type { TRuleChange } from "./confirm-rules-modal";
import { SETTINGS_LAYOUT } from "./layouts";
import type { TSettingsTabId } from "./layouts";
import { RegistrySettingRow } from "./setting-row";
import { describeField, formatSettingValue, normalizeValue, validateValue } from "./setting-utils";

type Props = {
  tab: TSettingsTabId;
  /** Shown in the unsaved bar and the success toast. */
  tabTitle: string;
  /** Rendered above the sections (explanations that belong to this tab). */
  intro?: ReactNode;
  /** Label time rows with the office timezone (Schedule tab). */
  showOfficeZone?: boolean;
  /** Rendered below the sections (a second form that belongs to this tab). */
  after?: ReactNode;
  /** A toggle that is off cannot be turned on while it has a reason here (turning off is always allowed). */
  blockedOn?: Record<string, string>;
};

export function SettingsTabForm({ tab, tabTitle, intro, showOfficeZone = false, after, blockedOn }: Props) {
  const { s, fill } = useGodmodeStrings();
  const t = s.settings;
  const { settings, error, update } = useInstanceSettings();
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);

  const valueOf = (key: string): string => draft[key] ?? settings?.[key]?.value ?? "";

  // Rows the server knows and whose condition holds. Unknown keys are skipped (KEP-45).
  const sections = useMemo(() => {
    if (!settings) return [];
    const current = (key: string) => draft[key] ?? settings[key]?.value ?? "";
    return SETTINGS_LAYOUT[tab]
      .map((section) => ({
        ...section,
        rows: section.rows.flatMap((row) => {
          const def = settings[row.key];
          return def && (!row.showWhen || row.showWhen(current)) ? [{ row, def }] : [];
        }),
      }))
      .filter((section) => section.rows.length > 0);
  }, [settings, draft, tab]);

  const visible = sections.flatMap((section) => section.rows);

  const changed: TInstanceSetting[] = visible
    .filter(({ def }) => draft[def.key] !== undefined && normalizeValue(def, draft[def.key]) !== def.value)
    .map(({ def }) => def);

  const clientErrors: Record<string, string> = {};
  for (const def of changed) {
    const message = validateValue(def, valueOf(def.key), t);
    if (message) clientErrors[def.key] = message;
  }
  const hasClientErrors = Object.keys(clientErrors).length > 0;

  const isAllDefault = visible.every(
    ({ def }) => normalizeValue(def, valueOf(def.key)) === normalizeValue(def, def.default)
  );
  const hasSensitive = visible.some(({ def }) => def.sensitive);
  const sensitiveChanges: TRuleChange[] = changed
    .filter((def) => def.sensitive)
    .map((def) => {
      const unit = SETTINGS_LAYOUT[tab].flatMap((sec) => sec.rows).find((r) => r.key === def.key)?.unit;
      const unitLabel = unit ? t.units[unit] : undefined;
      return {
        key: def.key,
        name: describeField(t, def.key).name,
        from: formatSettingValue(def, def.value, t, unitLabel),
        to: formatSettingValue(def, normalizeValue(def, valueOf(def.key)), t, unitLabel),
      };
    });

  const setValue = (key: string, value: string) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
    setServerErrors((prev) => {
      if (!(key in prev)) return prev;
      return Object.fromEntries(Object.entries(prev).filter(([k]) => k !== key));
    });
  };

  const discard = () => {
    setDraft({});
    setServerErrors({});
  };

  const save = async (confirm?: string) => {
    setIsSaving(true);
    try {
      const values = Object.fromEntries(changed.map((def) => [def.key, normalizeValue(def, valueOf(def.key))]));
      await update({ values, ...(confirm ? { confirm } : {}) });
      setDraft({});
      setServerErrors({});
      setIsConfirmOpen(false);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t.form.saved_title,
        message: fill(t.form.saved_message, { tab: tabTitle }),
      });
    } catch (err) {
      const body = err as TInstanceSettingsError;
      if (body?.errors) {
        setServerErrors(body.errors);
        setIsConfirmOpen(false);
        setToast({ type: TOAST_TYPE.ERROR, title: t.form.save_failed_title, message: t.form.save_failed_message });
      } else if (body?.error === "confirm_required") {
        setIsConfirmOpen(true);
        setToast({ type: TOAST_TYPE.ERROR, title: t.form.save_failed_title, message: s.settings.confirm.required });
      } else {
        setToast({
          type: TOAST_TYPE.ERROR,
          title: t.form.save_failed_title,
          message: body?.error ?? t.form.save_failed_message,
        });
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleSave = () => {
    if (changed.length === 0) return;
    if (hasClientErrors) {
      setToast({ type: TOAST_TYPE.ERROR, title: t.form.save_failed_title, message: t.validation.fix_first });
      return;
    }
    if (sensitiveChanges.length > 0) {
      setIsConfirmOpen(true);
      return;
    }
    void save();
  };

  useUnsavedChanges({
    label: tabTitle,
    isDirty: changed.length > 0,
    isSaving,
    canSave: !hasClientErrors,
    onSave: handleSave,
    onDiscard: discard,
  });

  if (error) return <p className="text-13 text-danger-primary">{t.form.load_failed}</p>;
  if (!settings) {
    return (
      <Loader className="space-y-4">
        <Loader.Item height="60px" />
        <Loader.Item height="60px" />
        <Loader.Item height="60px" />
      </Loader>
    );
  }

  const officeZone = settings.OFFICE_TIMEZONE?.value;

  return (
    <div className="space-y-8">
      {intro}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-11 text-tertiary">
          {hasSensitive
            ? fill(t.form.sensitive_note, { phrase: INSTANCE_SETTINGS_CONFIRM_PHRASE })
            : t.form.reset_confirm_hint}
        </p>
        <Button
          variant="secondary"
          size="base"
          disabled={isSaving || isAllDefault}
          onClick={() =>
            setDraft((prev) => ({
              ...prev,
              ...Object.fromEntries(visible.map(({ def }) => [def.key, def.default])),
            }))
          }
        >
          {t.form.reset}
        </Button>
      </div>

      {sections.map((section) => (
        <Section
          key={section.id}
          title={t.sections[section.id].title}
          description={
            "hint" in t.sections[section.id] ? (t.sections[section.id] as { hint?: string }).hint : undefined
          }
          bordered
        >
          {section.rows.map(({ row, def }) => (
            <RegistrySettingRow
              key={def.key}
              def={def}
              value={valueOf(def.key)}
              unit={row.unit}
              error={serverErrors[def.key] ?? clientErrors[def.key]}
              disabled={isSaving || Boolean(blockedOn?.[def.key] && valueOf(def.key) !== "1")}
              onChange={(value) => setValue(def.key, value)}
              hint={
                blockedOn?.[def.key] && valueOf(def.key) !== "1" ? (
                  <p className="text-11 text-warning-primary">{blockedOn[def.key]}</p>
                ) : showOfficeZone && def.kind === "time" && officeZone ? (
                  <p className="text-11 text-secondary">{fill(t.controls.time_in_zone, { zone: officeZone })}</p>
                ) : undefined
              }
            />
          ))}
        </Section>
      ))}

      {after}

      <ConfirmRulesModal
        isOpen={isConfirmOpen}
        changes={sensitiveChanges}
        isSaving={isSaving}
        onCancel={() => setIsConfirmOpen(false)}
        onConfirm={(phrase) => void save(phrase)}
      />
    </div>
  );
}
