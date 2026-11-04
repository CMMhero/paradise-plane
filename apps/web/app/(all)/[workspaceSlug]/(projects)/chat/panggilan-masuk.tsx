/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu panggilan masuk
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Phone, PhoneOff, Video } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Avatar } from "@plane/propel/avatar";
import { Button } from "@plane/propel/button";

type Props = {
  nama: string;
  avatar?: string;
  video: boolean;
  onAngkat: (video: boolean) => void;
  onTolak: () => void;
};

/**
 * Kartu panggilan masuk, tampil di halaman MANA PUN di workspace.
 *
 * Kartu di pojok, bukan layar penuh: orang yang sedang mengetik di work item
 * tidak boleh kehilangan apa yang sedang ia kerjakan hanya karena ada yang
 * menelepon. Layar penuh baru muncul sesudah ia mengangkat.
 *
 * Panggilan video menawarkan "angkat tanpa video": menolak panggilan hanya
 * karena belum siap tampil di kamera itu lebih buruk daripada menjawab dengan
 * suara saja.
 */
export function PanggilanMasuk({ nama, avatar, video, onAngkat, onTolak }: Props) {
  const { t } = useTranslation();
  const judul = video ? t("chat_ui.call_ring.incoming_video") : t("chat_ui.call_ring.incoming_voice");

  return (
    <div
      role="alertdialog"
      aria-modal="false"
      aria-labelledby="panggilan-masuk-judul"
      aria-describedby="panggilan-masuk-nama"
      className="fixed inset-x-3 top-3 z-50 flex flex-col gap-3 rounded-card border border-subtle bg-layer-3 p-4 shadow-overlay-200 sm:inset-x-auto sm:right-4 sm:w-80"
    >
      <div className="flex items-center gap-3">
        <Avatar name={nama} src={avatar} size={40} shape="circle" />
        <div className="min-w-0">
          <p id="panggilan-masuk-nama" className="truncate text-14 font-medium text-primary">
            {nama}
          </p>
          <p id="panggilan-masuk-judul" className="truncate text-12 text-tertiary">
            {judul}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap items-center justify-end gap-2">
        <Button variant="error-fill" size="lg" prependIcon={<PhoneOff />} onClick={onTolak}>
          {t("chat_ui.call_ring.decline")}
        </Button>
        {video ? (
          <Button variant="secondary" size="lg" prependIcon={<Phone />} onClick={() => onAngkat(false)}>
            {t("chat_ui.call_ring.accept_voice_only")}
          </Button>
        ) : null}
        <Button variant="primary" size="lg" prependIcon={video ? <Video /> : <Phone />} onClick={() => onAngkat(video)}>
          {t("chat_ui.call_ring.accept")}
        </Button>
      </div>
    </div>
  );
}
