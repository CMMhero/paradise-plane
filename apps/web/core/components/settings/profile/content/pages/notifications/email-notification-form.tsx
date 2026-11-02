/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { mutate } from "swr";
// plane imports
import { NOTIFICATION_DIGEST_SECTIONS, NOTIFICATION_EVENTS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { IUserEmailNotificationSettings, TNotificationPreferenceKey } from "@plane/types";
import { ToggleSwitch } from "@plane/ui";
// components
import { SettingsControlItem } from "@/components/settings/control-item";
// services
import { UserService } from "@/services/user.service";

type Props = {
  data: IUserEmailNotificationSettings;
};

type TKunciForm = TNotificationPreferenceKey | "ikut_bawaan_jabatan";

// services
const userService = new UserService();

export const EMAIL_SETTINGS_SWR_KEY = "CURRENT_USER_EMAIL_NOTIFICATION_SETTINGS";

/**
 * Kustomisasi Paradise (2026-11-02): satu matriks per jenis kabar, kolom inbox di
 * aplikasi dan email, plus bagian ringkasan harian yang bisa dipilih satu per satu.
 * Daftar barisnya dari `NOTIFICATION_EVENTS`, sama dengan God Mode.
 */
export const NotificationsProfileSettingsForm = observer(function NotificationsProfileSettingsForm(props: Props) {
  const { data } = props;
  const { t } = useTranslation();
  // Salinan lokal supaya saklar langsung bergerak; diganti jawaban server sesudah PATCH.
  const [nilai, setNilai] = useState(data);
  // Kebijakan direktur di God Mode: saklar ini selalu mati dan tak bisa dinyalakan sendiri.
  const dikunci = new Set(nilai.dikunci ?? []);

  useEffect(() => {
    setNilai(data);
  }, [data]);

  const ubah = async (key: TKunciForm, value: boolean) => {
    const sebelumnya = nilai;
    setNilai({ ...nilai, [key]: value });
    try {
      // Server mengembalikan saklar yang berlaku; mengubah satu = berhenti ikut bawaan jabatan.
      const updated: IUserEmailNotificationSettings = await userService.updateCurrentUserEmailNotificationSettings({
        [key]: value,
      });
      setNilai(updated);
      void mutate(EMAIL_SETTINGS_SWR_KEY, updated, false);
      setToast({
        title: t("success"),
        type: TOAST_TYPE.SUCCESS,
        message: t("email_notification_setting_updated_successfully"),
      });
    } catch (_error) {
      setNilai(sebelumnya);
      setToast({
        title: t("error"),
        type: TOAST_TYPE.ERROR,
        message: t("failed_to_update_email_notification_setting"),
      });
    }
  };

  return (
    <div className="flex flex-col gap-y-8">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-12 text-tertiary">
          {nilai.ikut_bawaan_jabatan ? t("shared_ui.role_defaults_on") : t("shared_ui.role_defaults_off")}
        </p>
        {!nilai.ikut_bawaan_jabatan && (
          <Button variant="secondary" size="sm" onClick={() => void ubah("ikut_bawaan_jabatan", true)}>
            {t("shared_ui.role_defaults_reset")}
          </Button>
        )}
      </div>

      <section className="flex flex-col gap-y-2" aria-labelledby="notif-matriks-judul">
        <div>
          <h3 id="notif-matriks-judul" className="text-14 font-medium text-primary">
            {t("notif_prefs_ui.events_title")}
          </h3>
          <p className="text-12 text-tertiary">{t("notif_prefs_ui.events_description")}</p>
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-subtle text-11 text-tertiary uppercase">
              <th className="py-2 text-left font-medium">{t("notif_prefs_ui.col_event")}</th>
              <th className="w-20 py-2 text-center font-medium">{t("notif_prefs_ui.col_inbox")}</th>
              <th className="w-20 py-2 text-center font-medium">{t("notif_prefs_ui.col_email")}</th>
            </tr>
          </thead>
          <tbody>
            {NOTIFICATION_EVENTS.map((ev) => {
              const judul = t(`notif_prefs_ui.event_${ev.key}`);
              return (
                <tr key={ev.key} className="border-b border-subtle last:border-b-0">
                  <td className="py-3 pr-3">
                    <span className="block text-13 text-primary">{judul}</span>
                    <span className="block text-12 text-tertiary">
                      {t(`notif_prefs_ui.event_${ev.key}_description`)}
                    </span>
                  </td>
                  <td className="py-3 text-center">
                    <ToggleSwitch
                      value={!!nilai[ev.inbox]}
                      label={`${judul}: ${t("notif_prefs_ui.col_inbox")}`}
                      onChange={(v) => void ubah(ev.inbox, v)}
                      disabled={dikunci.has(ev.inbox)}
                      size="sm"
                    />
                  </td>
                  <td className="py-3 text-center">
                    <ToggleSwitch
                      value={!!nilai[ev.email]}
                      label={`${judul}: ${t("notif_prefs_ui.col_email")}`}
                      onChange={(v) => void ubah(ev.email, v)}
                      disabled={dikunci.has(ev.email)}
                      size="sm"
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {dikunci.size > 0 && <p className="text-12 text-tertiary">{t("shared_ui.role_defaults_locked")}</p>}
      </section>

      <section className="flex flex-col gap-y-1" aria-labelledby="notif-ringkasan-judul">
        <h3 id="notif-ringkasan-judul" className="text-14 font-medium text-primary">
          {t("notif_prefs_ui.digest_title")}
        </h3>
        <SettingsControlItem
          title={t("shared_ui.daily_digest_title")}
          description={t("shared_ui.daily_digest_description")}
          control={
            <ToggleSwitch
              value={!!nilai.daily_digest}
              onChange={(v) => void ubah("daily_digest", v)}
              disabled={dikunci.has("daily_digest")}
              size="sm"
            />
          }
        />
        <SettingsControlItem
          title={t("shared_ui.daily_digest_sore_title")}
          description={t("shared_ui.daily_digest_sore_description")}
          control={
            <ToggleSwitch
              value={!!nilai.daily_digest_sore}
              onChange={(v) => void ubah("daily_digest_sore", v)}
              disabled={dikunci.has("daily_digest_sore")}
              size="sm"
            />
          }
        />
        {(nilai.daily_digest || nilai.daily_digest_sore) && (
          <div className="border-l-3 border-subtle-1 pl-3">
            <p className="pt-2 text-12 text-tertiary">{t("notif_prefs_ui.digest_sections_description")}</p>
            {NOTIFICATION_DIGEST_SECTIONS.map((bagian) => (
              <SettingsControlItem
                key={bagian}
                title={t(`notif_prefs_ui.${bagian}`)}
                description={t(`notif_prefs_ui.${bagian}_description`)}
                control={
                  <ToggleSwitch
                    value={!!nilai[bagian]}
                    onChange={(v) => void ubah(bagian, v)}
                    disabled={dikunci.has(bagian)}
                    size="sm"
                  />
                }
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
});
