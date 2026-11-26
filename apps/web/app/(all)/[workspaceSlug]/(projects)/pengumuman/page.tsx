/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: halaman Pengumuman
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Pengumuman tetap tersimpan di kanal sistem "Announcements" (`kunci_sistem =
 * pengumuman`), jadi daftar, hak menulis, dan email ke seluruh anggota memakai
 * jalur Obrolan yang sama. Halaman ini hanya muka lain untuk kanal itu: daftar
 * yang rapi, penyunting kaya bagi yang boleh menulis (Markdown + lampiran, lihat
 * penyunting.tsx), dan menu Sunting/Hapus pada pengumuman milik sendiri, tanpa
 * batas waktu. Hak-hak itu tidak diatur di sini; server menolak 403 untuk yang
 * tidak berhak (`boleh_kirim`, `ChatPesanEndpoint`).
 */

import { useMemo, useState } from "react";
import { observer } from "mobx-react";
import { Link, useParams } from "react-router";
import useSWR, { mutate as mutateGlobal } from "swr";
import { MessageSquare, MoreHorizontal, Pencil, Trash2 } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { Menu } from "@plane/propel/menu";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Avatar, Loader } from "@plane/ui";
import { getFileURL, renderFormattedDate, renderFormattedTime } from "@plane/utils";
// components
import { PageShell } from "@/components/common/page-shell";
import { PageHead } from "@/components/core/page-title";
import { kunciPengumuman, segarkanPengumuman } from "@/components/pengumuman/cache";
import { IsiMarkdown } from "@/components/pengumuman/isi-markdown";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useUser } from "@/hooks/store/user";
import { useKonfirmasi } from "@/hooks/use-konfirmasi";
// services
import { ChatService, KUNCI_BELUM_DIBACA } from "@/services/chat.service";
import type { TPesan, TRujukanKirim } from "@/services/chat.service";
// local imports
import { DaftarLampiran } from "../chat/lampiran";
import { PenyuntingPengumuman, SuntingPengumuman } from "./penyunting";

const chatService = new ChatService();
/** Ukuran satu halaman dari server (`JUMLAH_PESAN` di chat.py). */
const UKURAN_HALAMAN = 100;

function PengumumanPage() {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString();
  const {
    workspace: { getWorkspaceMemberDetails },
  } = useMember();
  const [lebihLama, setLebihLama] = useState<TPesan[]>([]);
  const [habis, setHabis] = useState(false);
  const [memuatLama, setMemuatLama] = useState(false);
  const [menyunting, setMenyunting] = useState<string | null>(null);
  const { data: saya } = useUser();
  const { minta, dialog } = useKonfirmasi();

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
    slug && kanal ? kunciPengumuman(slug, kanal.id) : null,
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

  const terbitkan = async (isi: string, lampiran: string[], rujukan: TRujukanKirim) => {
    if (!slug || !kanal) return;
    try {
      await chatService.kirimPesanRuang(slug, kanal.id, isi, lampiran, undefined, rujukan);
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: (galat as { error?: string })?.error ?? t("pengumuman_ui.send_failed"),
      });
      throw galat;
    }
    await mutate();
    void mutateGlobal(`CHAT_PERCAKAPAN_${slug}`);
    void mutateGlobal(KUNCI_BELUM_DIBACA);
  };

  /** Cache SWR (halaman, Home, Obrolan) dan riwayat lama yang disimpan di halaman ini. */
  const terapkanUbahan = (pesanId: string, hasil: TPesan | "dihapus") => {
    if (!slug || !kanal) return;
    setLebihLama((lama) =>
      lama.map((p) => {
        if (p.id !== pesanId) return p;
        return hasil === "dihapus" ? { ...p, dihapus: true } : hasil;
      })
    );
    segarkanPengumuman(slug, kanal.id, pesanId, hasil);
  };

  const simpan = async (pesanId: string, isi: string, rujukan: TRujukanKirim) => {
    if (!slug) return;
    try {
      terapkanUbahan(pesanId, await chatService.suntingPesan(slug, pesanId, isi, rujukan));
      setMenyunting(null);
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: (galat as { error?: string })?.error ?? t("pengumuman_ui.edit_failed"),
      });
      throw galat;
    }
  };

  const hapus = async (pesanId: string) => {
    if (!slug) return;
    try {
      await chatService.hapusPesan(slug, pesanId);
      terapkanUbahan(pesanId, "dihapus");
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: (galat as { error?: string })?.error ?? t("pengumuman_ui.delete_failed"),
      });
    }
  };

  const mintaHapus = (pesanId: string) =>
    minta({ judul: t("pengumuman_ui.confirm_delete_title"), isi: t("pengumuman_ui.confirm_delete_body") }, () =>
      hapus(pesanId)
    );

  if (!slug) return <></>;

  return (
    <>
      <PageHead title={t("pengumuman_ui.title")} />
      <PageShell>
        <PageShell.Header title={t("pengumuman_ui.title")} />
        {kanal?.boleh_kirim ? <PenyuntingPengumuman slug={slug} onTerbit={terbitkan} /> : null}

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
              // Hanya penulisnya; kartu sistem bukan tulisan yang bisa diubah.
              const milikSaya = !!saya?.id && p.pengirim === saya.id && (p.jenis ?? "teks") === "teks";
              return (
                <li key={p.id} className="flex flex-col gap-2 rounded-card border border-subtle bg-layer-1 p-4">
                  <div className="flex items-center gap-2">
                    <Avatar name={nama(p.pengirim)} src={getFileURL(penulis?.avatar_url ?? "")} size="sm" />
                    <p className="min-w-0 truncate text-13 font-medium text-primary">{nama(p.pengirim)}</p>
                    <p className="ml-auto shrink-0 text-12 text-tertiary">
                      {renderFormattedDate(p.created_at)} {renderFormattedTime(p.created_at)}
                      {p.disunting ? ` · ${t("chat_ui.edited")}` : null}
                    </p>
                    {milikSaya && menyunting !== p.id ? (
                      <Menu
                        ariaLabel={t("common.options")}
                        optionsClassName="min-w-36"
                        customButton={
                          <span
                            className="flex size-6 items-center justify-center rounded-button text-secondary hover:bg-layer-transparent-hover"
                            title={t("common.options")}
                          >
                            <MoreHorizontal className="size-3.5" />
                          </span>
                        }
                      >
                        <Menu.MenuItem onClick={() => setMenyunting(p.id)} className="flex items-center gap-2">
                          <Pencil className="size-3.5 shrink-0" />
                          {t("edit")}
                        </Menu.MenuItem>
                        <Menu.MenuItem
                          onClick={() => mintaHapus(p.id)}
                          className="flex items-center gap-2 text-danger-primary"
                        >
                          <Trash2 className="size-3.5 shrink-0" />
                          {t("delete")}
                        </Menu.MenuItem>
                      </Menu>
                    ) : null}
                  </div>
                  {menyunting === p.id ? (
                    <SuntingPengumuman
                      slug={slug}
                      pesanId={p.id}
                      isi={p.isi}
                      onSimpan={(isi, rujukan) => simpan(p.id, isi, rujukan)}
                      onBatal={() => setMenyunting(null)}
                    />
                  ) : p.isi ? (
                    <IsiMarkdown teks={p.isi} />
                  ) : null}
                  <DaftarLampiran lampiran={p.lampiran ?? []} />
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
      {dialog}
    </>
  );
}

export default observer(PengumumanPage);
