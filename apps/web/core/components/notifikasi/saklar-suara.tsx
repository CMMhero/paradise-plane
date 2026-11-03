/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: popup suara pemberitahuan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { Play, Volume1, Volume2, VolumeX } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { IconButton } from "@plane/propel/icon-button";
import { Popover } from "@plane/propel/popover";
import { ToggleSwitch } from "@plane/ui";
import { cn } from "@plane/utils";
import { useVolumeSuara } from "@/hooks/use-volume-suara";
import { SaklarPeramban } from "./saklar-peramban";

/**
 * SATU tombol suara untuk seluruh bunyi pemberitahuan, bukan satu per jenis.
 *
 * Klik membuka popup berisi volume, bisu, dan pratinjau. Dulu tombol ini cuma
 * saklar bisu dan volumenya tersembunyi di Profile > Preferences; orang yang
 * merasa bunyinya terlalu keras malah mematikannya sama sekali.
 *
 * Ditempatkan di dua tempat, dan itu bukan duplikasi: keduanya menulis ke
 * `profile.theme` akun yang sama. Orang yang terganggu bunyi pesan mencarinya
 * di halaman Obrolan, orang yang terganggu bunyi tugas mencarinya di panel
 * Pemberitahuan, dan keduanya menemukan setelan yang sama.
 */
export const SaklarSuara = observer(function SaklarSuara({ className = "" }: { className?: string }) {
  const { t } = useTranslation();
  const { volume, bisu, geser, setBisu, pratinjau } = useVolumeSuara();
  const nyala = !bisu && volume > 0;
  const ikon = !nyala ? VolumeX : volume < 50 ? Volume1 : Volume2;

  return (
    <Popover>
      <Popover.Button
        render={
          <IconButton
            variant="ghost"
            size="xl"
            icon={ikon}
            aria-label={t("chatux_kelola_ui.sound_volume")}
            title={nyala ? t("notification_ui.sound_on") : t("notification_ui.sound_off")}
            className={cn("shrink-0", className)}
          />
        }
      />
      <Popover.Panel
        side="bottom"
        align="end"
        className="z-30 w-64 rounded-popover border-[0.5px] border-strong bg-surface-1 p-3 shadow-raised-200"
      >
        <div className="flex flex-col gap-3">
          <p className="text-13 font-medium text-primary">{t("chatux_kelola_ui.sound_volume")}</p>

          <div className="flex items-center gap-2">
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
              className="h-2 min-w-0 flex-1 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50 sentuh:h-6"
            />
            <span className="w-9 text-right text-12 text-secondary tabular-nums">{volume}%</span>
          </div>

          <div className="flex items-center justify-between gap-2">
            <span className="text-12 text-secondary">{t("chatux_kelola_ui.sound_mute")}</span>
            <ToggleSwitch value={bisu} label={t("chatux_kelola_ui.sound_mute")} onChange={() => setBisu(!bisu)} />
          </div>

          <Button
            variant="secondary"
            size="base"
            prependIcon={<Play />}
            onClick={pratinjau}
            disabled={volume === 0}
            className="w-full"
          >
            {t("chatux_kelola_ui.sound_preview")}
          </Button>

          <SaklarPeramban />
        </div>
      </Popover.Panel>
    </Popover>
  );
});
