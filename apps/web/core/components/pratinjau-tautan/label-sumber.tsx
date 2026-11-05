/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: penanda asal link/lampiran (KEP-88)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";
import { Tooltip } from "@plane/propel/tooltip";

type Props = { sumber: string | undefined };

/**
 * Pengganti menu ubah/hapus pada link atau gambar yang diambil dari deskripsi
 * atau komentar. Menghapusnya dari daftar tidak akan menghapusnya dari teks,
 * jadi yang ditawarkan adalah keterangan asalnya, bukan tombol yang menipu.
 */
export function LabelSumberTeks({ sumber }: Props) {
  const { t } = useTranslation();
  const label = sumber === "comment" ? t("link_preview_ui.from_comment") : t("link_preview_ui.from_description");
  return (
    <Tooltip tooltipContent={t("link_preview_ui.edit_source_hint")}>
      <span className="shrink-0 rounded-sm bg-layer-1 px-1.5 py-0.5 text-11 text-tertiary">{label}</span>
    </Tooltip>
  );
}
