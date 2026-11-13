/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: folder Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { observer } from "mobx-react";
import { BookOpen, Settings2 } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router";
import { useSWRConfig } from "swr";
import { useTranslation } from "@plane/i18n";
import { Button, getButtonStyling } from "@plane/propel/button";
import { Logo } from "@plane/propel/emoji-icon-picker";
import { cn, sanitizeRichHTML } from "@plane/utils";
// components
import { PageHead } from "@/components/core/page-title";
import { gradienUntuk } from "@/components/wiki/gradien";
import { GridKartu, KartuKerangka } from "@/components/wiki/kartu";
// local imports
import { UbinTambahSubtopik, bolehTambahSubtopik, useBuatSubtopik } from "./buat-subtopik";
import { GridMateri, KerangkaUnggah, SeksiSubtopik, ZonaKosong, useMateriTopik } from "./daftar-materi";
import { anakDari, folderDenganId, folderTerlihat, jumlahHalamanDalam, jumlahMateriDalam, usePohonWiki } from "./data";
import { HalamanDepartemen } from "./halaman-departemen";
import { KelolaFolder } from "./kelola";

/** Judul satu bagian halaman: nama dan angka. Seragam supaya bagiannya mudah dipindai. */
function JudulBagian({ judul, angka }: { judul: string; angka?: number }) {
  return (
    <div className="flex items-baseline gap-2">
      <h2 className="text-14 font-semibold text-primary">{judul}</h2>
      {angka !== undefined && (
        <span className="rounded-control bg-layer-3 px-2 py-0.5 text-11 text-tertiary">{angka}</span>
      )}
    </div>
  );
}

function Chip({ children }: { children: ReactNode }) {
  return <span className="rounded-control bg-layer-3 px-2.5 py-1 text-12 font-medium text-secondary">{children}</span>;
}

/**
 * Isi sebuah folder Wiki. Satu halaman dipakai untuk divisi, departemen, dan
 * topik, dan itu disengaja: yang membedakan hanya apa yang kebetulan ada di dalamnya.
 *
 * Urutannya selalu dari yang paling sering dicari:
 * - Divisi: departemen (masing-masing terbuka dengan isinya), sub-topik, lalu materi divisi.
 * - Departemen dan topik: materi, sub-topik, lalu halaman project departemen.
 *
 * Posisi orang di pohon ditunjukkan breadcrumb di kepala Wiki (header.tsx),
 * jadi halaman ini tidak punya tautan kembali sendiri.
 */
function WikiFolderPage() {
  const { t } = useTranslation();
  const { workspaceSlug, folderId } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const idFolder = folderId?.toString() ?? "";
  const { folder: semuaFolder, sedangMemuat, muatUlang } = usePohonWiki(slug);
  const [kelolaTerbuka, setKelolaTerbuka] = useState(false);
  const navigate = useNavigate();
  const { mutate: segarkan } = useSWRConfig();

  const terlihat = useMemo(() => folderTerlihat(semuaFolder), [semuaFolder]);
  const folder = folderDenganId(terlihat, idFolder);
  const anak = anakDari(terlihat, idFolder);
  const departemen = anak.filter((f) => f.departemen_id);
  const subtopik = anak.filter((f) => !f.departemen_id);
  const adalahDivisi = !!folder?.divisi_id;
  const isiLama = folder?.isi_lama_html ? sanitizeRichHTML(folder.isi_lama_html).trim() : "";

  const konteks = { workspaceSlug: slug, folder: terlihat, onJumlahBerubah: muatUlang };
  const {
    buat: buatSubtopik,
    sedangMembuat: sedangMembuatSub,
    dialog: dialogSubtopik,
  } = useBuatSubtopik(slug, muatUlang);
  // Tanpa `revalidateOnFocus: false`: daftar ini membawa `can_upload`, jadi ia
  // harus ikut segar sama seperti pohonnya.
  const {
    daftar,
    sedangMemuat: memuatMateri,
    muatUlang: muatUlangMateri,
    inputBerkas,
    unggahan,
    lepas,
  } = useMateriTopik(konteks, folder);
  const materi = daftar?.materials ?? [];
  // Jawaban server, bukan dihitung ulang di sini, supaya aturan izinnya tidak pernah bercabang dua.
  const bolehKelola = !!folder?.can_manage;

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
  // Angkanya mencakup sub-folder, karena semuanya terlihat di halaman ini.
  const totalMateri = jumlahMateriDalam(terlihat, folder?.id);
  const totalHalaman = jumlahHalamanDalam(terlihat, folder?.id);

  // Materi folder ini sendiri. Daftar kosong menampilkan area seret-lepas besar;
  // daftar berisi menampilkan yang ringkas di bawahnya.
  const bagianMateri = (
    <div className="space-y-4">
      <JudulBagian judul={t("wiki_ui.folder.material_list")} angka={materi.length} />

      {memuatMateri ? (
        <GridKartu>
          <KartuKerangka />
          <KartuKerangka />
        </GridKartu>
      ) : materi.length > 0 ? (
        <>
          <GridMateri konteks={konteks} materi={materi} muatUlang={muatUlangMateri} />
          {/* Penanda lepas yang selalu ada, bukan hanya saat daftar kosong. */}
          <ZonaKosong unggahan={unggahan} ringkas />
        </>
      ) : (
        <ZonaKosong unggahan={unggahan} />
      )}
    </div>
  );

  const bisaTambahSub = bolehTambahSubtopik(folder);
  const bagianTopik = (subtopik.length > 0 || bisaTambahSub) && (
    <div className="space-y-3">
      <JudulBagian judul={t("wiki_ui.folder.subtopics_title")} angka={subtopik.length || undefined} />
      {subtopik.map((s) => (
        <SeksiSubtopik key={s.id} konteks={konteks} topik={s} />
      ))}
      {bisaTambahSub && <UbinTambahSubtopik onClick={() => void buatSubtopik(idFolder)} loading={sedangMembuatSub} />}
    </div>
  );

  // Departemen langsung sebagai seksi di halaman ini, lengkap dengan materi,
  // halaman, dan sub-topiknya, bukan kartu yang harus diklik satu per satu.
  const bagianDepartemen = departemen.length > 0 && (
    <div className="space-y-3">
      <JudulBagian judul={t("wiki_ui.folder.departments")} angka={departemen.length} />
      {departemen.map((d) => (
        <SeksiSubtopik key={d.id} konteks={konteks} topik={d} />
      ))}
    </div>
  );

  return (
    <>
      <PageHead title={t("wiki_ui.folder.page_title", { name: judul })} />
      {/* Seret berkas ke mana saja di halaman ini = unggah ke folder ini. Seksi
          sub-topik punya area sendiri dan menang di wilayahnya. */}
      <KerangkaUnggah lepas={lepas} inputBerkas={inputBerkas}>
        <div className="flex min-h-full w-full flex-col">
          <header className="border-b border-subtle bg-surface-1 px-page-x py-6">
            <div className="flex flex-wrap items-start gap-4">
              <span
                className="grid size-14 shrink-0 place-items-center rounded-card text-white"
                style={{ backgroundImage: gradienUntuk(judul) }}
              >
                {folder?.logo_props?.in_use ? (
                  <Logo logo={folder.logo_props} size={26} type="lucide" />
                ) : (
                  <BookOpen className="size-7" strokeWidth={1.5} />
                )}
              </span>
              <div className="min-w-0 flex-1">
                <h1 className="truncate text-24 font-semibold tracking-tight text-primary">{judul}</h1>
                {(folder?.keterangan || folder?.umum) && (
                  <p className="mt-1 max-w-3xl text-13 text-tertiary">
                    {folder.keterangan || t("wiki_ui.folder.access_general")}
                  </p>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  <Chip>{t("wiki_ui.folder.material_count", { count: totalMateri })}</Chip>
                  {departemen.length > 0 && (
                    <Chip>
                      {departemen.length} {t("wiki_ui.folder.departments")}
                    </Chip>
                  )}
                  {subtopik.length > 0 && <Chip>{t("wiki_ui.folder.subtopic_count", { count: subtopik.length })}</Chip>}
                  {totalHalaman > 0 && (
                    <Chip>
                      {totalHalaman} {t("wiki_ui.common.page_unit")}
                    </Chip>
                  )}
                </div>
              </div>
              {/* Pengelolaan folder dikelompokkan di satu tempat, rata kanan. */}
              {bolehKelola && (
                <div className="flex shrink-0 items-center gap-2">
                  <Button variant="secondary" size="sm" onClick={() => setKelolaTerbuka(true)}>
                    <Settings2 className="size-3.5" />
                    {t("wiki_ui.folder.manage")}
                  </Button>
                </div>
              )}
            </div>
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
          </header>

          <section className="flex-1 space-y-10 px-page-x py-6">
            {adalahDivisi ? (
              <>
                {bagianDepartemen}
                {bagianTopik}
                {bagianMateri}
              </>
            ) : (
              <>
                {bagianMateri}
                {bagianTopik}
                {/* Halaman project departemen, cermin baca saja (KEP-95). */}
                {folder?.departemen_id && (
                  <HalamanDepartemen key={folder.id} workspaceSlug={slug} folderId={folder.id} />
                )}
              </>
            )}
          </section>
        </div>
      </KerangkaUnggah>

      {dialogSubtopik}

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
