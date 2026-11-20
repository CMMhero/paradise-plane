/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: penulis kanal Announcements
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Bagian dialog setelan kanal Announcements, hanya untuk admin: departemen dan
 * orang yang boleh menulis pengumuman selain admin. Server yang menjaga
 * (`chat_penulis.py`); bagian ini tidak dirender untuk selain admin.
 */

import { useMemo, useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { Building2, Megaphone, Search, X } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { IconButton } from "@plane/propel/icon-button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Avatar, Input } from "@plane/ui";
import { getFileURL } from "@plane/utils";
// hooks
import { useMember } from "@/hooks/store/use-member";
import type { TOpsiKonfirmasi } from "@/hooks/use-konfirmasi";
// services
import { ChatService } from "@/services/chat.service";
import type { TPenulisKanal } from "@/services/chat.service";

const chatService = new ChatService();
const MAKS_CALON = 8;

type Props = {
  slug: string;
  ruangId: string;
  minta: (opsi: TOpsiKonfirmasi, aksi: () => Promise<unknown> | void) => void;
};

type TCalon = { kunci: string; jenis: "departemen" | "user"; id: string; nama: string; keterangan: string };

const pesanGalat = (galat: unknown, cadangan: string) => (galat as { error?: string })?.error ?? cadangan;

export const PenulisPengumuman = observer(function PenulisPengumuman({ slug, ruangId, minta }: Props) {
  const { t } = useTranslation();
  const {
    workspace: { workspaceMemberIds, getWorkspaceMemberDetails },
  } = useMember();
  const { data, mutate } = useSWR(`CHAT_PENULIS_KANAL_${ruangId}`, () => chatService.getPenulisKanal(slug, ruangId));
  const [cari, setCari] = useState("");

  const namaPenulis = (p: TPenulisKanal) =>
    p.departemen ? p.departemen.nama : (getWorkspaceMemberDetails(p.user ?? "")?.member?.display_name ?? "");

  const calon = useMemo((): TCalon[] => {
    const q = cari.trim().toLowerCase();
    if (!q || !data) return [];
    const sudah = new Set(data.penulis.map((p) => p.departemen?.id ?? p.user ?? ""));
    const departemen = data.departemen
      .filter((d) => !sudah.has(d.id) && `${d.kode} ${d.nama}`.toLowerCase().includes(q))
      .map((d) => ({ kunci: `d-${d.id}`, jenis: "departemen" as const, id: d.id, nama: d.nama, keterangan: d.divisi }));
    const orang = (workspaceMemberIds ?? [])
      .filter((id) => !sudah.has(id))
      .map((id) => ({ id, nama: getWorkspaceMemberDetails(id)?.member?.display_name ?? "" }))
      .filter((o) => o.nama.toLowerCase().includes(q))
      .map((o) => ({ kunci: `u-${o.id}`, jenis: "user" as const, id: o.id, nama: o.nama, keterangan: "" }));
    return [...departemen, ...orang].slice(0, MAKS_CALON);
  }, [cari, data, workspaceMemberIds, getWorkspaceMemberDetails]);

  const tambah = async (c: TCalon) => {
    try {
      await chatService.tambahPenulisKanal(
        slug,
        ruangId,
        c.jenis === "departemen" ? { departemen_id: c.id } : { user_id: c.id }
      );
      setCari("");
      await mutate();
    } catch (galat) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("obrolan_p29.writers_add_failed"),
        message: pesanGalat(galat, t("chat_ui.try_again_shortly")),
      });
    }
  };

  const cabut = (p: TPenulisKanal) => {
    const nama = namaPenulis(p);
    minta(
      {
        judul: t("obrolan_p29.writers_confirm_remove_title"),
        isi: t("obrolan_p29.writers_confirm_remove_body", { name: nama }),
        tombol: t("obrolan_p29.writers_remove"),
        tombolProses: t("obrolan_p29.writers_removing"),
      },
      async () => {
        try {
          await chatService.cabutPenulisKanal(slug, ruangId, p.id);
          await mutate();
        } catch (galat) {
          setToast({
            type: TOAST_TYPE.ERROR,
            title: t("obrolan_p29.writers_remove_failed"),
            message: pesanGalat(galat, t("chat_ui.try_again_shortly")),
          });
        }
      }
    );
  };

  return (
    <div className="space-y-1.5">
      <p className="flex items-center gap-1.5 text-12 font-medium text-secondary">
        <Megaphone className="size-3.5" />
        {t("obrolan_p29.writers_title")}
      </p>
      <p className="text-12 text-tertiary">{t("obrolan_p29.writers_hint")}</p>

      <ul>
        {data && data.penulis.length === 0 ? (
          <li className="px-2 py-1.5 text-12 text-tertiary">{t("obrolan_p29.writers_empty")}</li>
        ) : null}
        {(data?.penulis ?? []).map((p) => {
          const nama = namaPenulis(p);
          const orang = p.user ? getWorkspaceMemberDetails(p.user)?.member : undefined;
          return (
            <li key={p.id} className="group flex items-center gap-2.5 rounded-item px-2 py-1.5 hover:bg-layer-1">
              {p.departemen ? (
                <span className="grid size-7 shrink-0 place-items-center rounded-full bg-layer-2 text-tertiary">
                  <Building2 className="size-3.5" />
                </span>
              ) : (
                <Avatar name={orang?.display_name} src={getFileURL(orang?.avatar_url ?? "")} size={28} />
              )}
              <span className="min-w-0 flex-1 truncate text-13 text-primary">{nama}</span>
              <span className="text-12 text-tertiary">
                {p.departemen ? t("obrolan_p29.writers_department") : t("obrolan_p29.writers_person")}
              </span>
              <IconButton
                type="button"
                variant="ghost"
                size="sm"
                icon={X}
                data-sentuh-lega
                onClick={() => cabut(p)}
                aria-label={t("obrolan_p29.writers_remove_named", { name: nama })}
                title={t("obrolan_p29.writers_remove_named", { name: nama })}
              />
            </li>
          );
        })}
      </ul>

      <div className="flex items-center gap-2 search-field border border-subtle px-2.5 py-1.5 focus-within:border-accent-strong">
        <Search className="size-3.5 shrink-0 text-tertiary" />
        <Input
          type="search"
          mode="true-transparent"
          value={cari}
          onChange={(e) => setCari(e.target.value)}
          placeholder={t("obrolan_p29.writers_add_placeholder")}
          aria-label={t("obrolan_p29.writers_add_placeholder")}
          className="w-full p-0 text-primary placeholder:text-placeholder"
        />
      </div>
      {cari.trim() && calon.length === 0 ? (
        <p className="px-1 text-12 text-tertiary">{t("obrolan_p29.writers_no_match")}</p>
      ) : null}
      <ul>
        {calon.map((c) => (
          <li key={c.kunci}>
            <button
              type="button"
              onClick={() => void tambah(c)}
              className="flex w-full items-center gap-2 rounded-item px-2 py-1.5 text-left hover:bg-layer-1 sentuh:py-2.5"
            >
              {c.jenis === "departemen" ? (
                <Building2 className="size-4 shrink-0 text-tertiary" />
              ) : (
                <Avatar
                  name={c.nama}
                  src={getFileURL(getWorkspaceMemberDetails(c.id)?.member?.avatar_url ?? "")}
                  size={24}
                />
              )}
              <span className="min-w-0 flex-1 truncate text-13 text-primary">{c.nama}</span>
              {c.keterangan ? <span className="text-12 text-tertiary">{c.keterangan}</span> : null}
              <span className="text-12 text-accent-primary">{t("obrolan_p29.writers_add")}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
});
