/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tombol segarkan di dalam aplikasi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { RefreshCw } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { IconButton } from "@plane/propel/icon-button";
import { segarkanSemua, useSedangMenyegarkan } from "@/lib/data-live";

/**
 * Menyegarkan ISI layar (daftar, detail, lencana, pemberitahuan) tanpa memuat
 * ulang halaman, jadi posisi gulir, panel yang terbuka, dan isian yang sedang
 * ditulis tidak hilang seperti pada F5. Ikon berputar selama penarikan jalan.
 */
export function TombolSegarkan() {
  const { t } = useTranslation();
  const sibuk = useSedangMenyegarkan();
  const label = sibuk ? t("segar_ui.busy") : t("segar_ui.tooltip");

  return (
    <IconButton
      variant="ghost"
      size="lg"
      icon={RefreshCw}
      iconClassName={sibuk ? "size-4 animate-spin motion-reduce:animate-none" : "size-4"}
      aria-label={label}
      aria-busy={sibuk}
      title={label}
      onClick={() => {
        if (!sibuk) void segarkanSemua();
      }}
    />
  );
}
