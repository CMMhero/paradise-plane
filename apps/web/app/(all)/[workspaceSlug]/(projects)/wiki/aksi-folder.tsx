/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: aksi cepat di kartu folder Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { ArrowUpRight, MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { useNavigate } from "react-router";
import { useTranslation } from "@plane/i18n";
import { IconButton } from "@plane/propel/icon-button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { CustomMenu } from "@plane/ui";
// hooks
import { useKonfirmasi } from "@/hooks/use-konfirmasi";
// services
import type { TWikiFolder } from "@/services/wiki.service";
// local imports
import { adalahUnit, layananWiki } from "./data";
import { KelolaFolder } from "./kelola";

const KELAS_AKSI =
  "grid size-7 place-items-center rounded-button bg-black/25 text-white opacity-0 backdrop-blur-[1px] transition-opacity group-focus-within:opacity-100 group-hover:opacity-100 hover:bg-black/40 focus-visible:opacity-100 sentuh:size-9 sentuh:opacity-100";

type TProps = {
  workspaceSlug: string;
  folder: TWikiFolder;
  /**
   * `kartu`: pensil dan tong sampah melayang di atas sampul kartu, muncul saat disorot.
   * `menu`: satu tombol "..." di baris judul seksi (Buka, Ubah, Hapus), supaya baris
   * tidak penuh tombol kecil.
   */
  varian?: "kartu" | "menu";
  /** Dipanggil sesudah folder berubah atau terhapus, supaya pohonnya dimuat ulang. */
  onBerubah: () => void | Promise<unknown>;
};

/**
 * Ubah dan hapus folder tanpa membuka halamannya dulu.
 *
 * Folder unit (divisi atau departemen) ikut struktur God Mode: bisa diubah
 * (ikon dan keterangan) tetapi tidak pernah bisa dihapus, jadi aksi hapusnya
 * tidak ditampilkan. Aturan sebenarnya tetap dipegang server (`can_manage`).
 * Varian `menu` tetap menampilkan "Buka" untuk semua orang, karena itu bukan
 * aksi kelola.
 */
export function AksiFolder({ workspaceSlug, folder, onBerubah, varian = "kartu" }: TProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [kelolaTerbuka, setKelolaTerbuka] = useState(false);
  const { minta, dialog } = useKonfirmasi();

  const menu = varian === "menu";
  if (!folder.can_manage && !menu) return null;
  const bisaHapus = !adalahUnit(folder);

  const hapus = async () => {
    let diarsipkan = false;
    try {
      // Sama dengan KelolaFolder: server mewajibkan arsip dulu, dan menolak folder yang masih berisi.
      await layananWiki.archiveFolder(workspaceSlug, folder.id);
      diarsipkan = true;
      await layananWiki.deleteFolder(workspaceSlug, folder.id);
      await onBerubah();
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("wiki_ui.manage.deleted_title"), message: folder.nama });
    } catch (error) {
      if (diarsipkan) await layananWiki.unarchiveFolder(workspaceSlug, folder.id).catch(() => undefined);
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("wiki_ui.common.failed"),
        message: (error as { error?: string })?.error || t("wiki_ui.manage.delete_failed"),
      });
    }
  };

  const mintaHapus = () =>
    minta(
      {
        judul: t("wiki_ui.folder.confirm_delete_title"),
        isi: t("wiki_ui.manage.confirm_delete", { name: folder.nama }),
      },
      hapus
    );

  return (
    <>
      {menu ? (
        <CustomMenu
          ariaLabel={t("wiki_ui.folder.more_actions")}
          placement="bottom-end"
          closeOnSelect
          customButton={
            <IconButton
              icon={MoreHorizontal}
              variant="ghost"
              size="lg"
              aria-label={`${t("wiki_ui.folder.more_actions")}: ${folder.nama}`}
            />
          }
        >
          <CustomMenu.MenuItem
            onClick={() => void navigate(`/${workspaceSlug}/wiki/${folder.id}`)}
            className="flex items-center gap-2"
          >
            <ArrowUpRight className="size-3.5 shrink-0" />
            {t("wiki_ui.folder.open_topic")}
          </CustomMenu.MenuItem>
          {folder.can_manage && (
            <CustomMenu.MenuItem onClick={() => setKelolaTerbuka(true)} className="flex items-center gap-2">
              <Pencil className="size-3.5 shrink-0" />
              {t("wiki_ui.folder.manage")}
            </CustomMenu.MenuItem>
          )}
          {folder.can_manage && bisaHapus && (
            <CustomMenu.MenuItem onClick={mintaHapus} className="flex items-center gap-2 text-danger-primary">
              <Trash2 className="size-3.5 shrink-0" />
              {t("wiki_ui.manage.delete_folder")}
            </CustomMenu.MenuItem>
          )}
        </CustomMenu>
      ) : (
        <>
          <button
            type="button"
            title={t("wiki_ui.folder.manage")}
            aria-label={`${t("wiki_ui.folder.manage")}: ${folder.nama}`}
            onClick={() => setKelolaTerbuka(true)}
            className={KELAS_AKSI}
          >
            <Pencil className="size-3.5" />
          </button>
          {bisaHapus && (
            <button
              type="button"
              title={t("wiki_ui.manage.delete_folder")}
              aria-label={`${t("wiki_ui.manage.delete_folder")}: ${folder.nama}`}
              onClick={mintaHapus}
              className={KELAS_AKSI}
            >
              <Trash2 className="size-3.5" />
            </button>
          )}
        </>
      )}
      {dialog}
      {kelolaTerbuka && (
        <KelolaFolder
          workspaceSlug={workspaceSlug}
          folder={folder}
          isOpen={kelolaTerbuka}
          onClose={() => setKelolaTerbuka(false)}
          onBerubah={onBerubah}
          onTerhapus={() => {
            setKelolaTerbuka(false);
            void onBerubah();
          }}
        />
      )}
    </>
  );
}
