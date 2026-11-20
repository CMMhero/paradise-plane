/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: urutan linimasa aktivitas per akun
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu sumber untuk tombol urut di linimasa dan baris di Profile > Preferences.
 * Disimpan di `profile.theme.urutan_aktivitas`; kosong = terbaru di atas.
 */

import { useCallback } from "react";
import { E_SORT_ORDER } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { useUserProfile } from "./store/user";

export const useUrutanAktivitas = () => {
  const { t } = useTranslation();
  const { data, updateUserTheme } = useUserProfile();
  const urutan = data?.theme?.urutan_aktivitas === "asc" ? E_SORT_ORDER.ASC : E_SORT_ORDER.DESC;

  const setUrutan = useCallback(
    async (baru: E_SORT_ORDER) => {
      if (baru === urutan) return;
      try {
        await updateUserTheme({ urutan_aktivitas: baru });
      } catch {
        setToast({ type: TOAST_TYPE.ERROR, title: t("ui_fixes.activity_order_save_failed") });
      }
    },
    [urutan, updateUserTheme, t]
  );

  return { urutan, setUrutan };
};
