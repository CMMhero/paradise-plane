/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: typed confirmation for sensitive rules
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { INSTANCE_SETTINGS_CONFIRM_PHRASE } from "@plane/constants";
import { Button } from "@plane/propel/button";
import { Input } from "@plane/ui";
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { inputClass } from "@/components/common/paradise-styles";
import { EModalWidth, ParadiseModal } from "@/components/common/paradise-ui";

export type TRuleChange = { key: string; name: string; from: string; to: string };

type Props = {
  isOpen: boolean;
  changes: TRuleChange[];
  isSaving: boolean;
  onCancel: () => void;
  /** Called with the typed phrase once it matches. */
  onConfirm: (phrase: string) => void;
};

/** The body remounts per opening (see `key` at the call site), so the typed phrase never lingers. */
function ConfirmBody({ changes, isSaving, onCancel, onConfirm }: Omit<Props, "isOpen">) {
  const { s, fill } = useGodmodeStrings();
  const t = s.settings.confirm;
  const [typed, setTyped] = useState("");
  const matches = typed.trim() === INSTANCE_SETTINGS_CONFIRM_PHRASE;

  return (
    <ParadiseModal
      isOpen
      onClose={onCancel}
      width={EModalWidth.MD}
      title={t.title}
      closeLabel={t.cancel}
      footer={
        <>
          <Button variant="secondary" size="base" disabled={isSaving} onClick={onCancel}>
            {t.cancel}
          </Button>
          <Button
            variant="primary"
            size="base"
            loading={isSaving}
            disabled={!matches || isSaving}
            onClick={() => onConfirm(typed.trim())}
          >
            {t.confirm}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-13 text-secondary">{t.intro}</p>
        <div className="space-y-1">
          <div className="text-12 font-medium text-secondary">{t.changes_title}</div>
          <ul className="space-y-1 rounded-card border border-subtle bg-layer-1 p-3">
            {changes.map((c) => (
              <li key={c.key} className="text-12 text-primary">
                <span className="font-medium">{c.name}:</span> {fill(t.from_to, { from: c.from, to: c.to })}
              </li>
            ))}
          </ul>
        </div>
        <div className="space-y-1">
          <p className="text-12 text-secondary">{fill(t.instruction, { phrase: INSTANCE_SETTINGS_CONFIRM_PHRASE })}</p>
          <Input
            type="text"
            autoComplete="off"
            value={typed}
            placeholder={INSTANCE_SETTINGS_CONFIRM_PHRASE}
            aria-label={INSTANCE_SETTINGS_CONFIRM_PHRASE}
            aria-invalid={typed.length > 0 && !matches}
            className={`${inputClass} w-full`}
            onChange={(e) => setTyped(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && matches && !isSaving) onConfirm(typed.trim());
            }}
          />
          {typed.length > 0 && !matches && <p className="text-11 text-danger-primary">{t.wrong_phrase}</p>}
        </div>
      </div>
    </ParadiseModal>
  );
}

export function ConfirmRulesModal({ isOpen, ...rest }: Props) {
  return isOpen ? <ConfirmBody {...rest} /> : null;
}
