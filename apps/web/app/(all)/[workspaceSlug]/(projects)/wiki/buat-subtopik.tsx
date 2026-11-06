/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: buat sub-topik Wiki
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import type { ReactNode } from "react";
import { Plus } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
// services
import type { TWikiFolder } from "@/services/wiki.service";
// local imports
import { bisaPunyaSubtopik, layananWiki } from "./data";
import { KelolaFolder } from "./kelola";

/**
 * Satu cara membuat sub-topik untuk semua tempat: halaman folder, seksi
 * departemen di halaman divisi, dan tab Materials project departemen.
 *
 * Folder baru langsung dibuka di dialog kelola supaya namanya bisa diisi saat
 * itu juga; tanpa itu orang mendapat "New topic" lalu harus mencari tombol ubah.
 * Izinnya `can_manage` induk dari server, yang menilai ulang saat membuat.
 */
export function useBuatSubtopik(
  workspaceSlug: string,
  onBerubah: () => Promise<unknown>
): { buat: (indukId: string) => Promise<void>; sedangMembuat: boolean; dialog: ReactNode } {
  const { t } = useTranslation();
  const [sedangMembuat, setSedangMembuat] = useState(false);
  const [baru, setBaru] = useState<TWikiFolder | null>(null);

  const buat = async (indukId: string) => {
    if (sedangMembuat) return;
    setSedangMembuat(true);
    try {
      const folder = await layananWiki.createFolder(workspaceSlug, {
        nama: t("wiki_ui.folder.new_topic_name"),
        parent_id: indukId,
      });
      await onBerubah();
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("wiki_ui.folder.subtopic_created_title") });
      setBaru(folder);
    } catch (error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("wiki_ui.common.failed"),
        message: (error as { error?: string })?.error || t("wiki_ui.folder.subtopic_failed_message"),
      });
    } finally {
      setSedangMembuat(false);
    }
  };

  const dialog = baru ? (
    <KelolaFolder
      key={baru.id}
      workspaceSlug={workspaceSlug}
      folder={baru}
      isOpen
      onClose={() => setBaru(null)}
      onBerubah={onBerubah}
      onTerhapus={() => {
        setBaru(null);
        void onBerubah();
      }}
    />
  ) : null;

  return { buat, sedangMembuat, dialog };
}

/**
 * Ubin "Add sub-topic" yang duduk di dalam daftar sub-topik, bukan tombol di
 * kepala halaman. Bentuknya sama dengan penanda lepas berkas di daftar materi
 * (`ZonaKosong`), jadi dua cara menambah isi itu terbaca sebagai satu keluarga.
 */
export function UbinTambahSubtopik({ onClick, loading }: { onClick: () => void; loading: boolean }) {
  const { t } = useTranslation();
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      className="flex w-full items-center justify-center gap-2 rounded-card border-2 border-dashed border-subtle px-4 py-3 text-center transition-colors hover:border-accent-strong hover:bg-accent-subtle focus-visible:border-accent-strong focus-visible:bg-accent-subtle disabled:cursor-progress disabled:opacity-70"
    >
      <Plus className="size-4 shrink-0 text-tertiary" />
      <span className="text-13 font-medium text-secondary">{t("wiki_ui.folder.add_subtopic")}</span>
    </button>
  );
}

/** Folder yang boleh ditambah sub-topiknya oleh orang ini: server menilai `can_manage`, strukturnya satu tingkat. */
export const bolehTambahSubtopik = (folder: TWikiFolder | undefined): boolean =>
  !!folder?.can_manage && bisaPunyaSubtopik(folder);
