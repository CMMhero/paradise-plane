/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: volume suara pemberitahuan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Volume (0..100), bisu, dan tombol Pratinjau. Disimpan ke `profile.theme`
 * lewat `updateUserTheme`, sama seperti preferensi tampilan, jadi per akun.
 * Bawaan akun baru diatur di God Mode > Members > Defaults. Logika simpannya
 * dipakai bersama dengan popup suara di Obrolan (`useVolumeSuara`).
 */

import { observer } from "mobx-react";
import { Play } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { ToggleSwitch } from "@plane/ui";
// components
import { SettingsControlItem } from "@/components/settings/control-item";
// hooks
import { useVolumeSuara } from "@/hooks/use-volume-suara";

export const PreferensiSuara = observer(function PreferensiSuara() {
  const { t } = useTranslation();
  const { volume, bisu, geser, setBisu, pratinjau } = useVolumeSuara();

  return (
    <>
      <SettingsControlItem
        title={t("chatux_kelola_ui.sound_volume")}
        description={t("chatux_kelola_ui.sound_volume_desc")}
        control={
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={volume}
              disabled={bisu}
              onChange={(e) => geser(Number(e.target.value))}
              aria-label={t("chatux_kelola_ui.sound_volume")}
              aria-valuetext={`${volume}%`}
              className="h-2 w-40 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50 sentuh:h-6"
            />
            <span className="w-10 text-right text-13 text-secondary tabular-nums">{volume}%</span>
            <Button variant="secondary" size="base" prependIcon={<Play />} onClick={pratinjau}>
              {t("chatux_kelola_ui.sound_preview")}
            </Button>
          </div>
        }
      />
      <SettingsControlItem
        title={t("chatux_kelola_ui.sound_mute")}
        description={t("chatux_kelola_ui.sound_mute_desc")}
        control={<ToggleSwitch value={bisu} label={t("chatux_kelola_ui.sound_mute")} onChange={() => setBisu(!bisu)} />}
      />
    </>
  );
});
