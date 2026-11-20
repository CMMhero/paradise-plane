/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: editor folder Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Lock, X } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Avatar } from "@plane/ui";
import { getFileURL } from "@plane/utils";
// components
import { MemberDropdown } from "@/components/dropdowns/member/dropdown";
// hooks
import { useKonfirmasi } from "@/hooks/use-konfirmasi";
import { useMember } from "@/hooks/store/use-member";
// services
import type { TWikiFolder } from "@/services/wiki.service";
// local imports
import { layananWiki } from "./data";

type TProps = {
  workspaceSlug: string;
  folder: TWikiFolder;
  /** Folder yang daftar editornya berlaku di sini, kalau bukan folder ini sendiri. */
  pembatas?: TWikiFolder;
  onBerubah: () => void | Promise<unknown>;
};

/**
 * Siapa yang boleh menambah dan mengubah isi folder. Hanya admin Wiki yang
 * melihat bagian ini; server menolak yang lain. Pilihan langsung berlaku, tidak
 * menunggu tombol Simpan di formulir folder.
 */
export const EditorFolder = observer(function EditorFolder({ workspaceSlug, folder, pembatas, onBerubah }: TProps) {
  const { t } = useTranslation();
  const { minta, dialog } = useKonfirmasi();
  const {
    workspace: { workspaceMemberIds },
  } = useMember();
  const [sedangTambah, setSedangTambah] = useState(false);

  const editor = folder.editors ?? [];
  const sudah = new Set(editor.map((e) => e.id));
  const pilihan = (workspaceMemberIds ?? []).filter((id) => !sudah.has(id));
  const diwarisi = !editor.length && pembatas && pembatas.id !== folder.id ? pembatas : undefined;

  const galat = (error: unknown, cadangan: string) =>
    setToast({
      type: TOAST_TYPE.ERROR,
      title: t("wiki_ui.common.failed"),
      message: (error as { error?: string })?.error || cadangan,
    });

  const tambah = async (userId: string | null) => {
    if (!userId || sedangTambah) return;
    setSedangTambah(true);
    try {
      await layananWiki.addFolderEditor(workspaceSlug, folder.id, userId);
      await onBerubah();
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("wiki_editor.added_title") });
    } catch (error) {
      galat(error, t("wiki_editor.add_failed"));
    } finally {
      setSedangTambah(false);
    }
  };

  const hapus = async (userId: string) => {
    try {
      await layananWiki.removeFolderEditor(workspaceSlug, folder.id, userId);
      await onBerubah();
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("wiki_editor.removed_title") });
    } catch (error) {
      galat(error, t("wiki_editor.remove_failed"));
    }
  };

  return (
    <div className="space-y-3">
      <div>
        <h3 className="flex items-center gap-1.5 text-12 font-medium text-secondary">
          <Lock className="size-3.5" />
          {t("wiki_editor.section_title")}
        </h3>
        <p className="mt-1 text-12 text-tertiary">{t("wiki_editor.section_note")}</p>
        {diwarisi && (
          <p className="mt-1 text-12 text-tertiary">{t("wiki_editor.inherited_note", { name: diwarisi.nama })}</p>
        )}
      </div>

      {editor.length === 0 && !diwarisi && <p className="text-12 text-tertiary">{t("wiki_editor.empty")}</p>}
      {editor.length > 0 && (
        <ul className="divide-y divide-subtle rounded-card border border-subtle">
          {editor.map((e) => (
            <li key={e.id} className="flex items-center gap-2 px-3 py-2">
              <Avatar name={e.display_name} src={getFileURL(e.avatar_url ?? "")} size="md" />
              <span className="min-w-0 flex-1 truncate text-13 text-primary">{e.display_name}</span>
              <button
                type="button"
                aria-label={`${t("wiki_editor.remove_button")}: ${e.display_name}`}
                className="grid size-7 place-items-center rounded-button text-tertiary hover:bg-layer-2 hover:text-primary"
                onClick={() =>
                  minta(
                    {
                      judul: t("wiki_editor.remove_confirm_title"),
                      isi: t(editor.length === 1 ? "wiki_editor.remove_last_confirm" : "wiki_editor.remove_confirm", {
                        name: e.display_name,
                        folder: folder.nama,
                      }),
                      tombol: t("wiki_editor.remove_button"),
                      tombolProses: t("wiki_editor.removing"),
                    },
                    () => hapus(e.id)
                  )
                }
              >
                <X className="size-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="flex items-center gap-2">
        <span className="text-12 text-secondary">{t("wiki_editor.add_label")}</span>
        <MemberDropdown
          multiple={false}
          value={null}
          memberIds={pilihan}
          onChange={(id) => void tambah(id)}
          disabled={sedangTambah}
          placeholder={t("wiki_editor.add_placeholder")}
          buttonVariant="border-with-text"
          placement="bottom-start"
        />
      </div>
      {dialog}
    </div>
  );
});
