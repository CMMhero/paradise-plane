/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kredensial Google Calendar di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useForm } from "react-hook-form";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { IFormattedInstanceConfiguration, TInstanceGoogleCalendarConfigurationKeys } from "@plane/types";
// components
import { ControllerInput } from "@/components/common/controller-input";
import { UnsavedBar } from "@/components/common/unsaved-changes";
// hooks
import { useInstance } from "@/hooks/store";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";

type NilaiKredensial = Record<TInstanceGoogleCalendarConfigurationKeys, string>;

type Props = {
  config: IFormattedInstanceConfiguration;
};

export function KredensialKalender({ config }: Props) {
  const { s } = useGodmodeStrings();
  const t = s.fitur;
  const { updateInstanceConfigurations } = useInstance();
  const {
    handleSubmit,
    control,
    formState: { isSubmitting, isDirty },
    reset,
  } = useForm<NilaiKredensial>({
    defaultValues: {
      GOOGLE_CALENDAR_CLIENT_ID: config.GOOGLE_CALENDAR_CLIENT_ID ?? "",
      GOOGLE_CALENDAR_CLIENT_SECRET: config.GOOGLE_CALENDAR_CLIENT_SECRET ?? "",
    },
  });

  const simpan = async (nilai: NilaiKredensial) => {
    try {
      await updateInstanceConfigurations(nilai);
      reset(nilai);
      setToast({ type: TOAST_TYPE.SUCCESS, title: t.saved, message: t.gcal_name });
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: t.save_failed, message: t.gcal_name });
    }
  };

  return (
    <div className="space-y-4 py-4">
      <UnsavedBar
        label={t.gcal_name}
        isDirty={isDirty}
        isSaving={isSubmitting}
        onSave={() => handleSubmit(simpan)()}
        onDiscard={() => reset()}
      />
      <div className="grid grid-cols-1 gap-x-8 gap-y-4 lg:grid-cols-2">
        <ControllerInput
          control={control}
          type="text"
          name="GOOGLE_CALENDAR_CLIENT_ID"
          label={t.gcal_client_id}
          placeholder="123456789-abc.apps.googleusercontent.com"
          error={false}
          required={false}
        />
        <ControllerInput
          control={control}
          type="password"
          name="GOOGLE_CALENDAR_CLIENT_SECRET"
          label={t.gcal_client_secret}
          placeholder="GOCSPX-..."
          error={false}
          required={false}
        />
      </div>
      <p className="text-11 text-tertiary">{t.gcal_hint}</p>
      <Button variant="primary" size="lg" onClick={handleSubmit(simpan)} loading={isSubmitting} disabled={!isDirty}>
        {isSubmitting ? t.saving : t.save}
      </Button>
    </div>
  );
}
