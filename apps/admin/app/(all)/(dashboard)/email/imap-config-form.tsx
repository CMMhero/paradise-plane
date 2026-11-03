/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: setelan email MASUK
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useForm } from "react-hook-form";
import { AlertTriangle } from "lucide-react";
// plane imports
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { IFormattedInstanceConfiguration, TInstanceImapConfigurationKeys } from "@plane/types";
import { CustomSelect } from "@plane/ui";
// components
import type { TControllerInputFormField } from "@/components/common/controller-input";
import { ControllerInput } from "@/components/common/controller-input";
import { Callout } from "@/components/common/paradise";
import { UnsavedBar } from "@/components/common/unsaved-changes";
// hooks
import { useInstance } from "@/hooks/store";

type Props = {
  config: IFormattedInstanceConfiguration;
};

type ImapFormValues = Record<TInstanceImapConfigurationKeys, string>;

const KEAMANAN = { "1": "SSL/TLS (usually port 993)", "0": "No encryption (port 143)" } as const;

/**
 * Setelan server email masuk.
 *
 * Nilainya **tersimpan tapi belum dibaca apa pun**. Plane CE tidak punya
 * pemroses email masuk, tidak ada IMAP, POP3, maupun jalur inbound di seluruh
 * basis kode. Formulir ini ada supaya setelan mail kantor tercatat di satu
 * tempat bersama setelan kirim, dan siap dipakai kalau ingestion dibangun nanti.
 *
 * Peringatan di atas form BUKAN hiasan: form yang menerima isian lalu tidak
 * melakukan apa-apa, tanpa mengatakannya, adalah cara membuat orang menunggu
 * email yang tidak akan pernah diproses.
 */
export function InstanceImapForm({ config }: Props) {
  const { updateInstanceConfigurations } = useInstance();

  const {
    handleSubmit,
    watch,
    setValue,
    control,
    reset,
    formState: { errors, isDirty, isSubmitting },
  } = useForm<ImapFormValues>({
    defaultValues: {
      IMAP_HOST: config["IMAP_HOST"],
      IMAP_PORT: config["IMAP_PORT"],
      IMAP_HOST_USER: config["IMAP_HOST_USER"],
      IMAP_HOST_PASSWORD: config["IMAP_HOST_PASSWORD"],
      IMAP_USE_SSL: config["IMAP_USE_SSL"],
    },
  });

  const fields: TControllerInputFormField[] = [
    {
      key: "IMAP_HOST",
      type: "text",
      label: "Host",
      placeholder: "mail.paradiseperkasa.com",
      error: Boolean(errors.IMAP_HOST),
      required: false,
    },
    {
      key: "IMAP_PORT",
      type: "text",
      label: "Port",
      placeholder: "993",
      error: Boolean(errors.IMAP_PORT),
      required: false,
    },
    {
      key: "IMAP_HOST_USER",
      type: "text",
      label: "Username",
      description: "The inbox address being watched, not the sender address.",
      placeholder: "intake@paradiseperkasa.com",
      error: Boolean(errors.IMAP_HOST_USER),
      required: false,
    },
    {
      key: "IMAP_HOST_PASSWORD",
      type: "password",
      label: "Password",
      placeholder: "Password",
      error: Boolean(errors.IMAP_HOST_PASSWORD),
      required: false,
    },
  ];

  // oxlint-disable-next-line react/incompatible-library -- react-hook-form watch() is the intended API here
  const ssl = watch("IMAP_USE_SSL") === "1" ? "1" : "0";

  const onSubmit = async (data: ImapFormValues) => {
    await updateInstanceConfigurations(data)
      .then(() => {
        reset(data);
        return setToast({
          type: TOAST_TYPE.SUCCESS,
          title: "Saved",
          message: "Incoming email settings saved. Nothing reads them yet.",
        });
      })
      .catch((err) => {
        setToast({
          type: TOAST_TYPE.ERROR,
          title: "Failed",
          message: (err as { error?: string })?.error ?? "Could not save incoming email settings.",
        });
      });
  };

  return (
    <div className="space-y-6">
      <UnsavedBar
        label="Incoming email (IMAP)"
        isDirty={isDirty}
        isSaving={isSubmitting}
        onSave={() => handleSubmit(onSubmit)()}
        onDiscard={() => reset()}
      />
      <div className="max-w-4xl">
        <Callout icon={<AlertTriangle className="size-4" />} title="Saved, not used yet.">
          This instance has no feature that processes incoming email, so filling in the fields below does not turn
          emails into work items. It keeps the office mail settings in one place next to the outgoing ones.
        </Callout>
      </div>

      <div className="grid-col grid w-full max-w-4xl grid-cols-1 items-start justify-between gap-10 lg:grid-cols-2">
        {fields.map((field) => (
          <ControllerInput
            key={field.key}
            control={control}
            type={field.type}
            name={field.key}
            label={field.label}
            description={field.description}
            placeholder={field.placeholder}
            error={field.error}
            required={field.required}
          />
        ))}
        <div className="flex flex-col gap-1">
          <h4 className="text-13 text-tertiary">Security</h4>
          <CustomSelect
            value={ssl}
            label={KEAMANAN[ssl]}
            onChange={(v: "0" | "1") => setValue("IMAP_USE_SSL", v, { shouldDirty: true })}
            input
          >
            {Object.entries(KEAMANAN).map(([k, v]) => (
              <CustomSelect.Option key={k} value={k} className="w-full">
                {v}
              </CustomSelect.Option>
            ))}
          </CustomSelect>
        </div>
      </div>

      <div className="flex max-w-4xl items-center gap-4 py-1">
        <Button variant="primary" size="lg" onClick={handleSubmit(onSubmit)} loading={isSubmitting} disabled={!isDirty}>
          {isSubmitting ? "Saving" : "Save incoming settings"}
        </Button>
      </div>
    </div>
  );
}
