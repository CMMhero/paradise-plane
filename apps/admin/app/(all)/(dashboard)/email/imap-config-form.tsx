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
// hooks
import { useInstance } from "@/hooks/store";

type Props = {
  config: IFormattedInstanceConfiguration;
};

type ImapFormValues = Record<TInstanceImapConfigurationKeys, string>;

const KEAMANAN = { "1": "SSL/TLS (biasanya port 993)", "0": "Tanpa enkripsi (port 143)" } as const;

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
      description: "Alamat kotak masuk yang dipantau, bukan alamat pengirim.",
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

  const ssl = watch("IMAP_USE_SSL") === "1" ? "1" : "0";

  const onSubmit = async (data: ImapFormValues) => {
    await updateInstanceConfigurations(data)
      .then(() =>
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: "Tersimpan",
          message: "Setelan email masuk disimpan. Belum ada fitur yang membacanya.",
        })
      )
      .catch((err) => {
        setToast({
          type: TOAST_TYPE.ERROR,
          title: "Gagal",
          message: (err as { error?: string })?.error ?? "Setelan email masuk gagal disimpan.",
        });
      });
  };

  return (
    <div className="space-y-6">
      <div className="border-amber-500/40 bg-amber-500/10 flex max-w-4xl items-start gap-3 rounded border p-3">
        <AlertTriangle className="text-amber-600 mt-0.5 size-4 shrink-0" />
        <div className="text-13 text-secondary">
          <span className="font-medium text-primary">Tersimpan, belum dipakai.</span> Instance ini belum punya fitur
          yang memproses email masuk, jadi mengisi kolom di bawah tidak membuat email berubah jadi work item. Gunanya
          menyimpan setelan mail kantor di satu tempat bersama setelan kirim.
        </div>
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
          <h4 className="text-13 text-tertiary">Keamanan</h4>
          <CustomSelect
            value={ssl}
            label={KEAMANAN[ssl]}
            onChange={(v: "0" | "1") => setValue("IMAP_USE_SSL", v, { shouldDirty: true })}
            buttonClassName="rounded-md border-subtle"
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
          {isSubmitting ? "Menyimpan" : "Simpan setelan masuk"}
        </Button>
      </div>
    </div>
  );
}
