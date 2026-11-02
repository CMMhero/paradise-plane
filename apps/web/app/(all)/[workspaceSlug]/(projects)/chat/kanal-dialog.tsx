/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { Hash } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { EmptyStateCompact } from "@plane/propel/empty-state";
import { Checkbox, EModalPosition, EModalWidth, Input, ModalCore } from "@plane/ui";
// services
import type { TRuang } from "@/services/chat.service";

type TDialogBuatKanalProps = {
  isOpen: boolean;
  onClose: () => void;
  /** Mengembalikan true kalau kanal berhasil dibuat; isian baru dikosongkan saat itu. */
  onBuat: (nama: string, privat: boolean) => Promise<boolean>;
};

/** Dialog buat kanal. Memakai ModalCore seperti modal lain di aplikasi, jadi
 * Escape, klik di luar, dan fokus awal ke kotak nama sudah diurus Headless UI. */
export function DialogBuatKanal({ isOpen, onClose, onBuat }: TDialogBuatKanalProps) {
  const { t } = useTranslation();
  const [nama, setNama] = useState("");
  const [privat, setPrivat] = useState(false);
  const [membuat, setMembuat] = useState(false);

  const kirim = async () => {
    const bersih = nama.trim();
    if (!bersih || membuat) return;
    setMembuat(true);
    const berhasil = await onBuat(bersih, privat);
    setMembuat(false);
    if (!berhasil) return;
    setNama("");
    setPrivat(false);
  };

  return (
    <ModalCore isOpen={isOpen} handleClose={onClose} position={EModalPosition.CENTER} width={EModalWidth.MD}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void kirim();
        }}
      >
        <div className="space-y-4 p-5">
          <h3 className="text-18 font-medium text-secondary">{t("chat_ui.new_channel")}</h3>
          <Input
            type="text"
            value={nama}
            onChange={(e) => setNama(e.target.value)}
            maxLength={80}
            placeholder={t("chat_ui.channel_name_placeholder")}
            aria-label={t("chat_ui.channel_name_placeholder")}
            className="w-full text-14"
          />
          <label className="flex w-fit cursor-pointer items-center gap-2 text-13 text-secondary">
            <Checkbox checked={privat} onChange={(e) => setPrivat(e.target.checked)} />
            {t("chat_ui.private_channel")}
          </label>
        </div>
        <div className="flex items-center justify-end gap-2 border-t-[0.5px] border-subtle px-5 py-4">
          <Button variant="secondary" type="button" onClick={onClose}>
            {t("cancel")}
          </Button>
          <Button variant="primary" type="submit" loading={membuat} disabled={!nama.trim() || membuat}>
            {membuat ? t("chat_ui.creating") : t("chat_ui.create")}
          </Button>
        </div>
      </form>
    </ModalCore>
  );
}

type TDialogJelajahKanalProps = {
  isOpen: boolean;
  onClose: () => void;
  kanal: TRuang[];
  onGabung: (ruangId: string) => void;
};

/** Daftar kanal publik yang belum diikuti. */
export function DialogJelajahKanal({ isOpen, onClose, kanal, onGabung }: TDialogJelajahKanalProps) {
  const { t } = useTranslation();

  return (
    <ModalCore isOpen={isOpen} handleClose={onClose} position={EModalPosition.CENTER} width={EModalWidth.MD}>
      <div className="flex max-h-[70vh] flex-col">
        <h3 className="p-5 pb-3 text-18 font-medium text-secondary">{t("chat_ui.joinable_channels")}</h3>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-3">
          {kanal.length === 0 ? (
            <EmptyStateCompact assetKey="members" title={t("chat_ui.no_other_channels")} assetClassName="size-16" />
          ) : (
            kanal.map((r) => (
              <div key={r.id} className="flex items-center gap-2 py-1.5">
                <Hash className="size-3.5 shrink-0 text-tertiary" />
                <span className="min-w-0 flex-1 truncate text-13 text-primary">{r.nama}</span>
                <Button variant="secondary" size="base" onClick={() => onGabung(r.id)}>
                  {t("chat_ui.join")}
                </Button>
              </div>
            ))
          )}
        </div>
        <div className="flex items-center justify-end border-t-[0.5px] border-subtle px-5 py-4">
          <Button variant="secondary" onClick={onClose}>
            {t("close")}
          </Button>
        </div>
      </div>
    </ModalCore>
  );
}
