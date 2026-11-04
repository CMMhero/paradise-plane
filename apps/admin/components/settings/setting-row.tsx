/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: one registry-driven setting row
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import type { TInstanceSetting } from "@plane/types";
import { SettingRow } from "@/components/common/paradise";
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { settingAnchor } from "@/components/command-palette/entries";
import { SettingControl } from "./setting-control";
import { describeDayList, describeField, formatSettingValue, normalizeValue } from "./setting-utils";

type Props = {
  def: TInstanceSetting;
  value: string;
  onChange: (value: string) => void;
  unit?: string;
  /** Validation message from the client check or the server's 400 body. */
  error?: string | null;
  disabled: boolean;
  /** Extra line under the help text, e.g. the office timezone for time rows. */
  hint?: ReactNode;
};

/**
 * Title and help from the strings, control from the registry kind, plus the
 * server default next to any value that differs from it.
 */
export function RegistrySettingRow({ def, value, onChange, unit, error, disabled, hint }: Props) {
  const { s, fill } = useGodmodeStrings();
  const t = s.settings;
  const { name, help } = describeField(t, def.key);
  const unitLabel = unit ? (t.units[unit] ?? unit) : undefined;
  const differsFromDefault = normalizeValue(def, value) !== normalizeValue(def, def.default);

  return (
    <SettingRow
      id={settingAnchor(def.key)}
      title={name}
      description={help}
      note={
        <>
          {def.kind === "day_list" && !error && <p className="text-11 text-secondary">{describeDayList(t, value)}</p>}
          {hint}
          {error ? (
            <p className="text-11 text-danger-primary" role="alert">
              {error}
            </p>
          ) : (
            differsFromDefault && (
              <p className="text-11 text-tertiary">
                {fill(t.controls.default_prefix, { value: formatSettingValue(def, def.default, t, unitLabel) })}
              </p>
            )
          )}
        </>
      }
      control={
        <SettingControl
          def={def}
          value={value}
          onChange={onChange}
          label={name}
          unit={unitLabel}
          invalid={Boolean(error)}
          disabled={disabled}
        />
      }
    />
  );
}
