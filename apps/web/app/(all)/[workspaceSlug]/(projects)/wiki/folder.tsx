/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: isi folder Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { ArrowLeft, Plus, Settings2 } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router";
import { useSWRConfig } from "swr";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { getPageName } from "@plane/utils";
// components
import { PageHead } from "@/components/core/page-title";
import { GridKartu, KartuKerangka } from "@/components/wiki/kartu";
// services
import { ProjectPageService } from "@/services/page";
// local imports
import {
  anakDari,
  divisiDari,
  halamanDenganId,
  halamanTerlihat,
  izinFolderDari,
  jumlahMateriDalam,
  useIzinWiki,
  useJumlahMateriWiki,
  usePohonWiki,
  useProjectWiki,
} from "./data";
import { GridMateri, SeksiSubtopik, TombolUnggah, useMateriTopik } from "./daftar-materi";
import { KelolaFolder } from "./kelola";

const layananHalaman = new ProjectPageService();

/**
 * Isi sebuah folder Wiki: materinya sendiri, lalu tiap sub-topik sebagai seksi
 * yang bisa dibuka-tutup di daftar yang sama.
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
  const [sedangMembuatSub, setSedangMembuatSub] = useState(false);
  const [kelolaTerbuka, setKelolaTerbuka] = useState(false);
  const navigate = useNavigate();
  const { mutate: segarkan } = useSWRConfig();

  const terlihat = halamanTerlihat(halaman);
  const folder = halamanDenganId(terlihat, idFolder);
  const divisi = divisiDari(terlihat, folder?.id);
  const izinDivisi = izinFolderDari(izin, divisi?.id);
  const subtopik = anakDari(terlihat, idFolder);

  const konteks = {
    workspaceSlug: slug,
    projectId: projectId ?? "",
    halaman: terlihat,
    jumlahMateri,
    onJumlahBerubah: muatUlangJumlah,
  };
  // Tanpa `revalidateOnFocus: false`: daftar ini membawa `can_upload` dan
  // `can_manage`, jadi ia harus ikut segar sama seperti useIzinWiki.
  const {
    daftar,
    sedangMemuat: memuatMateri,
    muatUlang: muatUlangMateri,
    inputBerkas,
    unggahan,
  } = useMateriTopik(konteks, projectId ? folder : undefined);
  const materi = daftar?.materials ?? [];
  // Boleh mengurus folder ini. Jawabannya datang dari server, bukan dihitung
  // ulang di sini, supaya aturan izinnya tidak pernah bercabang dua.
  const bolehKelola = !!folder?.id && !!izin?.manageable_page_ids?.includes(folder.id);

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

  if (!sedangMemuat && !folder)
    return (
      <div className="flex h-full w-full items-center justify-center p-8 text-center">
        <div className="max-w-md">
          <h2 className="text-14 font-semibold text-primary">{t("wiki_ui.folder.gone_title")}</h2>
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
  // Angkanya mencakup sub-topik, karena semuanya sekarang terlihat di daftar ini.
  const totalMateri = jumlahMateriDalam(terlihat, jumlahMateri, folder?.id);
  // Folder yang isinya cuma sub-topik tidak perlu kotak "belum ada materi" yang
  // besar; sub-topiknya sendiri sudah menjawab di mana materinya.
  const tampilkanKosong = !memuatMateri && materi.length === 0 && subtopik.length === 0;

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
            <h1 className="text-24 font-semibold tracking-tight text-primary">{judul}</h1>
            {bolehKelola && (
              <Button variant="secondary" size="sm" onClick={() => setKelolaTerbuka(true)}>
                <Settings2 className="size-3.5" />
                {t("wiki_ui.folder.manage")}
              </Button>
            )}
            {bolehKelola && (
              <Button variant="secondary" size="sm" onClick={() => void buatSubtopik()} loading={sedangMembuatSub}>
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

        <section className="flex-1 px-page-x py-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div className="flex items-baseline gap-2">
              <h2 className="text-14 font-semibold text-primary">{t("wiki_ui.folder.material_list")}</h2>
              <span className="rounded-full bg-layer-3 px-2 py-0.5 text-11 text-tertiary">
                {t("wiki_ui.folder.material_count", { count: totalMateri })}
              </span>
            </div>
            {inputBerkas}
            <TombolUnggah unggahan={unggahan} namaTopik={judul} />
          </div>

          <div className="space-y-4">
            {memuatMateri ? (
              <GridKartu>
                <KartuKerangka />
                <KartuKerangka />
              </GridKartu>
            ) : (
              materi.length > 0 && <GridMateri konteks={konteks} materi={materi} muatUlang={muatUlangMateri} />
            )}

            {tampilkanKosong && (
              <div className="rounded-lg border border-dashed border-subtle px-6 py-14 text-center">
                <p className="text-14 font-medium text-secondary">{t("wiki_ui.folder.empty_title")}</p>
                <p className="mt-1 text-12 text-tertiary">
                  {unggahan.bolehUnggah
                    ? t("wiki_ui.folder.empty_can_upload")
                    : t("wiki_ui.folder.empty_cannot_upload")}
                </p>
              </div>
            )}

            {projectId && subtopik.map((s) => <SeksiSubtopik key={s.id} konteks={konteks} topik={s} />)}
          </div>
        </section>
      </div>

      {folder && kelolaTerbuka && (
        <KelolaFolder
          workspaceSlug={slug}
          projectId={projectId ?? ""}
          folder={folder}
          izin={izin}
          isOpen={kelolaTerbuka}
          onClose={() => setKelolaTerbuka(false)}
          // Materi ikut dimuat ulang: mengganti pemilik divisi mengubah `can_upload`
          // folder ini DAN semua sub-topiknya, yang datang dari daftar materi.
          onBerubah={() =>
            Promise.all([
              muatUlang(),
              muatUlangIzin(),
              segarkan((k) => typeof k === "string" && k.startsWith("WIKI_MATERIALS_")),
            ])
          }
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
