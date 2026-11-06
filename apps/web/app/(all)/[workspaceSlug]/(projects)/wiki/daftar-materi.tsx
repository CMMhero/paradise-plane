/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: daftar materi Wiki + sub-topik yang bisa dibuka-tutup
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useId, useRef, useState } from "react";
import type { DragEvent, ReactNode } from "react";
import { observer } from "mobx-react";
import { BookOpen, ChevronRight, Folder, MoveRight, Pencil, Trash2, Upload } from "lucide-react";
import useSWR, { useSWRConfig } from "swr";
import { useTranslation } from "@plane/i18n";
import { Logo } from "@plane/propel/emoji-icon-picker";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { cn, renderFormattedDate } from "@plane/utils";
// components
import { gradienUntuk } from "@/components/wiki/gradien";
import { GridKartu, KartuKerangka, KartuMateri } from "@/components/wiki/kartu";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useKonfirmasi } from "@/hooks/use-konfirmasi";
import useLocalStorage from "@/hooks/use-local-storage";
// services
import type { TWikiFolder, TWikiMaterialList } from "@/services/wiki.service";
// local imports
import { AksiFolder } from "./aksi-folder";
import { GantiNamaMateri } from "./ganti-nama";
import { UbinTambahSubtopik, bolehTambahSubtopik, useBuatSubtopik } from "./buat-subtopik";
import { HalamanDepartemen } from "./halaman-departemen";
import {
  TIPE_SERET_MATERI,
  adalahUnit,
  anakDari,
  jumlahMateriDalam,
  labelTipe,
  layananWiki,
  ukuranTerbaca,
  type TSeretMateri,
} from "./data";

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
  const { mutate: segarkan } = useSWRConfig();
  const topikId = topik?.id;
  const { data, isLoading, mutate } = useSWR(
    aktif && topikId ? kunciMateriTopik(topikId) : null,
    topikId ? () => layananWiki.fetchMaterials(workspaceSlug, topikId) : null
  );
  const berkasRef = useRef<HTMLInputElement>(null);
  // Hitungan, bukan boolean: berkas yang dilepas saat unggahan lain masih jalan
  // masuk antrean, dan indikator baru padam sesudah antreannya habis.
  const [jumlahBerjalan, setJumlahBerjalan] = useState(0);
  const antrean = useRef<Promise<void>>(Promise.resolve());
  const sedangUnggah = jumlahBerjalan > 0;

  const prosesUnggah = async (files: File[]) => {
    if (!topikId || !files.length) return;
    let berhasil = 0;
    // Sengaja berurutan, bukan Promise.all. Satu berkas di sini boleh 500 MB;
    // mengunggah sepuluh sekaligus menghabiskan jalur WiFi kantor dan membuat
    // semuanya gagal berbarengan alih-alih selesai satu per satu.
    for (const file of files) {
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
    if (berhasil > 0) {
      await Promise.all([mutate(), onJumlahBerubah()]);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("wiki_ui.folder.uploaded_title"),
        message: t("wiki_ui.folder.uploaded_message", { count: berhasil, folder: topik?.nama ?? "" }),
      });
    }
  };

  /** Satu pintu untuk tombol unggah dan seret-lepas: berkas diantre, lalu diunggah satu per satu. */
  const unggah = (files: File[]) => {
    if (!files.length) return;
    setJumlahBerjalan((n) => n + 1);
    antrean.current = antrean.current
      .then(() => prosesUnggah(files))
      .catch(() => undefined)
      .finally(() => setJumlahBerjalan((n) => n - 1));
  };

  const inputBerkas = (
    <input
      ref={berkasRef}
      type="file"
      multiple
      className="hidden"
      onChange={(e) => {
        // Salin dulu: mengosongkan input juga mengosongkan FileList-nya.
        const dipilih = Array.from(e.target.files ?? []);
        e.target.value = "";
        unggah(dipilih);
      }}
    />
  );

  // Seksi yang ditutup belum memuat daftarnya, jadi izinnya dipinjam dari pohon
  // (angka yang sama dari server) supaya seksi tertutup tetap bisa jadi sasaran lepas.
  const bolehUnggah = data?.can_upload ?? !!topik?.can_upload;
  const unggahan: TUnggah = {
    bolehUnggah,
    sedangUnggah,
    pilihBerkas: () => berkasRef.current?.click(),
  };

  /** Pindahkan materi yang diseret dari folder lain ke topik ini. Server menilai hak dua sisi. */
  const pindahkan = async (materi: TSeretMateri) => {
    if (!topikId || materi.folderId === topikId) return;
    try {
      await layananWiki.moveMaterial(workspaceSlug, materi.id, topikId);
      // Folder asal dan tujuan sama-sama berubah, dan keduanya bisa sedang tampil.
      await Promise.all([
        segarkan((k) => typeof k === "string" && k.startsWith("WIKI_MATERIALS_")),
        onJumlahBerubah(),
      ]);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("wiki_ui.folder.moved_title"),
        message: t("wiki_ui.folder.moved_message", { title: materi.judul, folder: topik?.nama ?? "" }),
      });
    } catch (error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("wiki_ui.folder.move_failed_title"),
        message: (error as { error?: string })?.error || t("wiki_ui.common.try_again"),
      });
    }
  };

  const lepas: TLepas = {
    bolehUnggah,
    namaTopik: topik?.nama ?? "",
    folderId: topikId,
    terima: (files) => unggah(files),
    pindah: (materi) => void pindahkan(materi),
  };

  return { daftar: data, sedangMemuat: isLoading, muatUlang: mutate, inputBerkas, unggahan, lepas };
}

type TLepas = {
  /** Hak unggah di topik ini; sama dengan hak menerima materi pindahan. */
  bolehUnggah: boolean;
  namaTopik: string;
  folderId?: string;
  terima: (files: File[]) => void;
  /** Materi dari folder lain dilepas di sini. */
  pindah: (materi: TSeretMateri) => void;
};

type TJenisSeret = "berkas" | "materi";

/** Berkas dari komputer, atau kartu materi dari halaman ini. null = seretan lain (teks, tautan). */
const jenisSeret = (e: DragEvent<HTMLElement>): TJenisSeret | null => {
  const tipe = new Set(e.dataTransfer.types);
  if (tipe.has(TIPE_SERET_MATERI)) return "materi";
  if (tipe.has("Files")) return "berkas";
  return null;
};

/** true bila ini seretan yang kita kenal dan sudah kita ambil alih. Event lain dibiarkan. */
const tangani = (e: DragEvent<HTMLElement>): TJenisSeret | null => {
  const jenis = jenisSeret(e);
  if (!jenis) return null;
  // Wajib: tanpa ini peramban membuka berkasnya di tab ini dan halaman hilang.
  e.preventDefault();
  e.stopPropagation();
  return jenis;
};

const bacaSeretanMateri = (dt: DataTransfer): TSeretMateri | null => {
  try {
    const mentah = JSON.parse(dt.getData(TIPE_SERET_MATERI)) as Partial<TSeretMateri>;
    return typeof mentah.id === "string" && typeof mentah.folderId === "string"
      ? { id: mentah.id, folderId: mentah.folderId, judul: String(mentah.judul ?? "") }
      : null;
  } catch {
    return null;
  }
};

/**
 * Berkas dari drop. Folder dibuang dan dihitung: peramban tidak bisa membaca
 * isi folder lewat `DataTransfer.files` (hasilnya satu "berkas" kosong tanpa
 * tipe), dan mengunggahnya menghasilkan galat yang membingungkan.
 */
const berkasDariDrop = (dt: DataTransfer): { files: File[]; folderDilewati: number } => {
  const files: File[] = [];
  let folderDilewati = 0;
  const item = Array.from(dt.items ?? []);
  if (item.length > 0 && typeof item[0]?.webkitGetAsEntry === "function") {
    for (const i of item) {
      if (i.kind !== "file") continue;
      if (i.webkitGetAsEntry()?.isDirectory) {
        folderDilewati += 1;
        continue;
      }
      const f = i.getAsFile();
      if (f) files.push(f);
    }
    return { files, folderDilewati };
  }
  return { files: Array.from(dt.files), folderDilewati };
};

/**
 * Area seret-lepas satu topik. Berkas yang dilepas diunggah ke topik ini lewat
 * jalur yang sama dengan tombol unggah, jadi izin, antrean, dan galat per
 * berkas tidak punya cabang kedua.
 *
 * Area bisa bersarang (seksi sub-topik di dalam seksi induknya). Tiap area
 * menghentikan perambatan event drag, jadi yang tertimpa hanya area paling
 * dalam, dan hitungan masuk-keluar per area tetap benar.
 */
export function ZonaLepas({ lepas, className, children }: { lepas: TLepas; className?: string; children: ReactNode }) {
  const { t } = useTranslation();
  // Hitungan, bukan boolean: dragenter/dragleave menyala untuk tiap elemen anak.
  const [masuk, setMasuk] = useState(0);
  const [jenis, setJenis] = useState<TJenisSeret>("berkas");
  // Materi yang diseret dari folder ini sendiri bukan sasaran di sini: tidak ada yang berubah.
  const sedangSeret = masuk > 0 && lepas.bolehUnggah;

  return (
    <div
      className={cn("relative", className)}
      onDragEnter={(e) => {
        const j = tangani(e);
        if (!j) return;
        setJenis(j);
        setMasuk((n) => n + 1);
      }}
      onDragOver={(e) => {
        const j = tangani(e);
        if (j) e.dataTransfer.dropEffect = lepas.bolehUnggah ? (j === "materi" ? "move" : "copy") : "none";
      }}
      onDragLeave={(e) => {
        if (tangani(e)) setMasuk((n) => Math.max(0, n - 1));
      }}
      onDrop={(e) => {
        const j = tangani(e);
        if (!j) return;
        setMasuk(0);
        if (!lepas.bolehUnggah) {
          setToast({ type: TOAST_TYPE.ERROR, title: t("wiki_ui.folder.drop_forbidden") });
          return;
        }
        if (j === "materi") {
          const materi = bacaSeretanMateri(e.dataTransfer);
          if (materi && materi.folderId !== lepas.folderId) lepas.pindah(materi);
          return;
        }
        const { files, folderDilewati } = berkasDariDrop(e.dataTransfer);
        if (folderDilewati > 0) setToast({ type: TOAST_TYPE.INFO, title: t("wiki_ui.folder.drop_folders_skipped") });
        lepas.terima(files);
      }}
    >
      {children}
      {sedangSeret && (
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 z-20 grid place-items-center rounded-card border-2 border-dashed border-accent-strong bg-accent-subtle/80 backdrop-blur-[1px]"
        >
          <div className="flex items-center gap-2 rounded-card bg-surface-1 px-4 py-2 text-13 font-medium text-primary shadow-raised-100">
            {jenis === "materi" ? (
              <MoveRight className="size-4 text-accent-primary" />
            ) : (
              <Upload className="size-4 text-accent-primary" />
            )}
            {t(jenis === "materi" ? "wiki_ui.folder.drop_move_here" : "wiki_ui.folder.drop_here", {
              folder: lepas.namaTopik,
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Isi kosong sebuah topik. Yang boleh mengunggah mendapat area seret-lepas yang
 * juga bisa diklik; yang tidak, cukup keterangan. Dipakai di SEMUA halaman Wiki
 * (divisi, departemen, folder, sub-topik) supaya tak ada halaman kosong tanpa
 * jalan masuk untuk materi pertama.
 */
export function ZonaKosong({ unggahan, ringkas }: { unggahan: TUnggah; ringkas?: boolean }) {
  const { t } = useTranslation();
  // Versi ringkas = penanda lepas yang SELALU ada di bawah daftar materi, supaya
  // menambah berkas tidak bergantung pada daftarnya kosong. Orang tanpa hak
  // unggah tidak melihat apa-apa di sana.
  if (ringkas && !unggahan.bolehUnggah) return null;
  if (ringkas)
    return (
      <button
        type="button"
        onClick={unggahan.pilihBerkas}
        disabled={unggahan.sedangUnggah}
        className="flex w-full items-center justify-center gap-2 rounded-card border-2 border-dashed border-subtle px-4 py-3 text-center transition-colors hover:border-accent-strong hover:bg-accent-subtle focus-visible:border-accent-strong focus-visible:bg-accent-subtle disabled:cursor-progress disabled:opacity-70"
      >
        <Upload className="size-4 shrink-0 text-tertiary" />
        <span className="text-13 font-medium text-secondary">{t("wiki_ui.folder.drop_empty_title")}</span>
        <span className="hidden text-12 text-tertiary sm:inline">{t("wiki_ui.folder.drop_empty_hint")}</span>
      </button>
    );
  if (!unggahan.bolehUnggah)
    return (
      <div className="rounded-card border border-dashed border-subtle px-6 py-10 text-center">
        <p className="text-14 font-medium text-secondary">{t("wiki_ui.folder.empty_title")}</p>
        <p className="mt-1 text-12 text-tertiary">{t("wiki_ui.folder.empty_cannot_upload")}</p>
      </div>
    );
  return (
    <button
      type="button"
      onClick={unggahan.pilihBerkas}
      disabled={unggahan.sedangUnggah}
      className="flex w-full flex-col items-center gap-1 rounded-card border-2 border-dashed border-strong px-6 py-10 text-center transition-colors hover:border-accent-strong hover:bg-accent-subtle focus-visible:border-accent-strong focus-visible:bg-accent-subtle disabled:cursor-progress disabled:opacity-70"
    >
      <span className="mb-1 grid size-10 place-items-center rounded-card bg-layer-3 text-tertiary">
        <Upload className="size-5" />
      </span>
      <span className="text-14 font-medium text-primary">{t("wiki_ui.folder.drop_empty_title")}</span>
      <span className="text-12 text-secondary">{t("wiki_ui.folder.drop_empty_hint")}</span>
      <span className="mt-2 max-w-xl text-11 text-tertiary">{t("wiki_ui.folder.empty_can_upload")}</span>
    </button>
  );
}

/**
 * Kerangka halaman yang bisa menerima unggahan: area seret-lepas seluas halaman
 * dan area gulir. Tidak ada tombol unggah terpisah; ajakan unggah ada di dalam
 * daftar materi (`ZonaKosong`). Folder dan tab materi departemen memakai ini,
 * jadi perilakunya tidak punya dua versi.
 */
export function KerangkaUnggah({
  lepas,
  inputBerkas,
  children,
}: {
  lepas: TLepas;
  inputBerkas: ReactNode;
  children: ReactNode;
}) {
  return (
    <ZonaLepas lepas={lepas} className="flex h-full w-full flex-col">
      {inputBerkas}
      <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
    </ZonaLepas>
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
            // Seret = pindah folder. Hanya yang berhak mengubah materi ini; tujuannya
            // dinilai lagi oleh server (hak unggah di folder tujuan).
            onSeretMulai={
              m.can_manage
                ? (e) => {
                    const muatan: TSeretMateri = { id: m.id, folderId: m.folder_id, judul: m.judul };
                    e.dataTransfer.setData(TIPE_SERET_MATERI, JSON.stringify(muatan));
                    e.dataTransfer.effectAllowed = "move";
                  }
                : undefined
            }
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
 * Divisi/departemen atau sub-topik sebagai seksi yang bisa dibuka-tutup, langsung
 * di halaman induknya.
 *
 * Dulu sub-topik tampil sebagai kartu yang harus diklik dulu untuk melihat
 * isinya, jadi satu berkas di sub-topik butuh dua klik plus satu halaman
 * tambahan. Sekarang materinya terlihat di tempat. Halaman sub-topik sendiri
 * tetap ada (menu "Buka") untuk mengelola atau membagikan alamatnya.
 *
 * Dua rupa, dan keduanya sama di mana pun seksinya tampil (halaman divisi,
 * halaman departemen, tab Materials):
 * - unit (departemen): kartu dengan ubin gradien, nama besar, dan ringkasan isi.
 * - sub-topik: kartu lebih ringan dengan ubin folder polos.
 * Sub-topik hanya satu tingkat, jadi sub-topik selalu duduk di dalam kartu unitnya
 * atau langsung di halaman, tidak pernah di dalam sub-topik lain.
 *
 * Materinya baru diambil saat seksinya terbuka, jadi seksi yang ditutup orang
 * tidak memakan permintaan.
 */
export const SeksiSubtopik = observer(function SeksiSubtopik({
  konteks,
  topik,
}: {
  konteks: TKonteks;
  topik: TWikiFolder;
}) {
  const { t } = useTranslation();
  const idIsi = useId();
  const { storedValue: tertutup, setValue: setTertutup } = useLocalStorage<string[]>(KUNCI_TERTUTUP, TIDAK_ADA);
  const idTopik = topik.id;
  const terbuka = !(tertutup ?? TIDAK_ADA).includes(idTopik);
  const { daftar, sedangMemuat, muatUlang, inputBerkas, unggahan, lepas } = useMateriTopik(konteks, topik, terbuka);
  const {
    buat: buatSubtopik,
    sedangMembuat: sedangMembuatSub,
    dialog: dialogSubtopik,
  } = useBuatSubtopik(konteks.workspaceSlug, konteks.onJumlahBerubah);

  const nama = topik.nama;
  const unit = adalahUnit(topik);
  const bisaTambahSub = bolehTambahSubtopik(topik);
  const anak = anakDari(konteks.folder, topik.id);
  const total = jumlahMateriDalam(konteks.folder, topik.id);
  const materi = daftar?.materials ?? [];

  const alihkan = () => {
    const sekarang = tertutup ?? TIDAK_ADA;
    setTertutup(terbuka ? [...sekarang, idTopik] : sekarang.filter((id) => id !== idTopik));
  };

  // Seksi tertutup pun jadi sasaran lepas: izinnya dipinjam dari pohon folder.
  return (
    <ZonaLepas lepas={lepas}>
      <section
        className={cn(
          "overflow-hidden rounded-card border border-subtle",
          unit ? "bg-surface-1 shadow-raised-100" : "bg-layer-1"
        )}
      >
        <div className={cn("flex items-center gap-2 px-3", unit ? "py-3" : "py-2")}>
          <button
            type="button"
            onClick={alihkan}
            aria-expanded={terbuka}
            aria-controls={idIsi}
            aria-label={t(terbuka ? "wiki_ui.folder.collapse_named" : "wiki_ui.folder.expand_named", { name: nama })}
            className="flex min-w-0 flex-1 items-center gap-3 rounded-item px-1 py-1 text-left transition-colors hover:bg-layer-1-hover focus-visible:bg-layer-1-hover"
          >
            <ChevronRight
              className={cn("size-4 shrink-0 text-tertiary transition-transform duration-150", terbuka && "rotate-90")}
            />
            <UbinSeksi topik={topik} unit={unit} />
            <span className="min-w-0">
              <span className={cn("block truncate font-semibold text-primary", unit ? "text-14" : "text-13")}>
                {nama}
              </span>
              {unit && (
                <span className="block truncate text-12 text-tertiary">
                  {[
                    t("wiki_ui.folder.material_count", { count: total }),
                    anak.length > 0 ? t("wiki_ui.folder.subtopic_count", { count: anak.length }) : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              )}
            </span>
            {!unit && (
              <span className="shrink-0 rounded-control bg-layer-3 px-2 py-0.5 text-11 text-tertiary">
                {t("wiki_ui.folder.material_count", { count: total })}
              </span>
            )}
          </button>
          {inputBerkas}
          {/* Buka, ubah, hapus dikumpulkan di satu menu supaya baris tidak penuh tombol.
              Izinnya `can_manage` dari server, sama seperti kartu folder. */}
          <AksiFolder
            varian="menu"
            workspaceSlug={konteks.workspaceSlug}
            folder={topik}
            onBerubah={konteks.onJumlahBerubah}
          />
        </div>

        {terbuka && (
          <div id={idIsi} className={cn("space-y-5 border-t border-subtle", unit ? "px-4 py-4" : "px-3 py-3")}>
            {sedangMemuat ? (
              <GridKartu>
                <KartuKerangka />
              </GridKartu>
            ) : materi.length > 0 ? (
              <div className="space-y-3">
                <GridMateri konteks={konteks} materi={materi} muatUlang={muatUlang} />
                <ZonaKosong unggahan={unggahan} ringkas />
              </div>
            ) : unggahan.bolehUnggah ? (
              <ZonaKosong unggahan={unggahan} ringkas />
            ) : (
              <p className="text-12 text-tertiary">{t("wiki_ui.folder.subtopic_empty")}</p>
            )}
            {/* Urutan sama dengan halaman foldernya: materi, sub-topik, lalu halaman. */}
            {(anak.length > 0 || bisaTambahSub) && (
              <div className="space-y-2.5">
                <div className="flex items-baseline gap-2">
                  <h3 className="text-13 font-semibold text-secondary">{t("wiki_ui.folder.subtopics_title")}</h3>
                  {anak.length > 0 && (
                    <span className="rounded-control bg-layer-3 px-2 py-0.5 text-11 text-tertiary">{anak.length}</span>
                  )}
                </div>
                {anak.map((s) => (
                  <SeksiSubtopik key={s.id} konteks={konteks} topik={s} />
                ))}
                {/* Sub-topik hanya satu tingkat, jadi ubin ini tidak ada di dalam sub-topik. */}
                {bisaTambahSub && (
                  <UbinTambahSubtopik onClick={() => void buatSubtopik(topik.id)} loading={sedangMembuatSub} />
                )}
              </div>
            )}
            {/* Halaman project departemen ikut tampil di sini, jadi halaman divisi
                cukup satu layar tanpa membuka tiap departemen. */}
            {topik.departemen_id && (
              <HalamanDepartemen key={topik.id} workspaceSlug={konteks.workspaceSlug} folderId={topik.id} />
            )}
          </div>
        )}
      </section>
      {dialogSubtopik}
    </ZonaLepas>
  );
});

/** Ubin di depan nama seksi: gradien khas untuk unit, folder polos untuk sub-topik. */
function UbinSeksi({ topik, unit }: { topik: TWikiFolder; unit: boolean }) {
  const ikon = topik.logo_props?.in_use ? (
    <Logo logo={topik.logo_props} size={unit ? 18 : 14} type="lucide" />
  ) : unit ? (
    <BookOpen className="size-[18px]" strokeWidth={1.75} />
  ) : (
    <Folder className="size-3.5" strokeWidth={1.75} />
  );
  return unit ? (
    <span
      className="grid size-9 shrink-0 place-items-center rounded-item text-white"
      style={{ backgroundImage: gradienUntuk(topik.nama) }}
    >
      {ikon}
    </span>
  ) : (
    <span className="grid size-7 shrink-0 place-items-center rounded-item bg-layer-3 text-secondary">{ikon}</span>
  );
}
