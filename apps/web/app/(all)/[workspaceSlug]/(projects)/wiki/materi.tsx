/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: penampil Materi Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { ArrowLeft, Download, Pencil } from "lucide-react";
import { Link, useParams } from "react-router";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import { renderFormattedDate } from "@plane/utils";
// components
import { PageHead } from "@/components/core/page-title";
// services
import { WikiMaterialService } from "@/services/wiki_material.service";
// local imports
import { labelTipe, ukuranTerbaca, useProjectWiki } from "./data";
import { GantiNamaMateri } from "./ganti-nama";
import { PenampilMateri } from "./penampil";

const layanan = new WikiMaterialService();

function WikiMateriPage() {
  const { t } = useTranslation();
  const { workspaceSlug, assetId } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const idMateri = assetId?.toString() ?? "";
  const { projectId } = useProjectWiki();
  const [gantiNama, setGantiNama] = useState(false);

  const { data, isLoading, error, mutate } = useSWR(
    projectId && idMateri ? `WIKI_MATERIAL_PREVIEW_${idMateri}` : null,
    projectId ? () => layanan.preview(slug, projectId, idMateri) : null,
    { revalidateOnFocus: false }
  );

  if (error)
    return (
      <div className="flex h-full w-full items-center justify-center p-8 text-center">
        <div className="max-w-md">
          <h2 className="text-15 font-semibold text-primary">{t("wiki_ui.material.cannot_open_title")}</h2>
          <p className="mt-1 text-13 text-tertiary">
            {(error as { error?: string })?.error || t("wiki_ui.material.cannot_open_message")}
          </p>
          <Link
            to={`/${slug}/wiki`}
            className="mt-4 inline-block rounded-md border border-subtle px-3 py-1.5 text-12 font-medium text-secondary transition-colors hover:border-strong hover:text-primary"
          >
            {t("wiki_ui.material.back_to_wiki")}
          </Link>
        </div>
      </div>
    );

  if (isLoading || !data)
    return (
      <div className="flex h-full w-full flex-col gap-4 px-page-x py-8">
        <div className="h-6 w-1/3 animate-pulse rounded bg-layer-3" />
        <div className="h-[60vh] w-full animate-pulse rounded-lg bg-layer-3" />
        <p className="text-center text-12 text-tertiary">{t("wiki_ui.material.preparing")}</p>
      </div>
    );

  return (
    <>
      <PageHead title={t("wiki_ui.folder.page_title", { name: data.title })} />
      <div className="flex h-full w-full flex-col overflow-y-auto">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-subtle bg-surface-1 px-page-x py-6">
          <div className="min-w-0">
            <Link
              to={data.topic_id ? `/${slug}/wiki/${data.topic_id}` : `/${slug}/wiki`}
              className="inline-flex items-center gap-1.5 text-12 text-tertiary transition-colors hover:text-secondary"
            >
              <ArrowLeft className="size-3.5" />
              {t("wiki_ui.material.back_to_division")}
            </Link>
            <h1 className="text-2xl mt-2 truncate font-semibold tracking-tight text-primary">{data.title}</h1>
            <p className="mt-1 text-12 text-tertiary">
              {[
                labelTipe(data.type, t),
                ukuranTerbaca(data.size),
                data.uploaded_by?.display_name,
                renderFormattedDate(data.created_at),
              ]
                .filter(Boolean)
                .join(" · ")}
              {data.converted && ` · ${t("wiki_ui.material.shown_as_pdf")}`}
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {data.can_manage && (
              <button
                type="button"
                onClick={() => setGantiNama(true)}
                className="inline-flex items-center gap-1.5 rounded-md border border-subtle px-3 py-1.5 text-12 font-medium text-secondary transition-colors hover:border-strong hover:text-primary"
              >
                <Pencil className="size-3.5" />
                {t("wiki_ui.folder.rename")}
              </button>
            )}
            <a
              href={data.download_url}
              className="inline-flex items-center gap-1.5 rounded-md border border-subtle px-3 py-1.5 text-12 font-medium text-secondary transition-colors hover:border-strong hover:text-primary"
            >
              <Download className="size-3.5" />
              {t("wiki_ui.material.download_original")}
            </a>
          </div>
        </div>

        <div className="flex-1 px-page-x py-6">
          {data.url ? (
            <PenampilMateri pratinjau={data} />
          ) : (
            <div className="rounded-lg border border-dashed border-subtle px-6 py-16 text-center">
              <p className="text-14 font-medium text-secondary">{t("wiki_ui.material.cannot_display_title")}</p>
              <p className="mx-auto mt-1 max-w-md text-12 text-tertiary">
                {data.reason
                  ? t("wiki_ui.material.cannot_display_with_reason", { reason: data.reason })
                  : t("wiki_ui.material.cannot_display_no_viewer")}
              </p>
            </div>
          )}
        </div>
      </div>

      {gantiNama && projectId && (
        <GantiNamaMateri
          workspaceSlug={slug}
          projectId={projectId}
          materiId={data.id}
          judulSekarang={data.title}
          namaBerkas={data.name}
          isOpen={gantiNama}
          onClose={() => setGantiNama(false)}
          onSelesai={() => mutate()}
        />
      )}
    </>
  );
}

export default observer(WikiMateriPage);
