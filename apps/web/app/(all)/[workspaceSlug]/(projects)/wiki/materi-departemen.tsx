/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tab Materials di project departemen (KEP-97)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo, useState } from "react";
import { observer } from "mobx-react";
import { ArrowUpRight, BookOpen, Undo2 } from "lucide-react";
import { Link } from "react-router";
import useSWR, { useSWRConfig } from "swr";
import { useTranslation } from "@plane/i18n";
import { Button, getButtonStyling } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { renderFormattedDate } from "@plane/utils";
// components
import { GridKartu, KartuKerangka } from "@/components/wiki/kartu";
// local imports
import {
  anakDari,
  folderTerlihat,
  jumlahMateriDalam,
  labelTipe,
  layananWiki,
  ukuranTerbaca,
  usePohonWiki,
} from "./data";
import { UbinTambahSubtopik, bolehTambahSubtopik, useBuatSubtopik } from "./buat-subtopik";
import { GridMateri, KerangkaUnggah, SeksiSubtopik, ZonaKosong, useMateriTopik } from "./daftar-materi";

type TProps = { workspaceSlug: string; projectId: string };

const kunciSampah = (workspaceSlug: string, folderId: string) => `WIKI_TRASH_${workspaceSlug}_${folderId}`;

/**
 * Materi Wiki departemen, dikelola langsung dari project departemennya.
 *
 * Ini bukan Wiki kedua: foldernya folder departemen yang sama, dan semua bagian
 * (daftar, unggah, seret-lepas, ganti judul, hapus, sub-topik) memakai komponen
 * dan endpoint Wiki yang sama. Izin (`can_upload`, `can_manage`, `can_delete`)
 * datang dari server per materi dan per folder, aturan KEP-95.
 *
 * Yang tetap di Wiki: struktur folder (buat/arsip sub-topik, keterangan, ikon).
 * Tautan "Open in Wiki" membawa ke sana.
 */
export const MateriDepartemen = observer(function MateriDepartemen({ workspaceSlug, projectId }: TProps) {
  const { t } = useTranslation();
  const { folder: semua, sedangMemuat: memuatPohon, galat, muatUlang: muatUlangPohon } = usePohonWiki(workspaceSlug);
  const terlihat = useMemo(() => folderTerlihat(semua), [semua]);
  const folder = terlihat.find((f) => f.project_id === projectId && !!f.departemen_id);
  const folderId = folder?.id;

  const { data: sampah, mutate: muatUlangSampah } = useSWR(
    folderId ? kunciSampah(workspaceSlug, folderId) : null,
    folderId ? () => layananWiki.fetchTrash(workspaceSlug, folderId) : null
  );
  // Hapus memindahkan materi ke sampah, jadi daftar sampah ikut segar.
  const konteks = {
    workspaceSlug,
    folder: terlihat,
    onJumlahBerubah: () => Promise.all([muatUlangPohon(), muatUlangSampah()]),
  };
  const { daftar, sedangMemuat, muatUlang, inputBerkas, unggahan, lepas } = useMateriTopik(konteks, folder);
  const {
    buat: buatSubtopik,
    sedangMembuat: sedangMembuatSub,
    dialog: dialogSubtopik,
  } = useBuatSubtopik(workspaceSlug, konteks.onJumlahBerubah);

  if (memuatPohon && !semua)
    return (
      <div className="px-page-x py-6">
        <GridKartu>
          <KartuKerangka />
          <KartuKerangka />
        </GridKartu>
      </div>
    );

  if (galat && !semua)
    return (
      <Kosong
        judul={t("wiki_ui.common.load_failed_title")}
        isi={galat.error || t("wiki_ui.common.load_failed_message")}
      />
    );

  if (!folder) return <Kosong judul={t("wiki_ui.tab.no_folder_title")} isi={t("wiki_ui.tab.no_folder_message")} />;

  const materi = daftar?.materials ?? [];
  const subtopik = anakDari(terlihat, folder.id);
  const total = jumlahMateriDalam(terlihat, folder.id);

  return (
    <>
      <KerangkaUnggah lepas={lepas} inputBerkas={inputBerkas}>
        <div className="flex min-h-full w-full flex-col">
          <div className="border-b border-subtle bg-surface-1 px-page-x py-6">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-20 font-semibold tracking-tight text-primary">
                {t("wiki_ui.tab.heading", { name: folder.nama })}
              </h1>
              <span className="rounded-control bg-layer-3 px-2 py-0.5 text-11 text-tertiary">
                {t("wiki_ui.folder.material_count", { count: total })}
              </span>
              <div className="ml-auto flex items-center gap-2">
                <Link to={`/${workspaceSlug}/wiki/${folder.id}`} className={getButtonStyling("secondary", "base")}>
                  <BookOpen className="size-3.5" />
                  {t("wiki_ui.tab.open_in_wiki")}
                  <ArrowUpRight className="size-3.5" />
                </Link>
              </div>
            </div>
            <p className="mt-1 max-w-3xl text-13 text-tertiary">
              {t("wiki_ui.tab.description", { name: folder.nama })}
            </p>
          </div>

          <section className="flex-1 space-y-8 px-page-x py-6">
            {sedangMemuat ? (
              <GridKartu>
                <KartuKerangka />
                <KartuKerangka />
              </GridKartu>
            ) : materi.length > 0 ? (
              <div className="space-y-4">
                <GridMateri konteks={konteks} materi={materi} muatUlang={muatUlang} />
                <ZonaKosong unggahan={unggahan} ringkas />
              </div>
            ) : (
              <ZonaKosong unggahan={unggahan} />
            )}

            {(subtopik.length > 0 || bolehTambahSubtopik(folder)) && (
              <div className="space-y-4">
                {subtopik.map((s) => (
                  <SeksiSubtopik key={s.id} konteks={konteks} topik={s} />
                ))}
                {bolehTambahSubtopik(folder) && (
                  <UbinTambahSubtopik onClick={() => void buatSubtopik(folder.id)} loading={sedangMembuatSub} />
                )}
              </div>
            )}

            <SampahDepartemen
              workspaceSlug={workspaceSlug}
              materi={sampah?.materials ?? []}
              onDipulihkan={() => Promise.all([muatUlangSampah(), muatUlangPohon()])}
            />
          </section>
        </div>
      </KerangkaUnggah>
      {dialogSubtopik}
    </>
  );
});

function Kosong({ judul, isi }: { judul: string; isi: string }) {
  return (
    <div className="flex h-full w-full items-center justify-center p-8 text-center">
      <div className="max-w-md">
        <h2 className="text-14 font-semibold text-primary">{judul}</h2>
        <p className="mt-1 text-13 text-tertiary">{isi}</p>
      </div>
    </div>
  );
}

type TSampah = {
  workspaceSlug: string;
  materi: { id: string; judul: string; type: string; size: number; deleted_at: string }[];
  onDipulihkan: () => Promise<unknown>;
};

/**
 * Materi yang dihapus dari folder departemen ini. Server sudah menyaring per
 * orang (pengelola: semua di wilayahnya; yang lain: unggahannya sendiri) dan
 * per folder (`?folder=`), jadi yang tampil di sini selalu boleh dipulihkan.
 */
function SampahDepartemen({ workspaceSlug, materi, onDipulihkan }: TSampah) {
  const { t } = useTranslation();
  const { mutate: segarkan } = useSWRConfig();
  const [sedang, setSedang] = useState<string | null>(null);

  if (materi.length === 0) return null;

  const pulihkan = async (id: string, judul: string) => {
    if (sedang) return;
    setSedang(id);
    try {
      await layananWiki.restoreMaterial(workspaceSlug, id);
      await Promise.all([onDipulihkan(), segarkan((k) => typeof k === "string" && k.startsWith("WIKI_MATERIALS_"))]);
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("wiki_ui.trash.restored_title"), message: judul });
    } catch (e) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("wiki_ui.trash.restore_failed"),
        message: (e as { error?: string })?.error || t("wiki_ui.common.try_again"),
      });
    } finally {
      setSedang(null);
    }
  };

  return (
    <div className="space-y-3">
      <div>
        <h2 className="text-14 font-semibold text-primary">{t("wiki_ui.tab.trash_title")}</h2>
        <p className="mt-1 text-12 text-tertiary">{t("wiki_ui.tab.trash_hint")}</p>
      </div>
      <div className="overflow-hidden rounded-card border border-subtle bg-surface-1">
        {materi.map((m) => (
          <div
            key={m.id}
            className="flex items-center justify-between gap-3 border-t border-subtle px-3 py-2.5 first:border-t-0"
          >
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
              loading={sedang === m.id}
              onClick={() => void pulihkan(m.id, m.judul)}
            >
              <Undo2 className="size-3.5" />
              {t("wiki_ui.trash.restore")}
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
