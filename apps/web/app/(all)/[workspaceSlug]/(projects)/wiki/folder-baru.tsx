/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: nama folder Wiki sebelum dibuat
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { EModalPosition, EModalWidth, Input, ModalCore } from "@plane/ui";

type TProps = {
  isOpen: boolean;
  onClose: () => void;
  /** Menerima nama yang sudah dirapikan; menolak (throw) membiarkan dialog tetap terbuka. */
  onBuat: (nama: string) => Promise<void>;
};

/** Folder butuh nama sebelum ada ("QMS"), jadi nama ditanya dulu, bukan dibuat "New folder" lalu diganti. */
export function FolderBaru({ isOpen, onClose, onBuat }: TProps) {
  const { t } = useTranslation();
  const [nama, setNama] = useState("");
  const [sedangMembuat, setSedangMembuat] = useState(false);

  const buat = async () => {
    const bersih = nama.trim();
    if (!bersih || sedangMembuat) return;
    setSedangMembuat(true);
    try {
      await onBuat(bersih);
      setNama("");
    } catch {
      // pemanggil sudah menampilkan toast galatnya
    } finally {
      setSedangMembuat(false);
    }
  };

  return (
    <ModalCore isOpen={isOpen} handleClose={onClose} position={EModalPosition.CENTER} width={EModalWidth.XL}>
      <div className="space-y-4 p-6">
        <div>
          <h2 className="text-14 font-semibold text-primary">{t("ui_fixes.new_folder_title")}</h2>
          <p className="mt-1 text-12 text-tertiary">{t("ui_fixes.new_folder_hint")}</p>
        </div>

        <Input
          type="text"
          value={nama}
          placeholder={t("ui_fixes.new_folder_placeholder")}
          // Modal berisi satu kolom yang dibuka khusus untuk mengetik nama.
          // oxlint-disable-next-line jsx-a11y/no-autofocus
          autoFocus
          onChange={(e) => setNama(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void buat();
          }}
          className="w-full border border-subtle text-primary focus:border-accent-strong"
        />

        <div className="flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={onClose}>
            {t("cancel")}
          </Button>
          <Button variant="primary" size="sm" onClick={buat} loading={sedangMembuat} disabled={!nama.trim()}>
            {t("ui_fixes.new_folder_create")}
          </Button>
        </div>
      </div>
    </ModalCore>
  );
}
