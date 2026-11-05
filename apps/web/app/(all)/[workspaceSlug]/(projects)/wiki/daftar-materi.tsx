/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: daftar materi Wiki + sub-topik yang bisa dibuka-tutup
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useId, useRef, useState } from "react";
import { observer } from "mobx-react";
import { ArrowUpRight, ChevronRight, Pencil, Trash2, Upload } from "lucide-react";
import { Link } from "react-router";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import { Button, getButtonStyling } from "@plane/propel/button";
import { Logo } from "@plane/propel/emoji-icon-picker";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { cn, renderFormattedDate } from "@plane/utils";
// components
import { GridKartu, KartuKerangka, KartuMateri } from "@/components/wiki/kartu";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useKonfirmasi } from "@/hooks/use-konfirmasi";
import useLocalStorage from "@/hooks/use-local-storage";
// services
import type { TWikiFolder, TWikiMaterialList } from "@/services/wiki.service";
// local imports
import { GantiNamaMateri } from "./ganti-nama";
import { anakDari, jumlahMateriDalam, labelTipe, layananWiki, ukuranTerbaca } from "./data";

/** Kunci SWR daftar materi satu topik. Dipakai bersama, jadi folder dan seksinya tidak mengambil dua kali. */
export const kunciMateriTopik = (topikId: string) => `WIKI_MATERIALS_${topikId}`;

/**
 * Sub-topik yang DITUTUP orang, bukan yang dibuka. Bawaannya semua terbuka,
 * karena tujuan seluruh tampilan ini justru melihat isi tanpa klik tambahan.
 * Yang disimpan cukup pengecualiannya.
 */
const KUNCI_TERTUTUP = "wiki_subtopik_tertutup";
const TIDAK_ADA: string[] = [];

type TKonteks = {
  workspaceSlug: string;
  /** Seluruh folder Wiki yang terlihat, untuk menelusuri sub-topik bertingkat. */
  folder: TWikiFolder[];
  /** Dipanggil sesudah unggah atau hapus, supaya angka di kartu folder ikut benar. */
  onJumlahBerubah: () => Promise<unknown>;
};

type TUnggah = { bolehUnggah: boolean; sedangUnggah: boolean; pilihBerkas: () => void };

/**
 * Satu topik = satu daftar materi + unggahnya.
 *
 * Folder induk dan tiap sub-topik memakai hook yang sama, jadi izin unggah dan
 * kelola SELALU datang dari jawaban server untuk topik itu sendiri. Sub-topik
 * tidak mewarisi tombol unggah induknya hanya karena tampil di halaman yang sama.
 */
export function useMateriTopik(konteks: TKonteks, topik: TWikiFolder | undefined, aktif = true) {
  const { t } = useTranslation();
  const { workspaceSlug, onJumlahBerubah } = konteks;
  const topikId = topik?.id;
  const { data, isLoading, mutate } = useSWR(
    aktif && topikId ? kunciMateriTopik(topikId) : null,
    topikId ? () => layananWiki.fetchMaterials(workspaceSlug, topikId) : null
  );
  const berkasRef = useRef<HTMLInputElement>(null);
  const [sedangUnggah, setSedangUnggah] = useState(false);

  const unggah = async (files: FileList | null) => {
    if (!topikId || !files?.length) return;
    setSedangUnggah(true);
    let berhasil = 0;
    // Sengaja berurutan, bukan Promise.all. Satu berkas di sini boleh 500 MB;
    // mengunggah sepuluh sekaligus menghabiskan jalur WiFi kantor dan membuat
    // semuanya gagal berbarengan alih-alih selesai satu per satu.
    for (const file of Array.from(files)) {
      try {
        // oxlint-disable-next-line no-await-in-loop
        await layananWiki.upload(workspaceSlug, topikId, file);
        berhasil += 1;
      } catch (error) {
        // Satu berkas gagal tidak membatalkan sisanya, dan orangnya harus tahu
        // berkas MANA yang gagal, bukan cuma "ada yang gagal".
        setToast({
          type: TOAST_TYPE.ERROR,
          title: t("wiki_ui.folder.upload_failed_title", { name: file.name }),
          message: (error as { error?: string })?.error || t("wiki_ui.folder.upload_failed_message"),
        });
      }
    }
    setSedangUnggah(false);
    if (berhasil > 0) {
      await Promise.all([mutate(), onJumlahBerubah()]);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("wiki_ui.folder.uploaded_title"),
        message: t("wiki_ui.folder.uploaded_message", { count: berhasil, folder: topik?.nama ?? "" }),
      });
    }
    if (berkasRef.current) berkasRef.current.value = "";
  };

  const inputBerkas = (
    <input ref={berkasRef} type="file" multiple className="hidden" onChange={(e) => void unggah(e.target.files)} />
  );

  const unggahan: TUnggah = {
    bolehUnggah: !!data?.can_upload,
    sedangUnggah,
    pilihBerkas: () => berkasRef.current?.click(),
  };

  return { daftar: data, sedangMemuat: isLoading, muatUlang: mutate, inputBerkas, unggahan };
}

/** Tombol unggah atau keterangan terkunci, satu bentuk untuk folder dan sub-topik. */
export function TombolUnggah({
  unggahan,
  ringkas,
  namaTopik,
}: {
  unggahan: TUnggah;
  ringkas?: boolean;
  namaTopik: string;
}) {
  const { t } = useTranslation();
  if (!unggahan.bolehUnggah) return null;
  return (
    <Button
      variant={ringkas ? "secondary" : "primary"}
      size="sm"
      onClick={unggahan.pilihBerkas}
      loading={unggahan.sedangUnggah}
      aria-label={t("wiki_ui.folder.upload_to_named", { name: namaTopik })}
    >
      <Upload className="size-3.5" />
      {/* Versi ringkas (judul sub-topik) cuma ikon di HP: barisnya juga memuat
          nama, jumlah materi, dan tautan buka. */}
      <span className={ringkas ? "hidden sm:inline" : undefined}>{t("wiki_ui.folder.upload_material")}</span>
    </Button>
  );
}

const KELAS_AKSI =
  "grid size-7 place-items-center rounded-button bg-black/25 text-white opacity-0 backdrop-blur-[1px] transition-opacity group-focus-within:opacity-100 group-hover:opacity-100 hover:bg-black/40 focus-visible:opacity-100 sentuh:size-9 sentuh:opacity-100";

/** Grid kartu materi berikut tombol ganti judul dan hapus, kalau orangnya berhak. */
export const GridMateri = observer(function GridMateri({
  konteks,
  materi,
  muatUlang,
}: {
  konteks: TKonteks;
  materi: TWikiMaterialList["materials"];
  muatUlang: () => Promise<unknown>;
}) {
  const { t } = useTranslation();
  const { workspaceSlug, onJumlahBerubah } = konteks;
  const { getUserDetails } = useMember();
  const [materiDiganti, setMateriDiganti] = useState<{ id: string; judul: string; name: string } | null>(null);
  const { minta, dialog: dialogKonfirmasi } = useKonfirmasi();

  const hapus = async (assetId: string, judul: string) => {
    try {
      await layananWiki.deleteMaterial(workspaceSlug, assetId);
      await Promise.all([muatUlang(), onJumlahBerubah()]);
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("wiki_ui.folder.deleted_title"), message: judul });
    } catch (error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("wiki_ui.folder.delete_failed_title"),
        message: (error as { error?: string })?.error || t("wiki_ui.common.try_again"),
      });
    }
  };

  return (
    <>
      <GridKartu>
        {materi.map((m) => (
          <KartuMateri
            key={m.id}
            to={`/${workspaceSlug}/wiki/materi/${m.id}`}
            judul={m.judul}
            keterangan={[
              m.created_by ? getUserDetails(m.created_by)?.display_name : undefined,
              renderFormattedDate(m.created_at),
            ]
              .filter(Boolean)
              .join(" · ")}
            tipe={m.type}
            label={labelTipe(m.type, t)}
            ukuran={ukuranTerbaca(m.size)}
            aksi={
              m.can_manage || m.can_delete ? (
                <>
                  {m.can_manage && (
                    <button
                      type="button"
                      title={t("wiki_ui.folder.rename")}
                      aria-label={t("wiki_ui.folder.rename_named", { title: m.judul })}
                      onClick={() => setMateriDiganti({ id: m.id, judul: m.judul, name: m.name })}
                      className={KELAS_AKSI}
                    >
                      <Pencil className="size-3.5" />
                    </button>
                  )}
                  {m.can_delete && (
                    <button
                      type="button"
                      title={t("wiki_ui.folder.delete")}
                      aria-label={t("wiki_ui.folder.delete_named", { title: m.judul })}
                      onClick={() =>
                        minta(
                          {
                            judul: t("wiki_ui.folder.confirm_delete_title"),
                            isi: t("wiki_ui.folder.confirm_delete_body", { title: m.judul }),
                          },
                          () => hapus(m.id, m.judul)
                        )
                      }
                      className={KELAS_AKSI}
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  )}
                </>
              ) : undefined
            }
          />
        ))}
      </GridKartu>

      {dialogKonfirmasi}

      {materiDiganti && (
        <GantiNamaMateri
          workspaceSlug={workspaceSlug}
          materiId={materiDiganti.id}
          judulSekarang={materiDiganti.judul}
          namaBerkas={materiDiganti.name}
          isOpen
          onClose={() => setMateriDiganti(null)}
          onSelesai={() => muatUlang()}
        />
      )}
    </>
  );
});

/**
 * Sub-topik sebagai seksi yang bisa dibuka-tutup, langsung di dalam Daftar
 * Materi induknya.
 *
 * Dulu sub-topik tampil sebagai kartu yang harus diklik dulu untuk melihat
 * isinya, jadi satu berkas di sub-topik butuh dua klik plus satu halaman
 * tambahan. Sekarang materinya terlihat di tempat, dan sub-topik di bawahnya
 * ikut bersarang di seksi yang sama. Halaman sub-topik sendiri tetap ada
 * (tautan "Buka") untuk mengelola atau membagikan alamatnya.
 *
 * Materinya baru diambil saat seksinya terbuka, jadi seksi yang ditutup orang
 * tidak memakan permintaan.
 */
export const SeksiSubtopik = observer(function SeksiSubtopik({
  konteks,
  topik,
  kedalaman = 0,
}: {
  konteks: TKonteks;
  topik: TWikiFolder;
  kedalaman?: number;
}) {
  const { t } = useTranslation();
  const idIsi = useId();
  const { storedValue: tertutup, setValue: setTertutup } = useLocalStorage<string[]>(KUNCI_TERTUTUP, TIDAK_ADA);
  const idTopik = topik.id;
  const terbuka = !(tertutup ?? TIDAK_ADA).includes(idTopik);
  const { daftar, sedangMemuat, muatUlang, inputBerkas, unggahan } = useMateriTopik(konteks, topik, terbuka);

  const nama = topik.nama;
  const anak = anakDari(konteks.folder, topik.id);
  const total = jumlahMateriDalam(konteks.folder, topik.id);
  const materi = daftar?.materials ?? [];

  const alihkan = () => {
    const sekarang = tertutup ?? TIDAK_ADA;
    setTertutup(terbuka ? [...sekarang, idTopik] : sekarang.filter((id) => id !== idTopik));
  };

  return (
    <section className={cn("rounded-card border border-subtle bg-surface-1", kedalaman > 0 && "bg-layer-1")}>
      <div className="flex items-center gap-2 px-3 py-2.5">
        <button
          type="button"
          onClick={alihkan}
          aria-expanded={terbuka}
          aria-controls={idIsi}
          aria-label={t(terbuka ? "wiki_ui.folder.collapse_named" : "wiki_ui.folder.expand_named", { name: nama })}
          className="flex min-w-0 flex-1 items-center gap-2 rounded-item px-1 py-1 text-left transition-colors hover:bg-layer-1-hover focus-visible:bg-layer-1-hover"
        >
          <ChevronRight
            className={cn("size-4 shrink-0 text-tertiary transition-transform duration-150", terbuka && "rotate-90")}
          />
          {topik.logo_props?.in_use && (
            <span className="grid size-5 shrink-0 place-items-center">
              <Logo logo={topik.logo_props} size={16} type="lucide" />
            </span>
          )}
          <span className="truncate text-14 font-semibold text-primary">{nama}</span>
          <span className="shrink-0 rounded-control bg-layer-3 px-2 py-0.5 text-11 text-tertiary">
            {t("wiki_ui.folder.material_count", { count: total })}
          </span>
        </button>
        {inputBerkas}
        {terbuka && <TombolUnggah unggahan={unggahan} ringkas namaTopik={nama} />}
        <Link
          to={`/${konteks.workspaceSlug}/wiki/${topik.id}`}
          title={t("wiki_ui.folder.open_topic")}
          aria-label={t("wiki_ui.folder.open_topic")}
          className={cn(getButtonStyling("ghost", "base"), "shrink-0")}
        >
          <span className="hidden sm:inline">{t("wiki_ui.folder.open_topic")}</span>
          <ArrowUpRight className="size-3.5" />
        </Link>
      </div>

      {terbuka && (
        <div id={idIsi} className="space-y-4 border-t border-subtle px-4 py-4">
          {sedangMemuat ? (
            <GridKartu>
              <KartuKerangka />
            </GridKartu>
          ) : materi.length > 0 ? (
            <GridMateri konteks={konteks} materi={materi} muatUlang={muatUlang} />
          ) : (
            anak.length === 0 && <p className="text-12 text-tertiary">{t("wiki_ui.folder.subtopic_empty")}</p>
          )}
          {anak.map((s) => (
            <SeksiSubtopik key={s.id} konteks={konteks} topik={s} kedalaman={kedalaman + 1} />
          ))}
        </div>
      )}
    </section>
  );
});
