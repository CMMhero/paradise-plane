/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: aksi satu klik di kartu "Needs attention"
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Tiap aksi memakai jalur yang sama dengan layar aslinya (persetujuan,
 * PATCH work item, komentar, notifikasi), jadi aturan server tidak ditulis ulang
 * di sini. `onAct` (dari root) menjalankan aksinya dengan pembaruan optimistis
 * dan mengembalikan false kalau gagal; pesan galatnya sudah ditampilkan.
 */

import { useState } from "react";
import { Check, X } from "lucide-react";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { Input } from "@plane/propel/input";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
// components
import { pesanGagalPersetujuan, usePutuskanPersetujuan } from "@/components/issues/approval-actions";
// hooks
import { useAturanInstance, useBolehPercakapanTugas, useBolehUbahTugas } from "@/hooks/use-aturan-tugas";
// services
import { IssueService } from "@/services/issue/issue.service";
import { IssueCommentService } from "@/services/issue/issue_comment.service";
import { ProjectStateService } from "@/services/project/project-state.service";
import { WorkspaceNotificationService } from "@/services/workspace-notification.service";
import type { TAttentionGroupKey, TAttentionItem } from "@/services/attention.service";
// local
import { removeItem, updateItem } from "./data";
import type { TAttentionPatch } from "./data";

const issueService = new IssueService();
const commentService = new IssueCommentService();
const stateService = new ProjectStateService();
const notificationService = new WorkspaceNotificationService();

export type TOnAct = (patch: TAttentionPatch | null, run: () => Promise<boolean>) => Promise<boolean>;

type TActionProps = {
  workspaceSlug: string;
  groupKey: TAttentionGroupKey;
  item: TAttentionItem;
  onAct: TOnAct;
};

/** Fokus ke kolom yang baru dibuka, supaya pemakai keyboard tidak harus mencarinya. */
const foco = (el: HTMLElement | null) => el?.focus();

const escapeHtml = (teks: string) =>
  teks.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

const toastGagal = (err: unknown, fallback: string) =>
  setToast({
    type: TOAST_TYPE.ERROR,
    title: fallback,
    message: pesanGagalPersetujuan(err, fallback),
  });

/** Setujui langsung; Tolak membuka satu baris alasan di tempat, bukan dialog. */
export function DecideActions({ workspaceSlug, groupKey, item, onAct }: TActionProps) {
  const { t } = useTranslation();
  const { putuskan, prosesId } = usePutuskanPersetujuan();
  const { alasan_tolak_wajib: alasanWajib } = useAturanInstance(workspaceSlug, item.project_id);
  const [menolak, setMenolak] = useState(false);
  const [alasan, setAlasan] = useState("");
  const approvalId = item.approval_id;
  if (!approvalId) return null;
  const baris = { id: approvalId, tugas: { id: item.id, nomor: item.identifier, judul: item.name } };
  const sibuk = prosesId === approvalId;

  const putus = (aksi: "setujui" | "tolak") =>
    onAct(removeItem(groupKey, item.key), () =>
      putuskan(workspaceSlug, item.project_id, baris, aksi, aksi === "tolak" ? alasan : "")
    );

  return (
    <>
      <Button
        variant="primary"
        size="sm"
        loading={sibuk}
        onClick={() => void putus("setujui")}
        prependIcon={<Check aria-hidden />}
        aria-label={`${t("perhatian_aksi.approve")} ${item.identifier}`}
      >
        {t("perhatian_aksi.approve")}
      </Button>
      <Button
        variant="error-outline"
        size="sm"
        disabled={sibuk}
        aria-expanded={menolak}
        onClick={() => setMenolak((v) => !v)}
        prependIcon={<X aria-hidden />}
        aria-label={`${t("perhatian_aksi.reject")} ${item.identifier}`}
      >
        {t("perhatian_aksi.reject")}
      </Button>
      {menolak && (
        <form
          className="flex w-full items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (alasanWajib && !alasan.trim()) return;
            void putus("tolak");
          }}
        >
          <Input
            ref={foco}
            value={alasan}
            maxLength={2000}
            required={alasanWajib}
            onChange={(e) => setAlasan(e.target.value)}
            placeholder={alasanWajib ? t("perhatian_aksi.reject_reason") : t("perhatian_aksi.reject_reason_optional")}
            aria-label={`${alasanWajib ? t("perhatian_aksi.reject_reason") : t("perhatian_aksi.reject_reason_optional")} ${item.identifier}`}
            className="min-w-0 flex-1"
            inputSize="xs"
          />
          <Button type="submit" variant="error-fill" size="sm" loading={sibuk} disabled={alasanWajib && !alasan.trim()}>
            {t("perhatian_aksi.reject_confirm")}
          </Button>
        </form>
      )}
    </>
  );
}

/** Pemilih status terbatas pada status project tugas ini; server yang menahan perpindahan ke Done. */
export function StateAction({ workspaceSlug, groupKey, item, onAct }: TActionProps) {
  const { t } = useTranslation();
  const [terbuka, setTerbuka] = useState(false);
  const bolehUbah = useBolehUbahTugas(workspaceSlug, item.project_id, item);
  const { data: states, error } = useSWR(terbuka ? `ATTENTION_STATES_${workspaceSlug}_${item.project_id}` : null, () =>
    stateService.getStates(workspaceSlug, item.project_id)
  );
  if (!bolehUbah || item.state_group === "completed") return null;

  const pindah = (stateId: string) => {
    const tujuan = states?.find((s) => s.id === stateId);
    if (!tujuan || stateId === item.state_id) return;
    // Ke Done: server bisa menahannya sebagai pengajuan, jadi kartu tidak ditebak.
    const patch =
      tujuan.group === "completed"
        ? null
        : updateItem(groupKey, item.key, {
            state_id: tujuan.id,
            state_name: tujuan.name,
            state_group: tujuan.group,
          });
    void onAct(patch, async () => {
      try {
        const hasil = await issueService.patchIssue(workspaceSlug, item.project_id, item.id, { state_id: stateId });
        if (hasil?.approval_requested) {
          setToast({
            type: TOAST_TYPE.SUCCESS,
            title: t("issue.approval.toast.requested_title"),
            message: t("issue.approval.toast.requested_message"),
          });
        } else {
          setToast({
            type: TOAST_TYPE.SUCCESS,
            title: t("perhatian_aksi.state_changed_title"),
            message: t("perhatian_aksi.state_changed_message", { number: item.identifier, state: tujuan.name }),
          });
        }
        setTerbuka(false);
        return true;
      } catch (err) {
        toastGagal(err, t("perhatian_aksi.failed"));
        return false;
      }
    });
  };

  return terbuka ? (
    <select
      ref={foco}
      value={item.state_id ?? ""}
      disabled={!states}
      onChange={(e) => pindah(e.target.value)}
      onBlur={() => setTerbuka(false)}
      aria-label={t("perhatian_aksi.state_label", { number: item.identifier })}
      className="h-6 max-w-40 rounded-field border-[0.5px] border-subtle-1 bg-layer-2 px-1.5 text-12 text-primary"
    >
      {!states && (
        <option value="">{error ? t("perhatian_aksi.states_failed") : t("perhatian_aksi.states_loading")}</option>
      )}
      {(states ?? []).map((s) => (
        <option key={s.id} value={s.id}>
          {s.name}
        </option>
      ))}
    </select>
  ) : (
    <Button
      variant="secondary"
      size="sm"
      onClick={() => setTerbuka(true)}
      aria-label={`${t("perhatian_aksi.change_state")} ${item.identifier}`}
    >
      {t("perhatian_aksi.change_state")}
    </Button>
  );
}

/** Tandai notifikasi sebutan dibaca lewat API inbox yang sama dengan layar Notifikasi. */
export const tandaiDibaca = async (workspaceSlug: string, notificationId: string | null | undefined) => {
  if (notificationId) await notificationService.markNotificationAsRead(workspaceSlug, notificationId);
};

/** Satu baris balasan; menempel ke komentar yang menyebut saya, atau komentar biasa kalau sebutannya di deskripsi. */
export function ReplyAction({ workspaceSlug, groupKey, item, onAct }: TActionProps) {
  const { t } = useTranslation();
  const bolehBalas = useBolehPercakapanTugas(workspaceSlug, item.project_id, item);
  const [terbuka, setTerbuka] = useState(false);
  const [teks, setTeks] = useState("");
  if (!bolehBalas) return null;
  const nama = item.mentioned_by ?? item.identifier;

  const kirim = () => {
    const isi = teks.trim();
    if (!isi) return;
    void onAct(removeItem(groupKey, item.key), async () => {
      try {
        await commentService.createIssueComment(workspaceSlug, item.project_id, item.id, {
          comment_html: `<p class="editor-paragraph-block">${escapeHtml(isi)}</p>`,
          ...(item.comment_id ? { parent: item.comment_id } : {}),
        });
      } catch (err) {
        toastGagal(err, t("perhatian_aksi.failed"));
        return false;
      }
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("perhatian_aksi.reply_sent_title"),
        message: t("perhatian_aksi.reply_sent_message", { number: item.identifier }),
      });
      // Membalas berarti sudah ditangani; gagal menandai dibaca tidak membatalkan balasan.
      await tandaiDibaca(workspaceSlug, item.notification_id).catch(() => undefined);
      return true;
    });
  };

  return terbuka ? (
    <form
      className="flex w-full items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        kirim();
      }}
    >
      <Input
        ref={foco}
        value={teks}
        maxLength={1000}
        onChange={(e) => setTeks(e.target.value)}
        placeholder={t("perhatian_aksi.reply_placeholder")}
        aria-label={t("perhatian_aksi.reply_label", { name: nama })}
        className="min-w-0 flex-1"
        inputSize="xs"
      />
      <Button type="submit" variant="primary" size="sm" disabled={!teks.trim()}>
        {t("perhatian_aksi.reply_send")}
      </Button>
    </form>
  ) : (
    <Button
      variant="secondary"
      size="sm"
      onClick={() => setTerbuka(true)}
      aria-label={`${t("perhatian_aksi.reply")} ${item.identifier}`}
    >
      {t("perhatian_aksi.reply")}
    </Button>
  );
}
