/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: penggeser volume suara pemberitahuan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Logika penggeser volume yang dipakai bersama oleh Profile > Preferences dan
 * popup suara di Obrolan & panel Pemberitahuan. Satu sumber supaya keduanya
 * menyimpan dengan jeda dan pesan gagal yang sama.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "@plane/i18n";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { SUARA_PABRIK } from "@/lib/suara";
import { useUserProfile } from "./store/user";
import { useSuaraNotifikasi } from "./use-suara-notifikasi";

/** Simpan sesudah penggeser diam sejenak, bukan tiap langkah. */
const JEDA_SIMPAN_MS = 400;

export const useVolumeSuara = () => {
  const { t } = useTranslation();
  const { updateUserTheme } = useUserProfile();
  const { suara, pratinjau } = useSuaraNotifikasi();
  const [volume, setVolume] = useState(suara.volume);
  const waktuRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Ikuti nilai tersimpan kalau berubah dari tempat lain (perangkat lain, God Mode, popup lain).
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- sync slider with the stored value
    setVolume(suara.volume);
  }, [suara.volume]);

  useEffect(
    () => () => {
      if (waktuRef.current) clearTimeout(waktuRef.current);
    },
    []
  );

  const simpan = useCallback(
    async (data: { volume_suara?: number; suara_bisu?: boolean }) => {
      try {
        await updateUserTheme(data);
      } catch {
        setToast({ type: TOAST_TYPE.ERROR, title: t("chatux_kelola_ui.sound_save_failed") });
      }
    },
    [updateUserTheme, t]
  );

  const geser = useCallback(
    (nilai: number) => {
      setVolume(nilai);
      if (waktuRef.current) clearTimeout(waktuRef.current);
      waktuRef.current = setTimeout(() => void simpan({ volume_suara: nilai }), JEDA_SIMPAN_MS);
    },
    [simpan]
  );

  /** Menyalakan dari volume 0 tidak akan terdengar; kembalikan ke volume pabrik. */
  const setBisu = useCallback(
    (bisu: boolean) => {
      const tambahan = !bisu && volume === 0 ? { volume_suara: SUARA_PABRIK.volume } : {};
      void simpan({ suara_bisu: bisu, ...tambahan });
    },
    [simpan, volume]
  );

  return { volume, bisu: suara.bisu, geser, setBisu, pratinjau: () => pratinjau(volume) };
};
