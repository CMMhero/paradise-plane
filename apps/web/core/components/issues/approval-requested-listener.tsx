/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: toast "Requested for approval" (KEP-55)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Dipasang sekali di lapisan workspace. Mendengar event dari store
 * (`pancarkanPengajuanPersetujuan`), lalu memberi tahu staf bahwa geseran ke
 * Done-nya menjadi pengajuan, dan menyegarkan semua panel persetujuan (sidebar
 * detail, antrean) supaya log-nya langsung muncul.
 */

import { useEffect } from "react";
import { useSWRConfig } from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
// components
import { AWALAN_KUNCI_PERSETUJUAN } from "@/components/issues/approval-actions";
// lib
import { EVENT_PENGAJUAN_PERSETUJUAN } from "@/lib/pengajuan-persetujuan";

export function PendengarPengajuanPersetujuan() {
  const { t } = useTranslation();
  const { mutate } = useSWRConfig();

  useEffect(() => {
    const tangani = () => {
      setToast({
        type: TOAST_TYPE.INFO,
        title: t("issue.approval.toast.requested_title"),
        message: t("issue.approval.toast.requested_message"),
      });
      void mutate((key) => typeof key === "string" && key.startsWith(AWALAN_KUNCI_PERSETUJUAN));
    };
    window.addEventListener(EVENT_PENGAJUAN_PERSETUJUAN, tangani);
    return () => window.removeEventListener(EVENT_PENGAJUAN_PERSETUJUAN, tangani);
  }, [t, mutate]);

  return null;
}
