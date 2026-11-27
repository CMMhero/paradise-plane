/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: widget Pengumuman di Home
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Pengumuman terbaru dari kanal sistem Announcements, memakai kunci SWR yang
 * sama dengan halaman Pengumuman, jadi membuka salah satunya mengisi cache yang
 * lain. Menulis tetap di halaman Pengumuman.
 */

import { useMemo } from "react";
import { observer } from "mobx-react";
import { Link } from "react-router";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import type { THomeWidgetProps } from "@plane/types";
import { Avatar, Loader } from "@plane/ui";
import { getFileURL, renderFormattedDate, renderFormattedTime } from "@plane/utils";
// components
import { kunciPengumuman } from "@/components/pengumuman/cache";
import { IsiMarkdown } from "@/components/pengumuman/isi-markdown";
// hooks
import { useMember } from "@/hooks/store/use-member";
// services
import { ChatService } from "@/services/chat.service";
// pages
import { DaftarLampiran } from "@/app/(all)/[workspaceSlug]/(projects)/chat/lampiran";

const chatService = new ChatService();
/** Berapa pengumuman terbaru yang tampil di Home. */
const JUMLAH_TAMPIL = 3;

export const AnnouncementsWidget = observer(function AnnouncementsWidget({ workspaceSlug }: THomeWidgetProps) {
  const { t } = useTranslation();
  const {
    workspace: { getWorkspaceMemberDetails },
  } = useMember();

  // Daftar percakapan juga mengikutkan saya ke kanal sistem secara malas, jadi
  // ia dipakai menemukan kanal Announcements (sama dengan halaman Pengumuman).
  const { data: percakapan, error: galatKanal } = useSWR(
    `CHAT_PERCAKAPAN_${workspaceSlug}`,
    () => chatService.getPercakapan(workspaceSlug),
    { revalidateOnFocus: false }
  );
  const kanal = percakapan?.find((r) => r.kunci_sistem === "pengumuman");
  const {
    data: pesan,
    error: galatPesan,
    mutate,
  } = useSWR(
    kanal ? kunciPengumuman(workspaceSlug, kanal.id) : null,
    kanal ? () => chatService.getPesanRuang(workspaceSlug, kanal.id) : null,
    { revalidateOnFocus: false, dedupingInterval: 60_000 }
  );

  // Server mengirim urut waktu naik: yang terbaru ada di belakang.
  const terbaru = useMemo(() => {
    const baru = (pesan ?? []).filter((p) => !p.dihapus).slice(-JUMLAH_TAMPIL);
    return baru.map((_, i) => baru[baru.length - 1 - i]);
  }, [pesan]);

  const galat = galatKanal || galatPesan;
  const memuat = !galat && (!percakapan || (!!kanal && !pesan));

  return (
    <section aria-labelledby="home-pengumuman-title" className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <h2 id="home-pengumuman-title" className="text-14 font-semibold text-primary">
          {t("pengumuman_ui.title")}
        </h2>
        <Link to={`/${workspaceSlug}/pengumuman`} className="text-12 text-tertiary hover:text-secondary">
          {t("attention_ui.view_all")}
        </Link>
      </div>
      {galat ? (
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-2 rounded-card border border-subtle px-4 py-3 text-13 text-tertiary"
        >
          <span>{t("pengumuman_ui.load_failed")}</span>
          <Button variant="secondary" size="base" onClick={() => void mutate()}>
            {t("common.retry")}
          </Button>
        </div>
      ) : memuat ? (
        <Loader>
          <span className="sr-only">{t("common.loading")}</span>
          <Loader.Item height="96px" />
        </Loader>
      ) : terbaru.length === 0 ? (
        <p className="rounded-card border border-subtle px-4 py-3 text-13 text-tertiary">{t("pengumuman_ui.empty")}</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {terbaru.map((p) => {
            const penulis = p.pengirim ? getWorkspaceMemberDetails(p.pengirim)?.member : undefined;
            const namaPenulis = penulis?.display_name ?? t("chat_ui.member");
            return (
              <li key={p.id} className="flex flex-col gap-2 rounded-card border border-subtle bg-layer-1 p-4">
                <div className="flex items-center gap-2">
                  <Avatar name={namaPenulis} src={getFileURL(penulis?.avatar_url ?? "")} size="sm" />
                  <p className="min-w-0 truncate text-13 font-medium text-primary">{namaPenulis}</p>
                  <p className="ml-auto shrink-0 text-12 text-tertiary">
                    {renderFormattedDate(p.created_at)} {renderFormattedTime(p.created_at)}
                    {p.disunting ? ` · ${t("chat_ui.edited")}` : null}
                  </p>
                </div>
                {p.isi ? <IsiMarkdown teks={p.isi} /> : null}
                <DaftarLampiran lampiran={p.lampiran ?? []} />
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
});
