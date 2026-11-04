/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: who can join and who can create workspaces
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Both switches read as "Allow ..." (KEP-83). Workspace creation is still stored
 * as DISABLE_WORKSPACE_CREATION, so the switch is the inverse of the stored
 * value and flipped again on save. Draft + shared unsaved bar like every tab.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Loader, ToggleSwitch } from "@plane/ui";
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { Section, SettingRow } from "@/components/common/paradise";
import { useUnsavedChanges } from "@/components/common/unsaved-changes";
import { useInstance } from "@/hooks/store";

type TDraft = { allowSignup?: boolean; allowWorkspaceCreation?: boolean };

export const AccessForm = observer(function AccessForm() {
  const { s } = useGodmodeStrings();
  const t = s.settings.access;
  const { fetchInstanceConfigurations, formattedConfig, updateInstanceConfigurations } = useInstance();
  const [draft, setDraft] = useState<TDraft>({});
  const [isSaving, setIsSaving] = useState(false);

  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  const saved = formattedConfig
    ? {
        allowSignup: formattedConfig.ENABLE_SIGNUP === "1",
        // Stored inverted: DISABLE_WORKSPACE_CREATION=1 means members may NOT create.
        allowWorkspaceCreation: formattedConfig.DISABLE_WORKSPACE_CREATION !== "1",
      }
    : null;
  const current = saved ? { ...saved, ...draft } : null;
  const isDirty = Boolean(
    saved &&
    current &&
    (current.allowSignup !== saved.allowSignup || current.allowWorkspaceCreation !== saved.allowWorkspaceCreation)
  );

  const save = async () => {
    if (!current) return;
    setIsSaving(true);
    try {
      await updateInstanceConfigurations({
        ENABLE_SIGNUP: current.allowSignup ? "1" : "0",
        DISABLE_WORKSPACE_CREATION: current.allowWorkspaceCreation ? "0" : "1",
      });
      setDraft({});
      setToast({ type: TOAST_TYPE.SUCCESS, title: t.saved, message: s.settings.tabs.access_methods.title });
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: t.save_failed, message: s.settings.tabs.access_methods.title });
    } finally {
      setIsSaving(false);
    }
  };

  useUnsavedChanges({
    label: s.settings.tabs.access_methods.title,
    isDirty,
    isSaving,
    onSave: save,
    onDiscard: () => setDraft({}),
  });

  if (!current) {
    return (
      <Loader className="space-y-4">
        <Loader.Item height="60px" />
        <Loader.Item height="60px" />
      </Loader>
    );
  }

  return (
    <Section title={t.section_open.title} bordered>
      <SettingRow
        title={t.signup_name}
        description={t.signup_help}
        control={
          <ToggleSwitch
            value={current.allowSignup}
            onChange={() => setDraft((d) => ({ ...d, allowSignup: !current.allowSignup }))}
            size="sm"
            disabled={isSaving}
            label={t.signup_name}
          />
        }
      />
      <SettingRow
        title={t.workspace_name}
        description={t.workspace_help}
        control={
          <ToggleSwitch
            value={current.allowWorkspaceCreation}
            onChange={() => setDraft((d) => ({ ...d, allowWorkspaceCreation: !current.allowWorkspaceCreation }))}
            size="sm"
            disabled={isSaving}
            label={t.workspace_name}
          />
        }
      />
    </Section>
  );
});
