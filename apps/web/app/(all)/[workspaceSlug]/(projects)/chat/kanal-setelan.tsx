/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: setelan kanal obrolan
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu dialog untuk semua yang menyangkut kanal: nama, topik, anggota, undang,
 * keluarkan, keluar sendiri, dan hapus.
 *
 * Yang boleh mengubah ditentukan SERVER (`boleh_kelola` di `chat_kelola.py`):
 * pembuat, admin workspace, atau Super Admin yang juga anggota. UI hanya
 * menyembunyikan tombol yang pasti ditolak; penjagaannya tetap di API.
 * Kanal sistem (`sistem`) tidak bisa diubah maupun ditinggalkan.
 */

import { useEffect, useMemo, useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { Hash, Lock, LogOut, Search, Trash2, UserMinus, UserPlus } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { IconButton } from "@plane/propel/icon-button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Avatar, EModalPosition, EModalWidth, Input, ModalCore, TextArea } from "@plane/ui";
import { getFileURL } from "@plane/utils";
// components
import { DenganKehadiran } from "@/components/chat/titik-kehadiran";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useUser } from "@/hooks/store/user";
import { useKonfirmasi } from "@/hooks/use-konfirmasi";
// services
import { ChatService } from "@/services/chat.service";

const chatService = new ChatService();
const BATAS_NAMA = 80;
const BATAS_TOPIK = 255;
/** Hasil pemilih undangan dibatasi supaya daftar 90 orang tidak menenggelamkan dialog. */
const MAKS_CALON = 8;

type Props = {
  isOpen: boolean;
  onClose: () => void;
  slug: string;
  ruangId: string | null;
  /** Dipanggil sesudah keluar sendiri atau kanal dihapus: halaman menutup percakapan. */
  onPergi: () => void;
  /** Nama, topik, atau anggota berubah: halaman menyegarkan daftarnya. */
  onBerubah: () => void;
};

const pesanGalat = (galat: unknown, cadangan: string) => (galat as { error?: string })?.error ?? cadangan;

export const DialogSetelanKanal = observer(function DialogSetelanKanal({
  isOpen,
  onClose,
  slug,
  ruangId,
  onPergi,
  onBerubah,
}: Props) {
  const { t } = useTranslation();
  const { data: saya } = useUser();
  const {
    workspace: { workspaceMemberIds, getWorkspaceMemberDetails },
  } = useMember();
  const { minta, dialog } = useKonfirmasi();

  const aktif = isOpen && ruangId;
  const { data: detail, mutate: muatDetail } = useSWR(
    aktif ? `CHAT_DETAIL_RUANG_${ruangId}` : null,
    aktif ? () => chatService.getDetailRuang(slug, ruangId) : null
  );
  const { data: anggota, mutate: muatAnggota } = useSWR(
    aktif ? `CHAT_ANGGOTA_RUANG_${ruangId}` : null,
    aktif ? () => chatService.getAnggotaRuang(slug, ruangId) : null
  );

  const [nama, setNama] = useState("");
  const [topik, setTopik] = useState("");
  const [menyimpan, setMenyimpan] = useState(false);
  const [cariUndang, setCariUndang] = useState("");

  // Isian disalin dari server setiap kali detail baru datang (buka dialog,
  // atau orang lain mengubahnya), bukan dibiarkan memegang nilai basi.
  useEffect(() => {
    if (!detail) return;
    // oxlint-disable-next-line react/set-state-in-effect -- sync editable copy with the server value
    setNama(detail.nama ?? "");
    setTopik(detail.topik ?? "");
  }, [detail]);

  const bolehKelola = !!detail?.boleh_kelola;
  // Kanal publik: siapa pun bisa masuk sendiri, jadi siapa pun boleh mengajak.
  const bolehUndang = !!detail && !detail.sistem && (bolehKelola || detail.tipe === "kanal");
  const berubah = !!detail && (nama.trim() !== (detail.nama ?? "") || topik.trim() !== (detail.topik ?? ""));

  const calon = useMemo(() => {
    const sudah = new Set(anggota ?? []);
    const q = cariUndang.trim().toLowerCase();
    if (!q) return [];
    return (workspaceMemberIds ?? [])
      .filter((id) => !sudah.has(id))
      .filter((id) => (getWorkspaceMemberDetails(id)?.member?.display_name ?? "").toLowerCase().includes(q))
      .slice(0, MAKS_CALON);
  }, [anggota, cariUndang, workspaceMemberIds, getWorkspaceMemberDetails]);

  const segarkan = async () => {
    await Promise.all([muatDetail(), muatAnggota()]);
    onBerubah();
  };

  const simpan = async () => {
    if (!ruangId || !berubah || menyimpan) return;
    setMenyimpan(true);
    try {
      await chatService.ubahRuang(slug, ruangId, { nama: nama.trim(), topik: topik.trim() });
      await segarkan();
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("chatux_kelola_ui.saved") });
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("chatux_kelola_ui.save_failed"),
        message: pesanGalat(galat, t("chat_ui.try_again_shortly")),
      });
    } finally {
      setMenyimpan(false);
    }
  };

  const undang = async (userId: string) => {
    if (!ruangId) return;
    try {
      await chatService.tambahAnggotaRuang(slug, ruangId, userId);
      setCariUndang("");
      await segarkan();
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("chatux_kelola_ui.invite_failed"),
        message: pesanGalat(galat, t("chat_ui.try_again_shortly")),
      });
    }
  };

  const keluarkan = (userId: string, namaOrang: string) =>
    minta(
      {
        judul: t("chatux_kelola_ui.confirm_remove_title"),
        isi: t("chatux_kelola_ui.confirm_remove_body", { name: namaOrang }),
        tombol: t("chatux_kelola_ui.remove"),
        tombolProses: t("chatux_kelola_ui.removing"),
      },
      async () => {
        if (!ruangId) return;
        try {
          await chatService.keluarkanAnggota(slug, ruangId, userId);
          await segarkan();
        } catch (galat) {
          setToast({
            type: TOAST_TYPE.ERROR,
            title: t("chatux_kelola_ui.remove_failed"),
            message: pesanGalat(galat, t("chat_ui.try_again_shortly")),
          });
        }
      }
    );

  const keluar = () =>
    minta(
      {
        judul: t("chat_ui.confirm_leave_title"),
        isi: t("chat_ui.confirm_leave_body", { name: detail?.nama ?? "" }),
        tombol: t("chat_ui.leave_channel"),
        tombolProses: t("chat_ui.leaving"),
      },
      async () => {
        if (!ruangId) return;
        try {
          await chatService.keluarRuang(slug, ruangId);
          onClose();
          onPergi();
        } catch (galat) {
          setToast({
            type: TOAST_TYPE.ERROR,
            title: t("chat_ui.leave_failed"),
            message: pesanGalat(galat, t("chat_ui.try_again_shortly")),
          });
        }
      }
    );

  const hapus = () =>
    minta(
      {
        judul: t("chatux_kelola_ui.confirm_delete_title"),
        isi: t("chatux_kelola_ui.confirm_delete_body", { name: detail?.nama ?? "" }),
      },
      async () => {
        if (!ruangId) return;
        try {
          await chatService.hapusRuang(slug, ruangId);
          onClose();
          onPergi();
        } catch (galat) {
          setToast({
            type: TOAST_TYPE.ERROR,
            title: t("chatux_kelola_ui.delete_failed"),
            message: pesanGalat(galat, t("chat_ui.try_again_shortly")),
          });
        }
      }
    );

  const Ikon = detail?.tipe === "privat" ? Lock : Hash;

  return (
    <>
      <ModalCore isOpen={isOpen} handleClose={onClose} position={EModalPosition.CENTER} width={EModalWidth.LG}>
        <div className="flex max-h-[80vh] flex-col">
          <h3 className="flex items-center gap-2 p-5 pb-3 text-18 font-medium text-secondary">
            <Ikon className="size-4 text-tertiary" />
            <span className="truncate">{detail?.nama ?? t("chat_ui.channel")}</span>
          </h3>

          <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 pb-4">
            {/* Nama & topik */}
            {bolehKelola ? (
              <form
                className="space-y-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  void simpan();
                }}
              >
                <label className="block space-y-1">
                  <span className="text-12 font-medium text-secondary">{t("chatux_kelola_ui.name")}</span>
                  <Input
                    value={nama}
                    onChange={(e) => setNama(e.target.value)}
                    maxLength={BATAS_NAMA}
                    className="w-full text-14"
                  />
                </label>
                <label className="block space-y-1">
                  <span className="text-12 font-medium text-secondary">{t("chatux_kelola_ui.topic")}</span>
                  <TextArea
                    value={topik}
                    onChange={(e) => setTopik(e.target.value)}
                    maxLength={BATAS_TOPIK}
                    rows={2}
                    placeholder={t("chatux_kelola_ui.topic_placeholder")}
                    className="w-full text-13"
                  />
                </label>
                <div className="flex justify-end">
                  <Button variant="primary" size="base" type="submit" loading={menyimpan} disabled={!berubah}>
                    {t("chatux_kelola_ui.save")}
                  </Button>
                </div>
              </form>
            ) : (
              <div className="space-y-1">
                <p className="text-12 font-medium text-secondary">{t("chatux_kelola_ui.topic")}</p>
                <p className="text-13 whitespace-pre-wrap text-primary">
                  {detail?.topik || t("chatux_kelola_ui.no_topic")}
                </p>
                {detail?.sistem ? (
                  <p className="text-12 text-tertiary">{t("chatux_kelola_ui.system_channel_hint")}</p>
                ) : (
                  <p className="text-12 text-tertiary">{t("chatux_kelola_ui.manage_hint")}</p>
                )}
              </div>
            )}

            {/* Undang */}
            {bolehUndang ? (
              <div className="space-y-1.5">
                <p className="flex items-center gap-1.5 text-12 font-medium text-secondary">
                  <UserPlus className="size-3.5" />
                  {t("chatux_kelola_ui.invite")}
                </p>
                <div className="flex items-center gap-2 search-field border border-subtle px-2.5 py-1.5 focus-within:border-accent-strong">
                  <Search className="size-3.5 shrink-0 text-tertiary" />
                  <Input
                    type="search"
                    mode="true-transparent"
                    value={cariUndang}
                    onChange={(e) => setCariUndang(e.target.value)}
                    placeholder={t("chatux_kelola_ui.invite_placeholder")}
                    aria-label={t("chatux_kelola_ui.invite_placeholder")}
                    className="w-full p-0 text-primary placeholder:text-placeholder"
                  />
                </div>
                {cariUndang.trim() && calon.length === 0 ? (
                  <p className="px-1 text-12 text-tertiary">{t("chat_ui.no_matching_people")}</p>
                ) : null}
                <ul>
                  {calon.map((id) => {
                    const orang = getWorkspaceMemberDetails(id)?.member;
                    return (
                      <li key={id}>
                        <button
                          type="button"
                          onClick={() => void undang(id)}
                          className="flex w-full items-center gap-2 rounded-item px-2 py-1.5 text-left hover:bg-layer-1 sentuh:py-2.5"
                        >
                          <Avatar name={orang?.display_name} src={getFileURL(orang?.avatar_url ?? "")} size={24} />
                          <span className="min-w-0 flex-1 truncate text-13 text-primary">{orang?.display_name}</span>
                          <span className="text-12 text-accent-primary">{t("chatux_kelola_ui.add")}</span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ) : null}

            {/* Anggota */}
            <div className="space-y-1">
              <p className="text-12 font-medium text-secondary">
                {t("chatux_kelola_ui.member_count", { count: anggota?.length ?? detail?.jumlah_anggota ?? 0 })}
              </p>
              <ul>
                {(anggota ?? []).map((id) => {
                  const orang = getWorkspaceMemberDetails(id)?.member;
                  const namaOrang = orang?.display_name ?? t("chat_ui.member");
                  const diriSendiri = id === saya?.id;
                  return (
                    <li key={id} className="group flex items-center gap-2.5 rounded-item px-2 py-1.5 hover:bg-layer-1">
                      <DenganKehadiran userId={id}>
                        <Avatar name={orang?.display_name} src={getFileURL(orang?.avatar_url ?? "")} size={28} />
                      </DenganKehadiran>
                      <span className="min-w-0 flex-1 truncate text-13 text-primary">
                        {diriSendiri ? `${namaOrang} (${t("chat_ui.you")})` : namaOrang}
                      </span>
                      {id === detail?.pembuat ? (
                        <span className="text-12 text-tertiary">{t("chatux_kelola_ui.creator")}</span>
                      ) : null}
                      {bolehKelola && !diriSendiri ? (
                        <IconButton
                          type="button"
                          variant="ghost"
                          size="sm"
                          icon={UserMinus}
                          data-sentuh-lega
                          onClick={() => keluarkan(id, namaOrang)}
                          aria-label={t("chatux_kelola_ui.remove_named", { name: namaOrang })}
                          title={t("chatux_kelola_ui.remove_named", { name: namaOrang })}
                          className="opacity-0 group-focus-within:opacity-100 group-hover:opacity-100 focus-visible:opacity-100 sentuh:opacity-100"
                        />
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 border-t-[0.5px] border-subtle px-5 py-4">
            <div className="flex flex-wrap items-center gap-2">
              {detail && !detail.sistem ? (
                <Button variant="secondary" size="base" prependIcon={<LogOut />} onClick={keluar}>
                  {t("chat_ui.leave_channel")}
                </Button>
              ) : null}
              {bolehKelola ? (
                <Button variant="error-outline" size="base" prependIcon={<Trash2 />} onClick={hapus}>
                  {t("chatux_kelola_ui.delete_channel")}
                </Button>
              ) : null}
            </div>
            <Button variant="secondary" size="base" onClick={onClose}>
              {t("close")}
            </Button>
          </div>
        </div>
      </ModalCore>
      {dialog}
    </>
  );
});
