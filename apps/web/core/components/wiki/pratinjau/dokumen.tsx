/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: pratinjau sederhana dokumen Word di Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/* oxlint-disable react/no-array-index-key -- blok dan sel hasil baca server tidak punya id; daftarnya statis dan tidak pernah disusun ulang */

import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
// services
import type { TWikiBlock, TWikiRun } from "@/services/wiki.service";
// local imports
import { CatatanPratinjau, KotakPratinjau } from "./teks";

// Server sudah menyaring skema tautan; diperiksa lagi di sini karena ini
// satu-satunya tempat sebuah alamat dari berkas unggahan menjadi `href`.
const TAUTAN_AMAN = /^(https?:|mailto:)/i;

const KELAS_JUDUL: Record<number, string> = {
  1: "mt-6 mb-2 text-20 font-semibold text-primary",
  2: "mt-5 mb-2 text-16 font-semibold text-primary",
  3: "mt-4 mb-1.5 text-14 font-semibold text-primary",
};
const TAG_JUDUL = ["h1", "h2", "h3", "h4", "h5", "h6"] as const;
const KELAS_JUDUL_KECIL = "mt-3 mb-1 text-13 font-semibold text-primary";

function Runs({ runs }: { runs: TWikiRun[] }) {
  return (
    <>
      {runs.map((run, i) => {
        const kelas = cn(
          run.bold && "font-semibold",
          run.italic && "italic",
          run.underline && "underline",
          run.strike && "line-through"
        );
        if (run.href && TAUTAN_AMAN.test(run.href))
          return (
            <a
              key={i}
              href={run.href}
              target="_blank"
              rel="noopener noreferrer"
              className={cn("text-accent-primary underline", kelas)}
            >
              {run.text}
            </a>
          );
        return (
          <span key={i} className={cn("whitespace-pre-wrap", kelas)}>
            {run.text}
          </span>
        );
      })}
    </>
  );
}

function Blok({ blok }: { blok: TWikiBlock }) {
  switch (blok.type) {
    case "heading": {
      const kelas = KELAS_JUDUL[blok.level] ?? KELAS_JUDUL_KECIL;
      const Judul = TAG_JUDUL[Math.min(Math.max(blok.level, 1), 6) - 1] ?? "h6";
      return (
        <Judul className={kelas}>
          <Runs runs={blok.runs} />
        </Judul>
      );
    }
    case "list_item":
      return (
        <div className="my-0.5 flex gap-2" style={{ paddingLeft: `${blok.level * 1.25}rem` }}>
          <span aria-hidden className="text-tertiary">
            •
          </span>
          <p className="min-w-0 flex-1">
            <Runs runs={blok.runs} />
          </p>
        </div>
      );
    case "table":
      return (
        <div className="my-3 overflow-auto">
          <table className="border-collapse text-12">
            <tbody>
              {blok.rows.map((baris, r) => (
                <tr key={r}>
                  {baris.map((sel, c) => (
                    <td
                      key={c}
                      className="border border-subtle px-2.5 py-1 align-top break-words whitespace-pre-wrap text-secondary"
                    >
                      {sel}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    default:
      return (
        <p className="my-2">
          <Runs runs={blok.runs} />
        </p>
      );
  }
}

/**
 * Tampilan sederhana berkas Word yang dibaca server. Dipakai saat konversi ke
 * PDF tidak tersedia; tata letak dan gambar tidak ikut, dan itu dikatakan terus
 * terang di bawahnya.
 */
export function PratinjauDokumen({
  blocks,
  truncated,
  className,
}: {
  blocks: TWikiBlock[];
  truncated?: boolean;
  className?: string;
}) {
  const { t } = useTranslation();
  return (
    <>
      <KotakPratinjau className={className}>
        {blocks.length > 0 ? (
          <div className="mx-auto max-w-3xl text-13 leading-relaxed text-secondary">
            {blocks.map((b, i) => (
              <Blok key={i} blok={b} />
            ))}
          </div>
        ) : (
          <p className="text-13 text-tertiary">{t("wiki_ui.viewer.empty_document")}</p>
        )}
      </KotakPratinjau>
      <CatatanPratinjau>
        {t("wiki_ui.viewer.simple_view")}
        {truncated && ` ${t("wiki_ui.viewer.truncated_text")}`}
      </CatatanPratinjau>
    </>
  );
}
