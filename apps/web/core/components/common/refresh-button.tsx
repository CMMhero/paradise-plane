/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tombol segarkan di header aplikasi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useState } from "react";
import { RefreshCw } from "lucide-react";
import { useSWRConfig } from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { IconButton } from "@plane/propel/icon-button";
import { Tooltip } from "@plane/propel/tooltip";
// hooks
import { usePlatformOS } from "@/hooks/use-platform-os";

// Putaran ikon paling singkat. Data lokal kembali dalam hitungan milidetik, dan
// tombol yang tak terlihat bereaksi terasa seperti tak bekerja.
const MIN_PUTAR_MS = 600;

/**
 * Menyegarkan semua data SWR yang sedang dipakai layar ini (daftar work item,
 * antrean persetujuan, lencana, dan sebagainya) tanpa memuat ulang halaman.
 * Kunci yang tak sedang dipasang diabaikan SWR, jadi biayanya hanya yang tampak.
 */
export function RefreshButton() {
  const { t } = useTranslation();
  const { mutate } = useSWRConfig();
  const { isMobile } = usePlatformOS();
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = useCallback(async () => {
    if (isRefreshing) return;
    setIsRefreshing(true);
    const minimum = new Promise((resolve) => setTimeout(resolve, MIN_PUTAR_MS));
    try {
      // Tanpa nilai kedua: revalidasi saja, jangan kosongkan cache dulu supaya layar tidak berkedip.
      await Promise.all([mutate(() => true), minimum]);
    } catch (error) {
      console.error("Gagal menyegarkan data", error);
    } finally {
      setIsRefreshing(false);
    }
  }, [isRefreshing, mutate]);

  const label = isRefreshing ? t("refreshing") : t("refresh");

  return (
    <Tooltip tooltipContent={label} isMobile={isMobile}>
      <IconButton
        size="base"
        variant="ghost"
        icon={RefreshCw}
        iconClassName={isRefreshing ? "animate-spin" : ""}
        aria-label={label}
        aria-busy={isRefreshing}
        onClick={() => void handleRefresh()}
        className="shrink-0"
      />
    </Tooltip>
  );
}
