/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: folder Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo, useState } from "react";
import { observer } from "mobx-react";
import { ArrowLeft, Plus, Settings2 } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router";
import { useSWRConfig } from "swr";
import { useTranslation } from "@plane/i18n";
import { Button, getButtonStyling } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { cn, sanitizeRichHTML } from "@plane/utils";
// components
import { PageHead } from "@/components/core/page-title";
import { GridKartu, KartuFolder, KartuKerangka } from "@/components/wiki/kartu";
// local imports
import { anakDari, folderDenganId, folderTerlihat, jumlahMateriDalam, layananWiki, usePohonWiki } from "./data";
import { GridMateri, SeksiSubtopik, TombolUnggah, useMateriTopik } from "./daftar-materi";
import { KelolaFolder } from "./kelola";

/**
 * Isi sebuah folder Wiki: materinya sendiri, lalu tiap sub-topik sebagai seksi
 * yang bisa dibuka-tutup di daftar yang sama.
 *
 * Satu halaman dipakai untuk divisi, departemen, dan topik, dan itu disengaja.
 * Yang membedakan hanya apa yang kebetulan ada di dalamnya. Folder divisi
 * menampilkan folder departemennya lebih dulu, lalu topiknya, lalu materinya.
 */
function WikiFolderPage() {
  const { t } = useTranslation();
  const { workspaceSlug, folderId } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const idFolder = folderId?.toString() ?? "";
  const { folder: semuaFolder, sedangMemuat, muatUlang } = usePohonWiki(slug);
  const [sedangMembuatSub, setSedangMembuatSub] = useState(false);
  const [kelolaTerbuka, setKelolaTerbuka] = useState(false);
  const navigate = useNavigate();
  const { mutate: segarkan } = useSWRConfig();

  const terlihat = useMemo(() => folderTerlihat(semuaFolder), [semuaFolder]);
  const folder = folderDenganId(terlihat, idFolder);
  const induk = folderDenganId(terlihat, folder?.parent_id);
  const anak = anakDari(terlihat, idFolder);
  const departemen = anak.filter((f) => f.departemen_id);
  const subtopik = anak.filter((f) => !f.departemen_id);
  const adalahDivisi = !!folder?.divisi_id;
  const isiLama = folder?.isi_lama_html ? sanitizeRichHTML(folder.isi_lama_html).trim() : "";

  const konteks = { workspaceSlug: slug, folder: terlihat, onJumlahBerubah: muatUlang };
  // Tanpa `revalidateOnFocus: false`: daftar ini membawa `can_upload`, jadi ia
  // harus ikut segar sama seperti pohonnya.
  const {
    daftar,
    sedangMemuat: memuatMateri,
    muatUlang: muatUlangMateri,
    inputBerkas,
    unggahan,
  } = useMateriTopik(konteks, folder);
  const materi = daftar?.materials ?? [];
  // Jawaban server, bukan dihitung ulang di sini, supaya aturan izinnya tidak pernah bercabang dua.
  const bolehKelola = !!folder?.can_manage;

  const buatSubtopik = async () => {
    if (!idFolder || sedangMembuatSub) return;
    setSedangMembuatSub(true);
    try {
      await layananWiki.createFolder(slug, { nama: t("wiki_ui.folder.new_topic_name"), parent_id: idFolder });
      await muatUlang();
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("wiki_ui.folder.subtopic_created_title") });
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
          <Link to={`/${slug}/wiki`} className={cn(getButtonStyling("secondary", "lg"), "mt-4")}>
            {t("wiki_ui.common.back_to_home")}
          </Link>
        </div>
      </div>
    );

  const judul = folder?.nama ?? "";
  // Angkanya mencakup sub-folder, karena semuanya terlihat di daftar ini.
  const totalMateri = jumlahMateriDalam(terlihat, folder?.id);
  // Folder yang isinya cuma sub-folder tidak perlu kotak "belum ada materi" yang besar.
  const tampilkanKosong = !memuatMateri && materi.length === 0 && anak.length === 0;

  const bagianMateri = (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-baseline gap-2">
          <h2 className="text-14 font-semibold text-primary">{t("wiki_ui.folder.material_list")}</h2>
          <span className="rounded-control bg-layer-3 px-2 py-0.5 text-11 text-tertiary">
            {t("wiki_ui.folder.material_count", { count: totalMateri })}
          </span>
        </div>
        {inputBerkas}
        <TombolUnggah unggahan={unggahan} namaTopik={judul} />
      </div>

      {memuatMateri ? (
        <GridKartu>
          <KartuKerangka />
          <KartuKerangka />
        </GridKartu>
      ) : (
        materi.length > 0 && <GridMateri konteks={konteks} materi={materi} muatUlang={muatUlangMateri} />
      )}

      {tampilkanKosong && (
        <div className="rounded-card border border-dashed border-subtle px-6 py-14 text-center">
          <p className="text-14 font-medium text-secondary">{t("wiki_ui.folder.empty_title")}</p>
          <p className="mt-1 text-12 text-tertiary">
            {unggahan.bolehUnggah ? t("wiki_ui.folder.empty_can_upload") : t("wiki_ui.folder.empty_cannot_upload")}
          </p>
        </div>
      )}
    </div>
  );

  const bagianTopik = subtopik.length > 0 && (
    <div className="space-y-4">
      {subtopik.map((s) => (
        <SeksiSubtopik key={s.id} konteks={konteks} topik={s} />
      ))}
    </div>
  );

  const bagianDepartemen = departemen.length > 0 && (
    <div className="space-y-4">
      <div className="flex items-baseline gap-2">
        <h2 className="text-14 font-semibold text-primary">{t("wiki_ui.folder.departments")}</h2>
        <span className="rounded-control bg-layer-3 px-2 py-0.5 text-11 text-tertiary">{departemen.length}</span>
      </div>
      <GridKartu>
        {departemen.map((d) => (
          <KartuFolder
            key={d.id}
            to={`/${slug}/wiki/${d.id}`}
            judul={d.nama}
            logoProps={d.logo_props ?? undefined}
            keterangan={d.keterangan}
            jumlahAnak={jumlahMateriDalam(terlihat, d.id)}
            satuanAnak={t("wiki_ui.common.material_unit")}
          />
        ))}
      </GridKartu>
    </div>
  );

  return (
    <>
      <PageHead title={t("wiki_ui.folder.page_title", { name: judul })} />
      <div className="flex h-full w-full flex-col overflow-y-auto">
        <div className="border-b border-subtle bg-surface-1 px-page-x py-8">
          <Link
            to={folder?.parent_id ? `/${slug}/wiki/${folder.parent_id}` : `/${slug}/wiki`}
            className="inline-flex items-center gap-1.5 text-12 text-tertiary transition-colors hover:text-secondary"
          >
            <ArrowLeft className="size-3.5" />
            {induk ? t("wiki_ui.folder.back_to_parent", { name: induk.nama }) : t("wiki_ui.common.back_to_home")}
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
          {(folder?.keterangan || folder?.umum) && (
            <p className="mt-1 max-w-3xl text-13 text-tertiary">
              {folder.keterangan || t("wiki_ui.folder.access_general")}
            </p>
          )}
          {isiLama && (
            <div className="mt-4 max-w-3xl">
              <h2 className="text-12 font-medium text-secondary">{t("wiki_ui.folder.legacy_title")}</h2>
              <div
                className="mt-2 rounded-card border border-subtle bg-layer-1 p-4 text-13 text-secondary [&_a]:text-accent-primary [&_a]:underline [&_h1]:text-16 [&_h1]:font-semibold [&_h2]:text-14 [&_h2]:font-semibold [&_h3]:font-semibold [&_img]:max-w-full [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-1.5 [&_ul]:list-disc [&_ul]:pl-5"
                // Sudah disanitasi dengan allowlist (sanitizeRichHTML); hanya baca.
                // oxlint-disable-next-line react/no-danger
                dangerouslySetInnerHTML={{ __html: isiLama }}
              />
            </div>
          )}
        </div>

        <section className="flex-1 space-y-8 px-page-x py-6">
          {adalahDivisi ? (
            <>
              {bagianDepartemen}
              {bagianTopik}
              {bagianMateri}
            </>
          ) : (
            <>
              {bagianDepartemen}
              {bagianMateri}
              {bagianTopik}
            </>
          )}
        </section>
      </div>

      {folder && kelolaTerbuka && (
        <KelolaFolder
          workspaceSlug={slug}
          folder={folder}
          isOpen={kelolaTerbuka}
          onClose={() => setKelolaTerbuka(false)}
          // Materi ikut dimuat ulang: perubahan struktur bisa mengubah `can_upload`
          // folder ini dan sub-foldernya, yang datang dari daftar materi.
          onBerubah={() =>
            Promise.all([muatUlang(), segarkan((k) => typeof k === "string" && k.startsWith("WIKI_MATERIALS_"))])
          }
          onTerhapus={() => {
            setKelolaTerbuka(false);
            void muatUlang();
            navigate(folder.parent_id ? `/${slug}/wiki/${folder.parent_id}` : `/${slug}/wiki`);
          }}
        />
      )}
    </>
  );
}

export default observer(WikiFolderPage);
