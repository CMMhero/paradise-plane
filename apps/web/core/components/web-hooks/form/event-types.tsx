/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// types
import { useTranslation } from "@plane/i18n";
import type { TWebhookEventTypes } from "@plane/types";
import { RadioGroup } from "@plane/propel/radio-group";

type Props = {
  value: string;
  onChange: (value: TWebhookEventTypes) => void;
};

const WEBHOOK_EVENT_TYPES: { key: TWebhookEventTypes; i18n_label: string }[] = [
  {
    key: "all",
    i18n_label: "workspace_settings.settings.webhooks.options.all",
  },
  {
    key: "individual",
    i18n_label: "workspace_settings.settings.webhooks.options.individual",
  },
];

export function WebhookOptions(props: Props) {
  const { value, onChange } = props;
  const { t } = useTranslation();

  return (
    <>
      <h6 className="text-13 font-medium">{t("workspace_settings.settings.webhooks.modal.question")}</h6>
      <RadioGroup
        name="webhook-event-types"
        aria-label={t("workspace_settings.settings.webhooks.modal.question")}
        className="-mx-2"
        value={value}
        onValueChange={(next) => onChange(next as TWebhookEventTypes)}
      >
        {WEBHOOK_EVENT_TYPES.map((option) => (
          <RadioGroup.Item key={option.key} value={option.key} label={t(option.i18n_label)} />
        ))}
      </RadioGroup>
    </>
  );
}
