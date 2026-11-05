/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu pratinjau hover untuk mention (KEP-91)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Hash, Lock, Users } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
// hooks
import { useInfoKanal } from "@/components/editor/embeds/mentions/use-info-rujukan";

/**
 * Isi kartu hover untuk #kanal: nama, publik/privat, topik, jumlah anggota.
 * Mengambil datanya sendiri; kunci SWR-nya sama dengan chip, jadi biasanya sudah ada di cache.
 */
export function KanalPreviewCard({ id }: { id: string }) {
  const { t } = useTranslation();
  const { info, isLoading } = useInfoKanal(id);

  if (isLoading || !info) return <p className="text-12 text-tertiary">{t("rujukan_ui.preview_loading")}</p>;

  // Tanpa akses: tidak ada yang boleh dibocorkan selain fakta bahwa kanalnya privat.
  if (!info.boleh) {
    return (
      <div className="flex items-start gap-2 text-12 text-tertiary">
        <Lock className="mt-0.5 size-3.5 shrink-0" aria-hidden />
        <p>{t("rujukan_ui.private_channel_hint")}</p>
      </div>
    );
  }

  const isPrivate = info.tipe === "privat";
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-1.5">
        <Hash className="size-3.5 shrink-0 text-tertiary" aria-hidden />
        <span className="min-w-0 flex-1 truncate text-13 font-medium text-primary">{info.nama}</span>
        <span className="flex shrink-0 items-center gap-1 rounded-sm bg-layer-1 px-1 text-11 text-tertiary">
          {isPrivate ? <Lock className="size-2.5" aria-hidden /> : null}
          {isPrivate ? t("rujukan_ui.private_channel") : t("rujukan_ui.public_channel")}
        </span>
      </div>
      <p className={info.topik ? "line-clamp-3 text-12 text-secondary" : "text-12 text-tertiary"}>
        {info.topik || t("rujukan_ui.no_topic")}
      </p>
      <p className="flex items-center gap-1.5 text-11 text-tertiary">
        <Users className="size-3" aria-hidden />
        {t("rujukan_ui.members", { count: info.jumlah_anggota ?? 0 })}
      </p>
    </div>
  );
}
