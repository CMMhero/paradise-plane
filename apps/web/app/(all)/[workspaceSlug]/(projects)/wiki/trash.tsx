/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tempat sampah Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { ArrowLeft, Undo2 } from "lucide-react";
import { Link, useParams } from "react-router";
import useSWR, { useSWRConfig } from "swr";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { renderFormattedDate } from "@plane/utils";
// components
import { PageHead } from "@/components/core/page-title";
// local imports
import { kunciPohonWiki, labelTipe, layananWiki, ukuranTerbaca } from "./data";

const KELAS = {
  baris: "flex items-center justify-between gap-3 border-t border-subtle px-3 py-2.5 first:border-t-0",
  daftar: "overflow-hidden rounded-card border border-subtle bg-surface-1",
};

/**
 * Tempat sampah Wiki. Admin melihat semua folder dan materi yang dihapus,
 * anggota lain hanya materi yang mereka unggah sendiri. Server yang menyaring.
 */
function WikiTrashPage() {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const { data, isLoading, error, mutate } = useSWR(
    slug ? `WIKI_TRASH_${slug}` : null,
    slug ? () => layananWiki.fetchTrash(slug) : null
  );
  const { mutate: segarkan } = useSWRConfig();
  const [sedangMemulihkan, setSedangMemulihkan] = useState<string | null>(null);

  const pulihkan = async (jenis: "folder" | "materi", id: string, nama: string) => {
    if (sedangMemulihkan) return;
    setSedangMemulihkan(id);
    try {
      if (jenis === "folder") {
        await layananWiki.restoreFolder(slug, id);
        // Folder selalu diarsipkan sebelum dihapus. Tanpa langkah ini ia pulih
        // tetapi tetap tersembunyi. Gagal di sini (mis. induknya masih terarsip) bukan galat pemulihan.
        await layananWiki.unarchiveFolder(slug, id).catch(() => undefined);
      } else {
        await layananWiki.restoreMaterial(slug, id);
      }
      await Promise.all([mutate(), segarkan(kunciPohonWiki(slug))]);
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("wiki_ui.trash.restored_title"), message: nama });
    } catch (e) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("wiki_ui.trash.restore_failed"),
        message: (e as { error?: string })?.error || t("wiki_ui.common.try_again"),
      });
    } finally {
      setSedangMemulihkan(null);
    }
  };

  const folder = data?.folders ?? [];
  const materi = data?.materials ?? [];
  const kosong = !isLoading && !error && folder.length === 0 && materi.length === 0;

  return (
    <>
      <PageHead title={t("wiki_ui.trash.title")} />
      <div className="flex h-full w-full flex-col overflow-y-auto">
        <div className="border-b border-subtle bg-surface-1 px-page-x py-8">
          <Link
            to={`/${slug}/wiki`}
            className="inline-flex items-center gap-1.5 text-12 text-tertiary transition-colors hover:text-secondary"
          >
            <ArrowLeft className="size-3.5" />
            {t("wiki_ui.common.back_to_home")}
          </Link>
          <h1 className="mt-3 text-24 font-semibold tracking-tight text-primary">{t("wiki_ui.trash.title")}</h1>
          <p className="mt-1 max-w-2xl text-13 text-tertiary">{t("wiki_ui.trash.subtitle")}</p>
        </div>

        <div className="flex-1 space-y-8 px-page-x py-6">
          {error && (
            <p className="text-13 text-tertiary">
              {(error as { error?: string })?.error || t("wiki_ui.common.load_failed_message")}
            </p>
          )}
          {kosong && (
            <div className="rounded-card border border-dashed border-subtle px-6 py-14 text-center">
              <p className="text-14 font-medium text-secondary">{t("wiki_ui.trash.empty_title")}</p>
            </div>
          )}

          {folder.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-14 font-semibold text-primary">{t("wiki_ui.trash.folders")}</h2>
              <div className={KELAS.daftar}>
                {folder.map((f) => (
                  <div key={f.id} className={KELAS.baris}>
                    <div className="min-w-0">
                      <p className="truncate text-13 font-medium text-primary">{f.nama}</p>
                      <p className="text-12 text-tertiary">
                        {t("wiki_ui.trash.deleted_on", { date: renderFormattedDate(f.deleted_at) })}
                      </p>
                    </div>
                    <Button
                      variant="secondary"
                      size="sm"
                      loading={sedangMemulihkan === f.id}
                      onClick={() => void pulihkan("folder", f.id, f.nama)}
                    >
                      <Undo2 className="size-3.5" />
                      {t("wiki_ui.trash.restore")}
                    </Button>
                  </div>
                ))}
              </div>
            </section>
          )}

          {materi.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-14 font-semibold text-primary">{t("wiki_ui.trash.materials")}</h2>
              <div className={KELAS.daftar}>
                {materi.map((m) => (
                  <div key={m.id} className={KELAS.baris}>
                    <div className="min-w-0">
                      <p className="truncate text-13 font-medium text-primary">{m.judul}</p>
                      <p className="text-12 text-tertiary">
                        {[
                          labelTipe(m.type, t),
                          ukuranTerbaca(m.size),
                          t("wiki_ui.trash.deleted_on", { date: renderFormattedDate(m.deleted_at) }),
                        ].join(" · ")}
                      </p>
                    </div>
                    <Button
                      variant="secondary"
                      size="sm"
                      loading={sedangMemulihkan === m.id}
                      onClick={() => void pulihkan("materi", m.id, m.judul)}
                    >
                      <Undo2 className="size-3.5" />
                      {t("wiki_ui.trash.restore")}
                    </Button>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </>
  );
}

export default observer(WikiTrashPage);
