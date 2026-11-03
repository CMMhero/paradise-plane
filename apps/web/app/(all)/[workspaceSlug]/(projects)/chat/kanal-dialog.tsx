/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
import useSWR from "swr";
import { Hash, Search, Users } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { EmptyStateCompact } from "@plane/propel/empty-state";
import { Checkbox, EModalPosition, EModalWidth, Input, ModalCore } from "@plane/ui";
import { cn, renderFormattedDate } from "@plane/utils";
// hooks
import { useMember } from "@/hooks/store/use-member";
// services
import { ChatService, type TRuang } from "@/services/chat.service";

const chatService = new ChatService();

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
  /** Kanal publik yang belum diikuti. */
  kanal: TRuang[];
  onGabung: (ruangId: string) => void;
};

/** Saring kanal menurut nama atau topik, tanpa peduli huruf besar-kecil. */
export const saringKanal = (kanal: TRuang[], kunci: string): TRuang[] => {
  const q = kunci.trim().toLowerCase();
  if (!q) return kanal;
  return kanal.filter((r) => (r.nama ?? "").toLowerCase().includes(q) || r.topik.toLowerCase().includes(q));
};

/**
 * Direktori kanal publik: cari, lihat jumlah anggota dan topik, pratinjau, gabung.
 *
 * Pratinjau sengaja TIDAK memuat pesan: berlangganan tetap satu-satunya hak
 * baca isi kanal (lihat `chat_kelola.py`). Yang terlihat sebelum bergabung:
 * nama, topik, jumlah anggota, pembuat, dan tanggal dibuat.
 */
export const DialogJelajahKanal = observer(function DialogJelajahKanal({
  isOpen,
  onClose,
  kanal,
  onGabung,
}: TDialogJelajahKanalProps) {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString();
  const {
    workspace: { getWorkspaceMemberDetails },
  } = useMember();
  const [cari, setCari] = useState("");
  const [dipilih, setDipilih] = useState<string | null>(null);

  const hasil = saringKanal(kanal, cari);
  const { data: detail } = useSWR(
    slug && dipilih && isOpen ? `CHAT_DETAIL_RUANG_${dipilih}` : null,
    slug && dipilih ? () => chatService.getDetailRuang(slug, dipilih) : null
  );
  const pembuat = detail?.pembuat ? getWorkspaceMemberDetails(detail.pembuat)?.member?.display_name : undefined;

  return (
    <ModalCore isOpen={isOpen} handleClose={onClose} position={EModalPosition.CENTER} width={EModalWidth.XL}>
      <div className="flex max-h-[75vh] flex-col">
        <div className="space-y-3 p-5 pb-3">
          <h3 className="text-18 font-medium text-secondary">{t("chat_ui.joinable_channels")}</h3>
          <div className="flex items-center gap-2 search-field border border-subtle px-2.5 py-1.5 focus-within:border-accent-strong">
            <Search className="size-3.5 shrink-0 text-tertiary" />
            <Input
              type="search"
              mode="true-transparent"
              value={cari}
              onChange={(e) => setCari(e.target.value)}
              placeholder={t("chatux_kelola_ui.search_channels")}
              aria-label={t("chatux_kelola_ui.search_channels")}
              className="w-full p-0 text-primary placeholder:text-placeholder"
            />
          </div>
        </div>
        <div className="flex min-h-0 flex-1 flex-col gap-3 px-5 pb-3 md:flex-row">
          <ul className="min-h-0 flex-1 overflow-y-auto" aria-label={t("chat_ui.joinable_channels")}>
            {hasil.length === 0 ? (
              <EmptyStateCompact
                assetKey={cari.trim() ? "search" : "members"}
                title={cari.trim() ? t("chatux_kelola_ui.no_matching_channels") : t("chat_ui.no_other_channels")}
                assetClassName="size-16"
              />
            ) : (
              hasil.map((r) => (
                <li key={r.id} className="flex items-center gap-2 rounded-item">
                  <button
                    type="button"
                    onClick={() => setDipilih(r.id)}
                    aria-pressed={dipilih === r.id}
                    className={cn(
                      "flex min-w-0 flex-1 items-start gap-2 rounded-item px-2 py-2 text-left hover:bg-layer-1 sentuh:py-3",
                      dipilih === r.id && "bg-layer-1-selected"
                    )}
                  >
                    <Hash className="mt-0.5 size-3.5 shrink-0 text-tertiary" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-13 font-medium text-primary">{r.nama}</span>
                      <span className="block truncate text-12 text-tertiary">
                        {t("chatux_kelola_ui.member_count", { count: r.jumlah_anggota ?? 0 })}
                        {r.topik ? ` · ${r.topik}` : ""}
                      </span>
                    </span>
                  </button>
                  <Button variant="secondary" size="base" onClick={() => onGabung(r.id)}>
                    {t("chat_ui.join")}
                  </Button>
                </li>
              ))
            )}
          </ul>
          {dipilih ? (
            <aside
              aria-live="polite"
              className="shrink-0 rounded-card border border-subtle bg-layer-1 p-4 md:w-64"
              aria-label={t("chatux_kelola_ui.preview")}
            >
              {detail ? (
                <div className="space-y-2">
                  <p className="flex items-center gap-1.5 text-14 font-medium text-primary">
                    <Hash className="size-4 text-tertiary" />
                    <span className="truncate">{detail.nama}</span>
                  </p>
                  <p className="text-13 whitespace-pre-wrap text-secondary">
                    {detail.topik || t("chatux_kelola_ui.no_topic")}
                  </p>
                  <p className="flex items-center gap-1.5 text-12 text-tertiary">
                    <Users className="size-3.5" />
                    {t("chatux_kelola_ui.member_count", { count: detail.jumlah_anggota })}
                  </p>
                  {pembuat ? (
                    <p className="text-12 text-tertiary">{t("chatux_kelola_ui.created_by", { name: pembuat })}</p>
                  ) : null}
                  <p className="text-12 text-tertiary">{renderFormattedDate(detail.created_at)}</p>
                  <p className="text-12 text-tertiary">{t("chatux_kelola_ui.preview_hint")}</p>
                  <Button variant="primary" size="base" className="w-full" onClick={() => onGabung(detail.id)}>
                    {t("chat_ui.join")}
                  </Button>
                </div>
              ) : (
                <p className="text-12 text-tertiary">{t("chat_ui.loading")}</p>
              )}
            </aside>
          ) : null}
        </div>
        <div className="flex items-center justify-end border-t-[0.5px] border-subtle px-5 py-4">
          <Button variant="secondary" onClick={onClose}>
            {t("close")}
          </Button>
        </div>
      </div>
    </ModalCore>
  );
});
