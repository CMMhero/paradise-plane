/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: archive and close timing a new project starts with
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Shown on Work rules > Archiving next to the instance ceiling, because the two
 * run together: a project may archive sooner, never later than the ceiling.
 * Stored in the project defaults (archive_in / close_in), not in the registry.
 */

import { useState } from "react";
import useSWR from "swr";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { InstanceMemberService } from "@plane/services";
import { CustomSelect, Loader } from "@plane/ui";
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { Section, SettingRow } from "@/components/common/paradise";
import { useUnsavedChanges } from "@/components/common/unsaved-changes";

const memberService = new InstanceMemberService();

type TArchiveTiming = { archive_in: number; close_in: number };

/** Months offered in the select; 0 turns the automation off. */
const MONTHS = Array.from({ length: 13 }, (_, i) => i);

function MonthsSelect({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  disabled: boolean;
}) {
  const { s, fill } = useGodmodeStrings();
  const text = (n: number) => (n === 0 ? s.settings.archiving.off : fill(s.settings.archiving.months, { count: n }));
  return (
    <CustomSelect
      value={value}
      label={text(value)}
      onChange={(v: number) => onChange(Number(v))}
      buttonClassName="w-full md:w-48"
      maxHeight="lg"
      disabled={disabled}
      input
      aria-label={label}
    >
      {MONTHS.map((n) => (
        <CustomSelect.Option key={n} value={n}>
          {text(n)}
        </CustomSelect.Option>
      ))}
    </CustomSelect>
  );
}

export function ProjectArchiveDefaults() {
  const { s, fill } = useGodmodeStrings();
  const t = s.settings.archiving;
  const { data, error, mutate } = useSWR("INSTANCE_PROJECT_DEFAULTS", () => memberService.bawaanProject());
  const [draft, setDraft] = useState<Partial<TArchiveTiming>>({});
  const [isSaving, setIsSaving] = useState(false);

  const saved: TArchiveTiming | null = data ? { archive_in: data.archive_in, close_in: data.close_in } : null;
  const current: TArchiveTiming | null = saved ? { ...saved, ...draft } : null;
  const isDirty = Boolean(
    saved && current && (current.archive_in !== saved.archive_in || current.close_in !== saved.close_in)
  );
  const factory: TArchiveTiming | null = data
    ? { archive_in: data.pabrik.archive_in, close_in: data.pabrik.close_in }
    : null;
  const isFactory = Boolean(
    current && factory && current.archive_in === factory.archive_in && current.close_in === factory.close_in
  );

  const save = async () => {
    if (!current) return;
    setIsSaving(true);
    try {
      const fresh = await memberService.ubahBawaanProject(current);
      await mutate(fresh, { revalidate: false });
      setDraft({});
      setToast({ type: TOAST_TYPE.SUCCESS, title: t.saved, message: t.label });
    } catch (err) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t.save_failed,
        message: (err as { error?: string })?.error ?? t.save_failed,
      });
    } finally {
      setIsSaving(false);
    }
  };

  useUnsavedChanges({
    label: t.label,
    isDirty,
    isSaving,
    onSave: save,
    onDiscard: () => setDraft({}),
  });

  if (error) return <p className="text-13 text-danger-primary">{t.load_failed}</p>;
  if (!current) {
    return (
      <Loader className="space-y-4">
        <Loader.Item height="60px" />
        <Loader.Item height="60px" />
      </Loader>
    );
  }

  return (
    <Section
      title={t.projects_title}
      description={t.projects_hint}
      actions={
        <Button
          variant="secondary"
          size="base"
          disabled={isSaving || isFactory}
          onClick={() => factory && setDraft(factory)}
        >
          {t.reset}
        </Button>
      }
      bordered
    >
      <SettingRow
        title={t.archive_in}
        description={t.projects_help}
        note={
          factory && current.archive_in !== factory.archive_in ? (
            <p className="text-11 text-tertiary">
              {fill(s.settings.controls.default_prefix, {
                value: factory.archive_in === 0 ? t.off : fill(t.months, { count: factory.archive_in }),
              })}
            </p>
          ) : undefined
        }
        control={
          <MonthsSelect
            label={t.archive_in}
            value={current.archive_in}
            onChange={(archive_in) => setDraft((d) => ({ ...d, archive_in }))}
            disabled={isSaving}
          />
        }
      />
      <SettingRow
        title={t.close_in}
        description={t.projects_help}
        note={
          factory && current.close_in !== factory.close_in ? (
            <p className="text-11 text-tertiary">
              {fill(s.settings.controls.default_prefix, {
                value: factory.close_in === 0 ? t.off : fill(t.months, { count: factory.close_in }),
              })}
            </p>
          ) : undefined
        }
        control={
          <MonthsSelect
            label={t.close_in}
            value={current.close_in}
            onChange={(close_in) => setDraft((d) => ({ ...d, close_in }))}
            disabled={isSaving}
          />
        }
      />
    </Section>
  );
}
