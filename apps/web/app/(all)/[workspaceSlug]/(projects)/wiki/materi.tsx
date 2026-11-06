/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: penampil Materi Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Download, Pencil } from "lucide-react";
import { Link, useParams } from "react-router";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import { getButtonStyling } from "@plane/propel/button";
import { cn, renderFormattedDate } from "@plane/utils";
// components
import { PageHead } from "@/components/core/page-title";
// local imports
import { labelTipe, layananWiki, ukuranTerbaca } from "./data";
import { GantiNamaMateri } from "./ganti-nama";
import { PenampilMateri } from "./penampil";

function WikiMateriPage() {
  const { t } = useTranslation();
  const { workspaceSlug, assetId } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const idMateri = assetId?.toString() ?? "";
  const [gantiNama, setGantiNama] = useState(false);

  // Dua permintaan: detail (judul, izin, jejak) cepat, pratinjau bisa menunggu konversi.
  const {
    data: materi,
    error: galatMateri,
    mutate,
  } = useSWR(
    idMateri ? `WIKI_MATERIAL_${idMateri}` : null,
    idMateri ? () => layananWiki.fetchMaterial(slug, idMateri) : null
  );
  const { data: pratinjau, error: galatPratinjau } = useSWR(
    idMateri ? `WIKI_MATERIAL_PREVIEW_${idMateri}` : null,
    idMateri ? () => layananWiki.fetchPreview(slug, idMateri) : null,
    { revalidateOnFocus: false }
  );
  const error = galatMateri ?? galatPratinjau;

  if (error)
    return (
      <div className="flex h-full w-full items-center justify-center p-8 text-center">
        <div className="max-w-md">
          <h2 className="text-14 font-semibold text-primary">{t("wiki_ui.material.cannot_open_title")}</h2>
          <p className="mt-1 text-13 text-tertiary">
            {(error as { error?: string })?.error || t("wiki_ui.material.cannot_open_message")}
          </p>
          <Link to={`/${slug}/wiki`} className={cn(getButtonStyling("secondary", "lg"), "mt-4")}>
            {t("wiki_ui.material.back_to_wiki")}
          </Link>
        </div>
      </div>
    );

  if (!materi || !pratinjau)
    return (
      <div className="flex h-full w-full flex-col gap-4 px-page-x py-8">
        <div className="h-6 w-1/3 animate-pulse rounded-item bg-layer-3" />
        <div className="h-[60vh] w-full animate-pulse rounded-card bg-layer-3" />
        <p className="text-center text-12 text-tertiary">{t("wiki_ui.material.preparing")}</p>
      </div>
    );

  return (
    <>
      <PageHead title={t("wiki_ui.folder.page_title", { name: materi.judul })} />
      <div className="flex h-full w-full flex-col overflow-y-auto">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-subtle bg-surface-1 px-page-x py-6">
          <div className="min-w-0">
            {/* Jalur ke materi ini ada di breadcrumb kepala Wiki, jadi tidak ada tautan kembali lagi di sini. */}
            <h1 className="truncate text-20 font-semibold tracking-tight text-primary">{materi.judul}</h1>
            <p className="mt-1 text-12 text-tertiary">
              {[labelTipe(materi.type, t), ukuranTerbaca(materi.size), renderFormattedDate(materi.created_at)]
                .filter(Boolean)
                .join(" · ")}
              {pratinjau.converted && ` · ${t("wiki_ui.material.shown_as_pdf")}`}
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {materi.can_manage && (
              <button type="button" onClick={() => setGantiNama(true)} className={getButtonStyling("secondary", "lg")}>
                <Pencil className="size-3.5" />
                {t("wiki_ui.folder.rename")}
              </button>
            )}
            <a href={pratinjau.download_url ?? materi.url} className={getButtonStyling("secondary", "lg")}>
              <Download className="size-3.5" />
              {t("wiki_ui.material.download_original")}
            </a>
          </div>
        </div>

        <div className="flex-1 px-page-x py-6">
          {pratinjau.url ? (
            <PenampilMateri pratinjau={pratinjau} title={materi.judul} />
          ) : (
            <div className="rounded-card border border-dashed border-subtle px-6 py-16 text-center">
              <p className="text-14 font-medium text-secondary">{t("wiki_ui.material.cannot_display_title")}</p>
              <p className="mx-auto mt-1 max-w-md text-12 text-tertiary">
                {pratinjau.reason
                  ? t("wiki_ui.material.cannot_display_with_reason", { reason: pratinjau.reason })
                  : t("wiki_ui.material.cannot_display_no_viewer")}
              </p>
            </div>
          )}
        </div>
      </div>

      {gantiNama && (
        <GantiNamaMateri
          workspaceSlug={slug}
          materiId={materi.id}
          judulSekarang={materi.judul}
          namaBerkas={materi.name}
          isOpen={gantiNama}
          onClose={() => setGantiNama(false)}
          onSelesai={() => mutate()}
        />
      )}
    </>
  );
}

export default observer(WikiMateriPage);
