/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kelola folder Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { Trash2 } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { EmojiIconPickerTypes, EmojiPicker, Logo } from "@plane/propel/emoji-icon-picker";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TLogoProps } from "@plane/types";
import { EModalPosition, EModalWidth, Input, ModalCore, TextArea } from "@plane/ui";
// hooks
import { useKonfirmasi } from "@/hooks/use-konfirmasi";
// services
import type { TWikiFolder, TWikiFolderUpdate } from "@/services/wiki.service";
// local imports
import { adalahUnit, layananWiki } from "./data";

type TProps = {
  workspaceSlug: string;
  folder: TWikiFolder;
  isOpen: boolean;
  onClose: () => void;
  /** Dipanggil sesudah ada yang berubah, supaya pemanggilnya memuat ulang. */
  onBerubah: () => void | Promise<unknown>;
  /** Dipanggil sesudah folder benar-benar dihapus. */
  onTerhapus: () => void;
};

/**
 * Satu tempat untuk mengurus sebuah folder Wiki: nama, ikon, keterangan, dan menghapusnya.
 *
 * Semua isian ditampung dulu dan baru dikirim saat Simpan, jadi Batal benar-benar
 * membatalkan. Hapus, Batal, dan Simpan satu baris di bawah; Hapus meminta
 * konfirmasi lewat dialog yang sama dengan hapus di tempat lain di Wiki.
 *
 * Folder unit (divisi atau departemen) mengikuti struktur organisasi God Mode:
 * namanya tidak bisa diganti dan folder itu tidak bisa diarsipkan atau dihapus
 * dari sini. Yang tetap bisa diubah admin hanya ikon dan keterangannya. Siapa
 * yang boleh mengunggah diturunkan server dari penempatan di God Mode.
 */
export function KelolaFolder({ workspaceSlug, folder, isOpen, onClose, onBerubah, onTerhapus }: TProps) {
  const { t } = useTranslation();
  const { minta, dialog } = useKonfirmasi();
  const [nama, setNama] = useState(folder.nama);
  const [keterangan, setKeterangan] = useState(folder.keterangan ?? "");
  const [logo, setLogo] = useState<TLogoProps | null>(folder.logo_props ?? null);
  const [umum, setUmum] = useState(folder.umum);
  const [sedangSimpan, setSedangSimpan] = useState(false);
  const [ikonTerbuka, setIkonTerbuka] = useState(false);

  const unit = adalahUnit(folder);
  // `umum` hanya berlaku untuk folder tingkat atas yang bukan unit.
  const bisaUmum = !unit && !folder.parent_id;

  const galat = (error: unknown, cadangan: string) =>
    setToast({
      type: TOAST_TYPE.ERROR,
      title: t("wiki_ui.common.failed"),
      message: (error as { error?: string })?.error || cadangan,
    });

  const namaBersih = nama.trim();
  const keteranganBersih = keterangan.trim();

  // Hanya yang benar-benar berubah yang dikirim.
  const perubahan: TWikiFolderUpdate = {};
  if (!unit && namaBersih !== folder.nama) perubahan.nama = namaBersih;
  if (keteranganBersih !== (folder.keterangan ?? "").trim()) perubahan.keterangan = keteranganBersih;
  if (logo !== (folder.logo_props ?? null)) perubahan.logo_props = logo ?? undefined;
  if (bisaUmum && umum !== folder.umum) perubahan.umum = umum;
  const adaPerubahan = Object.keys(perubahan).length > 0;
  const namaKosong = !unit && !namaBersih;

  const gantiIkon = (nilai: {
    type: (typeof EmojiIconPickerTypes)[keyof typeof EmojiIconPickerTypes];
    value: unknown;
  }) => {
    const isi = nilai.type === EmojiIconPickerTypes.EMOJI ? { value: nilai.value, url: undefined } : nilai.value;
    setLogo({ in_use: nilai.type, [nilai.type]: isi } as TLogoProps);
  };

  const simpan = async () => {
    if (sedangSimpan || namaKosong) return;
    if (!adaPerubahan) {
      onClose();
      return;
    }
    setSedangSimpan(true);
    try {
      await layananWiki.updateFolder(workspaceSlug, folder.id, perubahan);
      await onBerubah();
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("wiki_ui.manage.saved_title") });
      onClose();
    } catch (error) {
      galat(error, t("wiki_ui.common.try_again"));
    } finally {
      setSedangSimpan(false);
    }
  };

  const hapus = async () => {
    let diarsipkan = false;
    try {
      // Dua langkah: server mewajibkan folder diarsipkan dulu, dan menolak
      // menghapus folder yang masih berisi (409). Kalau langkah kedua gagal,
      // arsipnya dibatalkan supaya folder tidak hilang diam-diam dari daftar.
      await layananWiki.archiveFolder(workspaceSlug, folder.id);
      diarsipkan = true;
      await layananWiki.deleteFolder(workspaceSlug, folder.id);
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("wiki_ui.manage.deleted_title"), message: folder.nama });
      onTerhapus();
    } catch (error) {
      if (diarsipkan) await layananWiki.unarchiveFolder(workspaceSlug, folder.id).catch(() => undefined);
      galat(error, t("wiki_ui.manage.delete_failed"));
    }
  };

  return (
    <>
      <ModalCore isOpen={isOpen} handleClose={onClose} position={EModalPosition.CENTER} width={EModalWidth.XXL}>
        <div className="space-y-6 p-6">
          <div>
            <h2 className="text-16 font-semibold text-primary">{t("wiki_ui.manage.title")}</h2>
            <p className="mt-1 text-12 text-tertiary">{t("wiki_ui.manage.subtitle")}</p>
          </div>

          {/* Nama dan ikon */}
          <div className="space-y-2">
            <label htmlFor="wiki-nama-folder" className="text-12 font-medium text-secondary">
              {t("wiki_ui.manage.name_and_icon")}
            </label>
            <div className="flex items-center gap-2">
              <EmojiPicker
                isOpen={ikonTerbuka}
                handleToggle={setIkonTerbuka}
                closeOnSelect
                label={
                  <span className="grid size-9 shrink-0 place-items-center rounded-item border border-subtle bg-layer-2">
                    {logo?.in_use ? (
                      <Logo logo={logo} size={18} type="lucide" />
                    ) : (
                      <span className="text-12 text-tertiary">{t("wiki_ui.manage.icon")}</span>
                    )}
                  </span>
                }
                onChange={gantiIkon}
                defaultOpen={EmojiIconPickerTypes.EMOJI}
              />
              <Input
                id="wiki-nama-folder"
                type="text"
                value={nama}
                disabled={unit}
                onChange={(e) => setNama(e.target.value)}
                className="flex-1 border border-subtle text-primary focus:border-accent-strong"
              />
            </div>
            {unit && <p className="text-12 text-tertiary">{t("wiki_ui.manage.unit_name_note")}</p>}
          </div>

          {/* Keterangan */}
          <div className="space-y-2">
            <label htmlFor="wiki-keterangan-folder" className="text-12 font-medium text-secondary">
              {t("wiki_ui.manage.description")}
            </label>
            <TextArea
              id="wiki-keterangan-folder"
              value={keterangan}
              onChange={(e) => setKeterangan(e.target.value)}
              className="min-h-20 text-primary"
            />
          </div>

          {/* Folder umum */}
          {bisaUmum && (
            <label className="flex items-center gap-2 text-13 text-secondary">
              <input type="checkbox" checked={umum} onChange={(e) => setUmum(e.target.checked)} className="size-4" />
              {t("wiki_ui.manage.open_upload")}
            </label>
          )}

          {/* Satu baris: Hapus di kiri, Batal dan Simpan di kanan. */}
          <div className="flex items-center justify-between gap-2 border-t border-subtle pt-4">
            {unit ? (
              <span />
            ) : (
              <Button
                variant="error-outline"
                size="sm"
                disabled={sedangSimpan}
                onClick={() =>
                  minta(
                    {
                      judul: t("wiki_ui.folder.confirm_delete_title"),
                      isi: t("wiki_ui.manage.confirm_delete", { name: folder.nama }),
                    },
                    hapus
                  )
                }
              >
                <Trash2 className="size-3.5" />
                {t("wiki_ui.manage.delete_folder")}
              </Button>
            )}
            <div className="flex items-center gap-2">
              <Button variant="secondary" size="sm" onClick={onClose} disabled={sedangSimpan}>
                {t("cancel")}
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => void simpan()}
                loading={sedangSimpan}
                disabled={!adaPerubahan || namaKosong}
              >
                {t("save")}
              </Button>
            </div>
          </div>
        </div>
      </ModalCore>
      {dialog}
    </>
  );
}
