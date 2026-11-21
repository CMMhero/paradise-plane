/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: halaman Pengumuman
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Pengumuman tetap tersimpan di kanal sistem "Announcements" (`kunci_sistem =
 * pengumuman`), jadi daftar, hak menulis, dan email ke seluruh anggota memakai
 * jalur Obrolan yang sama. Halaman ini hanya muka lain untuk kanal itu: daftar
 * baca-saja yang rapi, dan kotak tulis bagi yang boleh. Hak menulis tidak
 * diatur di sini; server menolak 403 untuk yang tidak berhak (`boleh_kirim`).
 */

import { useMemo, useState } from "react";
import { observer } from "mobx-react";
import { Link, useParams } from "react-router";
import useSWR, { mutate as mutateGlobal } from "swr";
import { MessageSquare } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Avatar, Loader, TextArea } from "@plane/ui";
import { getFileURL, renderFormattedDate, renderFormattedTime } from "@plane/utils";
// components
import { PageShell } from "@/components/common/page-shell";
import { PageHead } from "@/components/core/page-title";
// hooks
import { useMember } from "@/hooks/store/use-member";
// services
import { ChatService, KUNCI_BELUM_DIBACA } from "@/services/chat.service";
import type { TPesan } from "@/services/chat.service";
// local imports
import { potongTautan } from "../chat/tautan";

const chatService = new ChatService();
/** Ukuran satu halaman dari server (`JUMLAH_PESAN` di chat.py). */
const UKURAN_HALAMAN = 100;

const denganTautan = (teks: string) =>
  potongTautan(teks).map((potongan, i) =>
    potongan.jenis === "teks" ? (
      potongan.isi
    ) : (
      // Potongan lahir dari memecah satu teks yang tidak berubah sebagian.
      // oxlint-disable-next-line no-array-index-key
      <span key={`tautan-${i}`}>
        <a
          href={potongan.alamat}
          target="_blank"
          rel="noopener noreferrer"
          className="text-accent-primary underline underline-offset-2 hover:opacity-80"
        >
          {potongan.alamat}
        </a>
        {potongan.ekor}
      </span>
    )
  );

function PengumumanPage() {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString();
  const {
    workspace: { getWorkspaceMemberDetails },
  } = useMember();
  const [draf, setDraf] = useState("");
  const [mengirim, setMengirim] = useState(false);
  const [lebihLama, setLebihLama] = useState<TPesan[]>([]);
  const [habis, setHabis] = useState(false);
  const [memuatLama, setMemuatLama] = useState(false);

  // Daftar percakapan juga mengikutkan saya ke kanal sistem secara malas, jadi
  // ia dipakai untuk menemukan kanal Announcements, bukan daftar kanal publik.
  const { data: percakapan, error: galatKanal } = useSWR(
    slug ? `CHAT_PERCAKAPAN_${slug}` : null,
    slug ? () => chatService.getPercakapan(slug) : null,
    { revalidateOnFocus: false }
  );
  const kanal = percakapan?.find((r) => r.kunci_sistem === "pengumuman");

  const {
    data: pesan,
    error: galatPesan,
    mutate,
  } = useSWR(
    slug && kanal ? `PENGUMUMAN_${slug}_${kanal.id}` : null,
    slug && kanal ? () => chatService.getPesanRuang(slug, kanal.id) : null,
    { revalidateOnFocus: true }
  );

  // Server mengirim urut waktu naik, dan halaman lebih lama dipasang di depan,
  // jadi daftar ini naik; ditampilkan terbaru dulu dengan membacanya dari belakang.
  const daftar = useMemo(() => {
    const naik = [...lebihLama, ...(pesan ?? [])].filter((p) => !p.dihapus);
    return naik.map((_, i) => naik[naik.length - 1 - i]);
  }, [pesan, lebihLama]);
  const adaLagi = !habis && (pesan?.length ?? 0) >= UKURAN_HALAMAN;

  const nama = (id: string | null) =>
    (id ? getWorkspaceMemberDetails(id)?.member?.display_name : null) ?? t("chat_ui.member");

  const muatLebihLama = async () => {
    if (!slug || !kanal || memuatLama) return;
    const tertua = (lebihLama[0] ?? pesan?.[0])?.created_at;
    if (!tertua) return;
    setMemuatLama(true);
    try {
      const halaman = await chatService.getPesanLamaRuang(slug, kanal.id, tertua);
      setLebihLama((lama) => [...halaman, ...lama]);
      if (halaman.length < UKURAN_HALAMAN) setHabis(true);
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: t("pengumuman_ui.load_failed") });
    } finally {
      setMemuatLama(false);
    }
  };

  const terbitkan = async () => {
    const isi = draf.trim();
    if (!slug || !kanal || !isi || mengirim) return;
    setMengirim(true);
    try {
      await chatService.kirimPesanRuang(slug, kanal.id, isi);
      setDraf("");
      await mutate();
      void mutateGlobal(`CHAT_PERCAKAPAN_${slug}`);
      void mutateGlobal(KUNCI_BELUM_DIBACA);
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: (galat as { error?: string })?.error ?? t("pengumuman_ui.send_failed"),
      });
    } finally {
      setMengirim(false);
    }
  };

  if (!slug) return <></>;

  return (
    <>
      <PageHead title={t("pengumuman_ui.title")} />
      <PageShell>
        <PageShell.Header title={t("pengumuman_ui.title")} />
        {kanal?.boleh_kirim ? (
          <div className="flex flex-col gap-2 rounded-card border border-subtle bg-surface-1 p-3">
            <TextArea
              value={draf}
              onChange={(e) => setDraf(e.target.value)}
              placeholder={t("pengumuman_ui.placeholder")}
              rows={3}
              className="w-full"
            />
            <div className="flex justify-end">
              <Button
                variant="primary"
                size="base"
                onClick={() => void terbitkan()}
                disabled={!draf.trim() || mengirim}
              >
                {t("pengumuman_ui.send")}
              </Button>
            </div>
          </div>
        ) : null}

        {galatKanal || galatPesan ? (
          <div role="alert" className="rounded-card border border-subtle px-4 py-3 text-13 text-tertiary">
            {t("pengumuman_ui.load_failed")}
          </div>
        ) : !pesan ? (
          <Loader className="flex flex-col gap-3">
            <span className="sr-only">{t("common.loading")}</span>
            <Loader.Item height="96px" />
            <Loader.Item height="96px" />
          </Loader>
        ) : daftar.length === 0 ? (
          <p className="py-10 text-center text-13 text-tertiary">{t("pengumuman_ui.empty")}</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {daftar.map((p) => {
              const penulis = p.pengirim ? getWorkspaceMemberDetails(p.pengirim)?.member : undefined;
              return (
                <li key={p.id} className="flex flex-col gap-2 rounded-card border border-subtle bg-surface-1 p-4">
                  <div className="flex items-center gap-2">
                    <Avatar name={nama(p.pengirim)} src={getFileURL(penulis?.avatar_url ?? "")} size="sm" />
                    <p className="min-w-0 truncate text-13 font-medium text-primary">{nama(p.pengirim)}</p>
                    <p className="ml-auto shrink-0 text-12 text-tertiary">
                      {renderFormattedDate(p.created_at)} {renderFormattedTime(p.created_at)}
                    </p>
                  </div>
                  <p className="text-13 [overflow-wrap:anywhere] whitespace-pre-wrap text-secondary">
                    {denganTautan(p.isi)}
                  </p>
                </li>
              );
            })}
          </ul>
        )}

        {adaLagi ? (
          <div>
            <Button variant="secondary" size="base" onClick={() => void muatLebihLama()} disabled={memuatLama}>
              {t("changelog_ui.show_more")}
            </Button>
          </div>
        ) : null}

        {kanal ? (
          <Link
            to={`/${slug}/chat?ruang=${kanal.id}`}
            className="inline-flex items-center gap-1.5 text-12 text-tertiary hover:text-secondary"
          >
            <MessageSquare className="size-3.5" />
            {t("pengumuman_ui.open_in_chat")}
          </Link>
        ) : null}
      </PageShell>
    </>
  );
}

export default observer(PengumumanPage);
