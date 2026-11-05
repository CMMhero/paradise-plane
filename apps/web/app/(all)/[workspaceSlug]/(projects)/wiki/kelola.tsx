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
// services
import type { TWikiFolder } from "@/services/wiki.service";
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
 * Folder unit (divisi atau departemen) mengikuti struktur organisasi God Mode:
 * namanya tidak bisa diganti dan folder itu tidak bisa diarsipkan atau dihapus
 * dari sini. Yang tetap bisa diubah admin hanya ikon dan keterangannya. Siapa
 * yang boleh mengunggah diturunkan server dari penempatan di God Mode.
 */
export function KelolaFolder({ workspaceSlug, folder, isOpen, onClose, onBerubah, onTerhapus }: TProps) {
  const { t } = useTranslation();
  const [nama, setNama] = useState(folder.nama);
  const [keterangan, setKeterangan] = useState(folder.keterangan ?? "");
  const [sedangSimpan, setSedangSimpan] = useState(false);
  const [sedangSimpanKeterangan, setSedangSimpanKeterangan] = useState(false);
  const [sedangHapus, setSedangHapus] = useState(false);
  const [konfirmasiHapus, setKonfirmasiHapus] = useState(false);
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

  const simpanNama = async () => {
    const bersih = nama.trim();
    if (!bersih || bersih === folder.nama) return;
    setSedangSimpan(true);
    try {
      await layananWiki.updateFolder(workspaceSlug, folder.id, { nama: bersih });
      await onBerubah();
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("wiki_ui.manage.renamed_title"), message: bersih });
    } catch (error) {
      galat(error, t("wiki_ui.manage.rename_failed"));
    } finally {
      setSedangSimpan(false);
    }
  };

  const simpanKeterangan = async () => {
    if (keterangan.trim() === (folder.keterangan ?? "").trim()) return;
    setSedangSimpanKeterangan(true);
    try {
      await layananWiki.updateFolder(workspaceSlug, folder.id, { keterangan: keterangan.trim() });
      await onBerubah();
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("wiki_ui.manage.saved_title") });
    } catch (error) {
      galat(error, t("wiki_ui.common.try_again"));
    } finally {
      setSedangSimpanKeterangan(false);
    }
  };

  const gantiUmum = async (nilai: boolean) => {
    try {
      await layananWiki.updateFolder(workspaceSlug, folder.id, { umum: nilai });
      await onBerubah();
    } catch (error) {
      galat(error, t("wiki_ui.common.try_again"));
    }
  };

  const gantiIkon = async (nilai: {
    type: (typeof EmojiIconPickerTypes)[keyof typeof EmojiIconPickerTypes];
    value: unknown;
  }) => {
    const isi = nilai.type === EmojiIconPickerTypes.EMOJI ? { value: nilai.value, url: undefined } : nilai.value;
    const logoProps = { in_use: nilai.type, [nilai.type]: isi } as TLogoProps;
    try {
      await layananWiki.updateFolder(workspaceSlug, folder.id, { logo_props: logoProps });
      await onBerubah();
    } catch (error) {
      galat(error, t("wiki_ui.manage.icon_failed"));
    }
  };

  const hapus = async () => {
    if (sedangHapus) return;
    setSedangHapus(true);
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
    } finally {
      setSedangHapus(false);
      setKonfirmasiHapus(false);
    }
  };

  return (
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
                  {folder.logo_props?.in_use ? (
                    <Logo logo={folder.logo_props} size={18} type="lucide" />
                  ) : (
                    <span className="text-12 text-tertiary">{t("wiki_ui.manage.icon")}</span>
                  )}
                </span>
              }
              onChange={(nilai) => void gantiIkon(nilai)}
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
            {!unit && (
              <Button variant="primary" size="sm" onClick={simpanNama} loading={sedangSimpan}>
                {t("save")}
              </Button>
            )}
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
          <Button variant="primary" size="sm" onClick={simpanKeterangan} loading={sedangSimpanKeterangan}>
            {t("save")}
          </Button>
        </div>

        {/* Folder umum */}
        {bisaUmum && (
          <label className="flex items-center gap-2 text-13 text-secondary">
            <input
              type="checkbox"
              checked={folder.umum}
              onChange={(e) => void gantiUmum(e.target.checked)}
              className="size-4"
            />
            {t("wiki_ui.manage.open_upload")}
          </label>
        )}

        {/* Hapus */}
        {!unit && (
          <div className="space-y-2 border-t border-subtle pt-4">
            {konfirmasiHapus ? (
              <div className="rounded-card border border-danger-strong bg-danger-subtle p-3">
                <p className="text-12 text-primary">{t("wiki_ui.manage.confirm_delete", { name: folder.nama })}</p>
                <div className="mt-3 flex gap-2">
                  <Button variant="error-fill" size="sm" onClick={hapus} loading={sedangHapus}>
                    {t("wiki_ui.manage.yes_delete")}
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => setKonfirmasiHapus(false)}>
                    {t("cancel")}
                  </Button>
                </div>
              </div>
            ) : (
              <Button variant="error-outline" size="sm" onClick={() => setKonfirmasiHapus(true)}>
                <Trash2 className="size-3.5" />
                {t("wiki_ui.manage.delete_folder")}
              </Button>
            )}
          </div>
        )}
      </div>
    </ModalCore>
  );
}
