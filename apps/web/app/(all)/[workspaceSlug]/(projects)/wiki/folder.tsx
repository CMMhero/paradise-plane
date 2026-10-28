/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: isi folder Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useRef, useState } from "react";
import { observer } from "mobx-react";
import { ArrowLeft, Lock, Pencil, Plus, Settings2, Trash2, Upload } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { getPageName, renderFormattedDate } from "@plane/utils";
// components
import { PageHead } from "@/components/core/page-title";
import { GridKartu, KartuFolder, KartuMateri } from "@/components/wiki/kartu";
// services
import { ProjectPageService } from "@/services/page";
import { WikiMaterialService } from "@/services/wiki_material.service";
// local imports
import { GantiNamaMateri } from "./ganti-nama";
import { KelolaFolder } from "./kelola";
// local imports
import {
  anakDari,
  divisiDari,
  halamanDenganId,
  halamanTerlihat,
  izinFolderDari,
  jumlahMateriDalam,
  labelTipe,
  ukuranTerbaca,
  useIzinWiki,
  useJumlahMateriWiki,
  usePohonWiki,
  useProjectWiki,
} from "./data";

const layananMateri = new WikiMaterialService();
const layananHalaman = new ProjectPageService();

/**
 * Isi sebuah folder Wiki: Topik di dalamnya, lalu Materi di dalamnya.
 *
 * Satu halaman dipakai untuk Divisi maupun Topik, dan itu disengaja. Yang
 * membedakan keduanya cuma apa yang kebetulan ada di dalamnya, bukan aturan
 * kaku soal kedalaman. Divisi yang cukup menaruh berkasnya langsung tidak
 * dipaksa membuat Topik kosong hanya demi bentuk.
 */
function WikiFolderPage() {
  const { t } = useTranslation();
  const { workspaceSlug, folderId } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const idFolder = folderId?.toString() ?? "";
  const { projectId } = useProjectWiki();
  const { halaman, sedangMemuat, muatUlang } = usePohonWiki(slug, projectId);
  const { izin, muatUlangIzin } = useIzinWiki(slug, projectId);
  const { jumlahMateri, muatUlangJumlah } = useJumlahMateriWiki(slug, projectId);
  const berkasRef = useRef<HTMLInputElement>(null);
  const [sedangUnggah, setSedangUnggah] = useState(false);
  const [sedangMembuatSub, setSedangMembuatSub] = useState(false);
  const [kelolaTerbuka, setKelolaTerbuka] = useState(false);
  const [materiDiganti, setMateriDiganti] = useState<{ id: string; title: string; name: string } | null>(null);
  const navigate = useNavigate();

  const terlihat = halamanTerlihat(halaman);
  const folder = halamanDenganId(terlihat, idFolder);
  const divisi = divisiDari(terlihat, folder?.id);
  const izinDivisi = izinFolderDari(izin, divisi?.id);

  const kunciMateri = projectId && idFolder ? `WIKI_MATERIALS_${idFolder}` : null;
  const { data: daftarMateri, mutate: muatUlangMateri } = useSWR(
    kunciMateri,
    projectId ? () => layananMateri.fetchByTopic(slug, projectId, idFolder) : null,
    { revalidateOnFocus: false }
  );
  const materi = daftarMateri?.materials ?? [];
  const bolehUnggah = !!daftarMateri?.can_upload;
  // Boleh mengurus folder ini. Jawabannya datang dari server, bukan dihitung
  // ulang di sini, supaya aturan izinnya tidak pernah bercabang dua.
  const bolehKelola = !!folder?.id && !!izin?.manageable_page_ids?.includes(folder.id);

  const unggah = async (files: FileList | null) => {
    if (!projectId || !files?.length) return;
    setSedangUnggah(true);
    let berhasil = 0;
    // Sengaja berurutan, bukan Promise.all. Satu berkas di sini boleh 250 MB;
    // mengunggah sepuluh sekaligus akan menghabiskan seluruh jalur WiFi kantor
    // dan membuat semuanya gagal berbarengan alih-alih selesai satu per satu.
    for (const file of Array.from(files)) {
      try {
        // oxlint-disable-next-line no-await-in-loop
        await layananMateri.upload(slug, projectId, idFolder, file);
        berhasil += 1;
      } catch (error) {
        // Satu berkas gagal tidak boleh membatalkan sisanya, dan orangnya harus
        // tahu berkas MANA yang gagal, bukan cuma "ada yang gagal".
        setToast({
          type: TOAST_TYPE.ERROR,
          title: t("wiki_ui.folder.upload_failed_title", { name: file.name }),
          message: (error as { error?: string })?.error || t("wiki_ui.folder.upload_failed_message"),
        });
      }
    }
    setSedangUnggah(false);
    if (berhasil > 0) {
      await Promise.all([muatUlangMateri(), muatUlangJumlah()]);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("wiki_ui.folder.uploaded_title"),
        message: t("wiki_ui.folder.uploaded_message", { count: berhasil, folder: getPageName(folder?.name) }),
      });
    }
    if (berkasRef.current) berkasRef.current.value = "";
  };

  const buatSubtopik = async () => {
    if (!projectId || !idFolder || sedangMembuatSub) return;
    setSedangMembuatSub(true);
    try {
      await layananHalaman.create(slug, projectId, { name: t("wiki_ui.folder.new_topic_name"), parent: idFolder });
      // Izin ikut dimuat ulang: folder baru belum ada di manageable_page_ids
      // cache, jadi tanpa ini tombol Kelola/unggah baru muncul setelah refresh.
      await Promise.all([muatUlang(), muatUlangIzin()]);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("wiki_ui.folder.subtopic_created_title"),
        message: t("wiki_ui.folder.subtopic_created_message"),
      });
    } catch (error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("wiki_ui.common.failed"),
        message: (error as { error?: string })?.error || t("wiki_ui.folder.subtopic_failed_message"),
      });
    } finally {
      setSedangMembuatSub(false);
    }
  };
  const hapus = async (assetId: string, judul: string) => {
    if (!projectId) return;
    try {
      await layananMateri.remove(slug, projectId, assetId);
      await Promise.all([muatUlangMateri(), muatUlangJumlah()]);
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("wiki_ui.folder.deleted_title"), message: judul });
    } catch (error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("wiki_ui.folder.delete_failed_title"),
        message: (error as { error?: string })?.error || t("wiki_ui.common.try_again"),
      });
    }
  };

  if (!sedangMemuat && !folder)
    return (
      <div className="flex h-full w-full items-center justify-center p-8 text-center">
        <div className="max-w-md">
          <h2 className="text-15 font-semibold text-primary">{t("wiki_ui.folder.gone_title")}</h2>
          <p className="mt-1 text-13 text-tertiary">{t("wiki_ui.folder.gone_description")}</p>
          <Link
            to={`/${slug}/wiki`}
            className="mt-4 inline-block rounded-md border border-subtle px-3 py-1.5 text-12 font-medium text-secondary transition-colors hover:border-strong hover:text-primary"
          >
            {t("wiki_ui.common.back_to_home")}
          </Link>
        </div>
      </div>
    );

  const judul = getPageName(folder?.name);

  return (
    <>
      <PageHead title={t("wiki_ui.folder.page_title", { name: judul })} />
      <div className="flex h-full w-full flex-col overflow-y-auto">
        <div className="border-b border-subtle bg-surface-1 px-page-x py-8">
          <Link
            to={folder?.parent ? `/${slug}/wiki/${folder.parent}` : `/${slug}/wiki`}
            className="inline-flex items-center gap-1.5 text-12 text-tertiary transition-colors hover:text-secondary"
          >
            <ArrowLeft className="size-3.5" />
            {folder?.parent
              ? t("wiki_ui.folder.back_to_parent", { name: getPageName(divisi?.name) })
              : t("wiki_ui.common.back_to_home")}
          </Link>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-semibold tracking-tight text-primary">{judul}</h1>
            {bolehKelola && (
              <Button variant="secondary" size="sm" onClick={() => setKelolaTerbuka(true)}>
                <Settings2 className="size-3.5" />
                {t("wiki_ui.folder.manage")}
              </Button>
            )}
            {bolehKelola && (
              <Button variant="primary" size="sm" onClick={() => void buatSubtopik()} loading={sedangMembuatSub}>
                <Plus className="size-3.5" />
                {t("wiki_ui.folder.subtopic")}
              </Button>
            )}
          </div>
          <p className="mt-1 text-13 text-tertiary">
            {izinDivisi?.is_general
              ? t("wiki_ui.folder.access_general")
              : izinDivisi?.divisions.length
                ? t("wiki_ui.folder.managed_by", { names: izinDivisi.divisions.map((d) => d.name).join(", ") })
                : t("wiki_ui.folder.no_managing_division")}
          </p>
        </div>

        <div className="flex-1 space-y-8 px-page-x py-6">
          {anakDari(terlihat, idFolder).length > 0 && (
            <section>
              <div className="mb-4 flex items-baseline gap-2">
                <h2 className="text-15 font-semibold text-primary">{t("wiki_ui.folder.subtopic")}</h2>
                <span className="rounded-full bg-layer-3 px-2 py-0.5 text-11 text-tertiary">
                  {t("wiki_ui.folder.topic_count", { count: anakDari(terlihat, idFolder).length })}
                </span>
              </div>
              <GridKartu>
                {anakDari(terlihat, idFolder).map((s) => (
                  <KartuFolder
                    key={s.id}
                    to={`/${slug}/wiki/${s.id}`}
                    judul={getPageName(s.name)}
                    logoProps={s.logo_props}
                    jumlahAnak={jumlahMateriDalam(terlihat, jumlahMateri, s.id)}
                    satuanAnak={t("wiki_ui.common.material_unit")}
                  />
                ))}
              </GridKartu>
            </section>
          )}
          <section>
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="flex items-baseline gap-2">
                <h2 className="text-15 font-semibold text-primary">{t("wiki_ui.folder.material_list")}</h2>
                <span className="rounded-full bg-layer-3 px-2 py-0.5 text-11 text-tertiary">
                  {t("wiki_ui.folder.material_count", { count: materi.length })}
                </span>
              </div>
              {bolehUnggah ? (
                <>
                  <input
                    ref={berkasRef}
                    type="file"
                    multiple
                    className="hidden"
                    onChange={(e) => void unggah(e.target.files)}
                  />
                  <Button variant="primary" size="sm" onClick={() => berkasRef.current?.click()} loading={sedangUnggah}>
                    <Upload className="size-3.5" />
                    {t("wiki_ui.folder.upload_material")}
                  </Button>
                </>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-11 text-tertiary">
                  <Lock className="size-3" />
                  {t("wiki_ui.folder.only_managers_can_add")}
                </span>
              )}
            </div>

            {materi.length === 0 ? (
              <div className="rounded-lg border border-dashed border-subtle px-6 py-14 text-center">
                <p className="text-14 font-medium text-secondary">{t("wiki_ui.folder.empty_title")}</p>
                <p className="mt-1 text-12 text-tertiary">
                  {bolehUnggah ? t("wiki_ui.folder.empty_can_upload") : t("wiki_ui.folder.empty_cannot_upload")}
                </p>
              </div>
            ) : (
              <GridKartu>
                {materi.map((m) => (
                  <KartuMateri
                    key={m.id}
                    to={`/${slug}/wiki/materi/${m.id}`}
                    judul={m.title}
                    keterangan={[m.uploaded_by?.display_name, renderFormattedDate(m.created_at)]
                      .filter(Boolean)
                      .join(" · ")}
                    tipe={m.type}
                    label={labelTipe(m.type, t)}
                    ukuran={ukuranTerbaca(m.size)}
                    aksi={
                      m.can_manage ? (
                        <>
                          <button
                            type="button"
                            title={t("wiki_ui.folder.rename")}
                            aria-label={t("wiki_ui.folder.rename_named", { title: m.title })}
                            onClick={() => setMateriDiganti({ id: m.id, title: m.title, name: m.name })}
                            className="grid size-7 place-items-center rounded-md bg-black/25 text-white opacity-0 backdrop-blur-[1px] transition-opacity group-hover:opacity-100 hover:bg-black/40 focus-visible:opacity-100"
                          >
                            <Pencil className="size-3.5" />
                          </button>
                          <button
                            type="button"
                            title={t("wiki_ui.folder.delete")}
                            aria-label={t("wiki_ui.folder.delete_named", { title: m.title })}
                            onClick={() => void hapus(m.id, m.title)}
                            className="grid size-7 place-items-center rounded-md bg-black/25 text-white opacity-0 backdrop-blur-[1px] transition-opacity group-hover:opacity-100 hover:bg-black/40 focus-visible:opacity-100"
                          >
                            <Trash2 className="size-3.5" />
                          </button>
                        </>
                      ) : undefined
                    }
                  />
                ))}
              </GridKartu>
            )}
          </section>
        </div>
      </div>

      {materiDiganti && projectId && (
        <GantiNamaMateri
          workspaceSlug={slug}
          projectId={projectId}
          materiId={materiDiganti.id}
          judulSekarang={materiDiganti.title}
          namaBerkas={materiDiganti.name}
          isOpen
          onClose={() => setMateriDiganti(null)}
          onSelesai={() => muatUlangMateri()}
        />
      )}

      {folder && kelolaTerbuka && (
        <KelolaFolder
          workspaceSlug={slug}
          projectId={projectId ?? ""}
          folder={folder}
          izin={izin}
          isOpen={kelolaTerbuka}
          onClose={() => setKelolaTerbuka(false)}
          onBerubah={() => Promise.all([muatUlang(), muatUlangIzin()])}
          onTerhapus={() => {
            setKelolaTerbuka(false);
            navigate(folder.parent ? `/${slug}/wiki/${folder.parent}` : `/${slug}/wiki`);
          }}
        />
      )}
    </>
  );
}

export default observer(WikiFolderPage);
