/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: beranda Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo, useState } from "react";
import { observer } from "mobx-react";
import { Plus } from "lucide-react";
import { useParams } from "react-router";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
// components
import { PageHead } from "@/components/core/page-title";
import { GridKartu, KartuFolder, KartuKerangka } from "@/components/wiki/kartu";
// services
import type { TWikiFolder } from "@/services/wiki.service";
// local imports
import { AksiFolder } from "./aksi-folder";
import { anakDari, folderTerlihat, jumlahHalamanDalam, jumlahMateriDalam, layananWiki, usePohonWiki } from "./data";
import { PencarianWiki } from "./pencarian";

/**
 * Beranda Wiki: folder divisi sebagai tampilan utama, lalu folder Umum dan
 * folder tingkat atas lainnya.
 *
 * Pohonnya datang dari satu panggilan `GET wiki/`; izin (`can_manage`) dibaca
 * apa adanya dari server.
 */
function WikiBerandaPage() {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const { folder, adalahAdmin, sedangMemuat, galat, muatUlang } = usePohonWiki(slug);
  const [mencari, setMencari] = useState(false);
  const [sedangMembuat, setSedangMembuat] = useState(false);

  const terlihat = useMemo(() => folderTerlihat(folder), [folder]);
  const tingkatAtas = anakDari(terlihat, null);
  const divisi = tingkatAtas.filter((f) => f.divisi_id);
  const lainnya = tingkatAtas.filter((f) => !f.divisi_id);

  const buatFolder = async () => {
    if (sedangMembuat) return;
    setSedangMembuat(true);
    try {
      await layananWiki.createFolder(slug, { nama: t("wiki_ui.home.new_folder_name") });
      await muatUlang();
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("wiki_ui.home.folder_created_title") });
    } catch (error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("wiki_ui.common.failed"),
        message: (error as { error?: string })?.error || t("wiki_ui.home.create_folder_failed"),
      });
    } finally {
      setSedangMembuat(false);
    }
  };

  const kartu = (f: TWikiFolder) => (
    <KartuFolder
      key={f.id}
      to={`/${slug}/wiki/${f.id}`}
      judul={f.nama}
      logoProps={f.logo_props ?? undefined}
      terbuka={f.umum}
      aksi={<AksiFolder workspaceSlug={slug} folder={f} onBerubah={muatUlang} />}
      keterangan={f.keterangan || (f.umum ? t("wiki_ui.home.open_to_all") : undefined)}
      jumlahAnak={jumlahMateriDalam(terlihat, f.id)}
      satuanAnak={t("wiki_ui.common.material_unit")}
      // Divisi: halaman semua departemennya, aturan yang sama dengan angka materi (KEP-97).
      halaman={
        f.divisi_id || f.departemen_id
          ? { jumlah: jumlahHalamanDalam(terlihat, f.id), satuan: t("wiki_ui.common.page_unit") }
          : undefined
      }
    />
  );

  if (galat && !folder)
    return (
      <div className="flex h-full w-full items-center justify-center p-8 text-center">
        <div className="max-w-md">
          <h2 className="text-14 font-semibold text-primary">{t("wiki_ui.common.load_failed_title")}</h2>
          <p className="mt-1 text-13 text-tertiary">{galat.error || t("wiki_ui.common.load_failed_message")}</p>
        </div>
      </div>
    );

  return (
    <>
      <PageHead title={t("wiki_ui.home.title")} />
      <div className="flex h-full w-full flex-col overflow-y-auto">
        <div className="border-b border-subtle bg-surface-1 px-page-x py-8">
          <h1 className="text-24 font-semibold tracking-tight text-primary">{t("wiki_ui.home.title")}</h1>
          <p className="mt-1 max-w-2xl text-13 text-tertiary">{t("wiki_ui.home.description")}</p>
          <div className="mt-5">
            <PencarianWiki workspaceSlug={slug} onAktif={setMencari} />
          </div>
        </div>

        {!mencari && (
          <div className="flex-1 space-y-8 px-page-x py-6">
            <section>
              <div className="mb-4 flex items-center justify-between gap-3">
                <div className="flex items-baseline gap-2">
                  <h2 className="text-14 font-semibold text-primary">{t("wiki_ui.home.pick_division")}</h2>
                  <span className="rounded-control bg-layer-3 px-2 py-0.5 text-11 text-tertiary">
                    {t("wiki_ui.home.division_count", { count: divisi.length })}
                  </span>
                </div>
                {adalahAdmin && (
                  <Button variant="primary" size="sm" onClick={buatFolder} loading={sedangMembuat}>
                    <Plus className="size-3.5" />
                    {t("wiki_ui.home.new_folder")}
                  </Button>
                )}
              </div>

              {sedangMemuat && !folder ? (
                <GridKartu>
                  {[0, 1, 2, 3].map((i) => (
                    <KartuKerangka key={i} />
                  ))}
                </GridKartu>
              ) : divisi.length === 0 ? (
                <div className="rounded-card border border-dashed border-subtle px-6 py-14 text-center">
                  <p className="text-14 font-medium text-secondary">{t("wiki_ui.home.empty_title")}</p>
                  <p className="mt-1 text-12 text-tertiary">{t("wiki_ui.home.empty_message")}</p>
                </div>
              ) : (
                <GridKartu>{divisi.map(kartu)}</GridKartu>
              )}
            </section>

            {lainnya.length > 0 && (
              <section>
                <h2 className="mb-4 text-14 font-semibold text-primary">{t("wiki_ui.home.other_folders")}</h2>
                <GridKartu>{lainnya.map(kartu)}</GridKartu>
              </section>
            )}
          </div>
        )}
      </div>
    </>
  );
}

export default observer(WikiBerandaPage);
