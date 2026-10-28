/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: ganti nama Materi
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
// services
import { WikiMaterialService } from "@/services/wiki_material.service";

const layanan = new WikiMaterialService();

type TProps = {
  workspaceSlug: string;
  projectId: string;
  materiId: string;
  judulSekarang: string;
  namaBerkas: string;
  isOpen: boolean;
  onClose: () => void;
  onSelesai: () => void | Promise<unknown>;
};

/**
 * Judul materi terpisah dari nama berkasnya, dan itu disengaja.
 *
 * Saat diunggah, judulnya memang mengikuti nama berkas apa adanya, karena itu
 * satu-satunya yang kita tahu dan memaksa orang mengetik judul di tengah
 * unggahan hanya membuat mereka berhenti mengunggah. Tapi berkas nyata bernama
 * "SOP_final_v3(1).pdf", dan itu bukan judul yang layak dibaca 83 orang di
 * halaman daftar. Jadi judulnya bisa diganti sesudahnya, dan nama berkas
 * aslinya tetap utuh untuk diunduh.
 */
export function GantiNamaMateri({
  workspaceSlug,
  projectId,
  materiId,
  judulSekarang,
  namaBerkas,
  isOpen,
  onClose,
  onSelesai,
}: TProps) {
  const { t } = useTranslation();
  const [judul, setJudul] = useState(judulSekarang);
  const [sedangSimpan, setSedangSimpan] = useState(false);

  const simpan = async () => {
    const bersih = judul.trim();
    if (!bersih || sedangSimpan) return;
    setSedangSimpan(true);
    try {
      await layanan.rename(workspaceSlug, projectId, materiId, bersih);
      await onSelesai();
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("wiki_ui.rename.done_title"), message: bersih });
      onClose();
    } catch (error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("wiki_ui.common.failed"),
        message: (error as { error?: string })?.error || t("wiki_ui.rename.failed_message"),
      });
    } finally {
      setSedangSimpan(false);
    }
  };

  return (
    <ModalCore isOpen={isOpen} handleClose={onClose} position={EModalPosition.CENTER} width={EModalWidth.XL}>
      <div className="space-y-4 p-6">
        <div>
          <h2 className="text-15 font-semibold text-primary">{t("wiki_ui.rename.title")}</h2>
          <p className="mt-1 text-12 text-tertiary">{t("wiki_ui.rename.note", { fileName: namaBerkas })}</p>
        </div>

        <input
          type="text"
          value={judul}
          // Fokus otomatis memang dipertanyakan untuk form pada umumnya, tapi
          // ini modal yang HANYA berisi satu kolom dan dibuka dengan sengaja
          // untuk mengetik. Memaksa orang menekan Tab dulu justru yang aneh.
          // oxlint-disable-next-line jsx-a11y/no-autofocus
          autoFocus
          onChange={(e) => setJudul(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void simpan();
          }}
          className="w-full rounded-md border border-subtle bg-layer-2 px-3 py-2 text-13 text-primary outline-none focus:border-accent-strong"
        />

        <div className="flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={onClose}>
            {t("cancel")}
          </Button>
          <Button variant="primary" size="sm" onClick={simpan} loading={sedangSimpan} disabled={!judul.trim()}>
            {t("save")}
          </Button>
        </div>
      </div>
    </ModalCore>
  );
}
