/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pratinjau CSV dan Excel di Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/* oxlint-disable react/no-array-index-key -- baris dan sel hasil baca server tidak punya id; daftarnya statis dan tidak pernah disusun ulang */

import { useState } from "react";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
// services
import type { TWikiSheet } from "@/services/wiki.service";
// local imports
import { CatatanPratinjau } from "./teks";

/**
 * Tabel baca-saja. Sel selalu teks dari server, jadi tidak ada yang dirender
 * sebagai HTML. Baris pertama diperlakukan sebagai judul kolom dan menempel di
 * atas saat digulir.
 */
export function PratinjauTabel({
  sheets,
  truncated,
  className,
}: {
  sheets: TWikiSheet[];
  /** Ada lembar yang tidak ikut karena batas jumlah lembar. */
  truncated?: boolean;
  className?: string;
}) {
  const { t } = useTranslation();
  const [aktif, setAktif] = useState(0);
  const lembar = sheets[Math.min(aktif, sheets.length - 1)];
  if (!lembar) return null;
  const [judul, ...isi] = lembar.rows;
  const terpotong = truncated || sheets.some((s) => s.truncated);

  return (
    <>
      {sheets.length > 1 && (
        <div role="tablist" className="mb-2 flex flex-wrap gap-1">
          {sheets.map((s, i) => (
            <button
              key={`${s.name}-${i}`}
              type="button"
              role="tab"
              aria-selected={i === aktif}
              onClick={() => setAktif(i)}
              className={cn(
                "max-w-48 truncate rounded-control px-3 py-1 text-12 transition-colors",
                i === aktif
                  ? "bg-layer-3 font-medium text-primary"
                  : "text-tertiary hover:bg-layer-1 hover:text-secondary"
              )}
            >
              {s.name}
            </button>
          ))}
        </div>
      )}

      <div className={cn("overflow-auto rounded-card border border-subtle bg-layer-1", className)}>
        {judul ? (
          <table className="min-w-full border-separate border-spacing-0 text-12">
            <thead>
              <tr>
                <th className="font-normal sticky top-0 left-0 z-20 w-10 border-r border-b border-subtle bg-layer-3 px-2 py-1.5 text-right text-tertiary tabular-nums">
                  1
                </th>
                {judul.map((sel, i) => (
                  <th
                    key={i}
                    className="sticky top-0 z-10 max-w-sm border-r border-b border-subtle bg-layer-3 px-3 py-1.5 text-left font-semibold whitespace-pre-wrap text-primary"
                  >
                    {sel}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isi.map((baris, r) => (
                <tr key={r} className="hover:bg-layer-2">
                  <td className="sticky left-0 border-r border-b border-subtle bg-layer-3 px-2 py-1 text-right text-tertiary tabular-nums">
                    {r + 2}
                  </td>
                  {judul.map((_, c) => (
                    <td
                      key={c}
                      className="max-w-sm border-r border-b border-subtle px-3 py-1 align-top break-words whitespace-pre-wrap text-secondary"
                    >
                      {baris[c] ?? ""}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="p-4 text-13 text-tertiary">{t("wiki_ui.viewer.empty_sheet")}</p>
        )}
      </div>
      {terpotong && <CatatanPratinjau>{t("wiki_ui.viewer.truncated_table")}</CatatanPratinjau>}
    </>
  );
}
