/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: bilah pesan tersemat
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { ChevronDown, ChevronUp, Pin, PinOff } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { IconButton } from "@plane/propel/icon-button";
import { renderFormattedDate } from "@plane/utils";
import type { TPesanTersemat } from "@/services/chat.service";

type Props = {
  /** Terbaru disematkan lebih dulu, urutan dari server. */
  daftar: TPesanTersemat[];
  namaOrang: (id: string) => string;
  onLompat: (pesanId: string) => void;
  /** Tidak diisi = orang ini tidak boleh melepas sematan di ruang ini. */
  onLepas?: (pesanId: string) => void;
};

/**
 * Bilah di atas percakapan: satu sematan terlihat, klik melompat ke pesannya
 * lalu bergeser ke sematan berikutnya (pola WhatsApp), sehingga klik berulang
 * menyusuri semuanya. Panah membuka daftar lengkap.
 */
export function BilahSematan({ daftar, namaOrang, onLompat, onLepas }: Props) {
  const { t } = useTranslation();
  const [urutan, setUrutan] = useState(0);
  const [terbuka, setTerbuka] = useState(false);

  if (daftar.length === 0) return null;

  // Daftar bisa menyusut (dilepas dari tab lain), jadi indeks dijepit, bukan dipercaya.
  const aktif = daftar[urutan % daftar.length];
  const cuplikan = (p: TPesanTersemat) => p.isi || t("chat_ui.attachment");
  const pengirim = (p: TPesanTersemat) => (p.pengirim ? namaOrang(p.pengirim) : t("chatkartu_ui.system_badge"));

  const lompatAktif = () => {
    onLompat(aktif.id);
    setUrutan((i) => (i + 1) % daftar.length);
  };

  return (
    <div className="border-b border-subtle bg-layer-1">
      <div className="flex items-center gap-2 px-4 py-1.5">
        <Pin className="size-3.5 shrink-0 text-accent-primary" aria-hidden />
        <button
          type="button"
          onClick={lompatAktif}
          className="min-w-0 flex-1 rounded-item text-left hover:bg-layer-transparent-hover"
          title={t("chat_ui.jump_to_message")}
        >
          <span className="block truncate text-12 font-semibold text-accent-primary">
            {daftar.length > 1
              ? t("chat_ui.pinned_count", { current: (urutan % daftar.length) + 1, count: daftar.length })
              : t("chat_ui.pinned_message")}
          </span>
          <span className="block truncate text-12 text-secondary">
            {pengirim(aktif)}: {cuplikan(aktif)}
          </span>
        </button>
        <IconButton
          type="button"
          onClick={() => setTerbuka((v) => !v)}
          aria-label={terbuka ? t("chat_ui.hide_pinned") : t("chat_ui.show_pinned")}
          aria-expanded={terbuka}
          variant="ghost"
          size="sm"
          icon={terbuka ? ChevronUp : ChevronDown}
        />
      </div>

      {terbuka ? (
        <ul className="max-h-60 overflow-y-auto border-t border-subtle py-1">
          {daftar.map((p) => (
            <li key={p.id} className="flex items-center gap-2 px-4 py-1 hover:bg-layer-transparent-hover">
              <button
                type="button"
                onClick={() => {
                  onLompat(p.id);
                  setTerbuka(false);
                }}
                className="min-w-0 flex-1 text-left"
              >
                <span className="flex items-baseline gap-2">
                  <span className="truncate text-12 font-semibold text-primary">{pengirim(p)}</span>
                  <span className="shrink-0 text-12 text-tertiary">{renderFormattedDate(p.created_at, "dd MMM")}</span>
                </span>
                <span className="line-clamp-2 text-12 text-secondary">{cuplikan(p)}</span>
              </button>
              {onLepas ? (
                <IconButton
                  type="button"
                  onClick={() => onLepas(p.id)}
                  aria-label={t("chat_ui.unpin")}
                  title={t("chat_ui.unpin")}
                  variant="ghost"
                  size="sm"
                  icon={PinOff}
                />
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
