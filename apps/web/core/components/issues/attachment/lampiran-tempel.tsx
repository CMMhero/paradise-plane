/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tempel/seret berkas ke komentar atau deskripsi = lampiran work item
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { observer } from "mobx-react";
import { Loader2, Paperclip, X } from "lucide-react";
import type { TAttachedFile } from "@plane/editor";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { getFileURL } from "@plane/utils";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useFileSize } from "@/hooks/use-file-size";
import { useUploadFailureText } from "@/hooks/use-upload-error-reporter";

const BYTES_PER_MB = 1024 * 1024;

type TLampiranGagal = { id: string; pesan: string };

/**
 * Berkas non-gambar yang ditempel atau diseret ke kotak komentar atau deskripsi diunggah
 * sebagai LAMPIRAN WORK ITEM (layanan & batas ukuran yang sama dengan bagian
 * Attachments), lalu editor menyisipkan tautan ke tiap berkas di teksnya.
 *
 * Kenapa bukan aset editor: backend hanya menerima GAMBAR untuk
 * COMMENT_DESCRIPTION dan ISSUE_DESCRIPTION, jadi PDF yang ditempel dulu jadi
 * kartu berkas yang unggahannya ditolak. Sebagai
 * lampiran work item, berkas juga muncul di daftar Attachments dan ikut
 * terhitung di kartu, di mana orang memang mencarinya.
 *
 * Progres unggah dibaca dari store lampiran (yang sama dipakai daftar
 * Attachments); kegagalan disimpan lokal supaya tetap terlihat sampai ditutup.
 */
export const useLampiranTempel = (workspaceSlug: string, projectId: string, issueId: string) => {
  const { t } = useTranslation();
  const {
    attachment: { createAttachment },
  } = useIssueDetail();
  const { maxFileSize } = useFileSize();
  const describeUploadFailure = useUploadFailureText();
  const [gagal, setGagal] = useState<TLampiranGagal[]>([]);
  // files this editor is uploading right now, to pick their rows out of the
  // issue-wide upload status (the Attachments widget may be uploading too)
  const [menunggu, setMenunggu] = useState<File[]>([]);

  const catatGagal = useCallback((pesan: string) => {
    setGagal((sebelumnya) => [...sebelumnya, { id: `${Date.now()}-${Math.random()}`, pesan }]);
  }, []);

  const tutupGagal = useCallback((id: string) => {
    setGagal((sebelumnya) => sebelumnya.filter((item) => item.id !== id));
  }, []);

  const unggah = useCallback(
    async (files: File[]): Promise<TAttachedFile[]> => {
      const hasil = await Promise.all(
        files.map(async (file): Promise<TAttachedFile | null> => {
          if (file.size > maxFileSize) {
            catatGagal(
              t("navigasi_lampiran_ui.too_large", {
                name: file.name,
                size: Math.round(maxFileSize / BYTES_PER_MB),
              })
            );
            return null;
          }
          setMenunggu((sebelumnya) => [...sebelumnya, file]);
          try {
            const lampiran = await createAttachment(workspaceSlug, projectId, issueId, file);
            const url = getFileURL(lampiran?.asset_url ?? "");
            return url ? { name: file.name, url } : null;
          } catch (error) {
            // say WHY (offline, type, server...) instead of one fixed sentence
            const alasan = describeUploadFailure(error, { name: file.name });
            if (!alasan.isCancelled)
              catatGagal(`${t("navigasi_lampiran_ui.failed", { name: file.name })} · ${alasan.message}`);
            return null;
          } finally {
            setMenunggu((sebelumnya) => sebelumnya.filter((item) => item !== file));
          }
        })
      );

      const berhasil = hasil.filter((item): item is TAttachedFile => !!item);
      if (berhasil.length > 0) {
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: t("navigasi_lampiran_ui.attached", { names: berhasil.map((item) => item.name).join(", ") }),
        });
      }
      return berhasil;
    },
    [catatGagal, createAttachment, describeUploadFailure, issueId, maxFileSize, projectId, t, workspaceSlug]
  );

  // The editor builds its paste/drop plugin once and keeps the handler it got
  // at creation. Hand it a stable function that always calls the latest one,
  // so a late instance config (size limit) or a new issue is never missed.
  const unggahTerbaru = useRef(unggah);
  useEffect(() => {
    unggahTerbaru.current = unggah;
  }, [unggah]);
  const attachFiles = useCallback((files: File[]) => unggahTerbaru.current(files), []);

  const status = useMemo<TStatusProps>(
    () => ({ issueId, gagal, menunggu, onTutupGagal: tutupGagal }),
    [issueId, gagal, menunggu, tutupGagal]
  );

  return { attachFiles, status };
};

type TStatusProps = {
  issueId: string;
  gagal: TLampiranGagal[];
  menunggu: File[];
  onTutupGagal: (id: string) => void;
};

/** Baris status di bawah editor: progres unggah dan kegagalan. */
export const StatusLampiranTempel = observer(function StatusLampiranTempel(props: TStatusProps) {
  const { issueId, gagal, menunggu, onTutupGagal } = props;
  const { t } = useTranslation();
  const {
    attachment: { getAttachmentsUploadStatusByIssueId },
  } = useIssueDetail();
  // only the uploads started from this editor, matched by name and size
  const sedangUnggah = (getAttachmentsUploadStatusByIssueId(issueId) ?? []).filter((item) =>
    menunggu.some((file) => file.name === item.name && file.size === item.size)
  );

  if (sedangUnggah.length === 0 && gagal.length === 0) return null;

  return (
    <ul className="mt-2 flex flex-col gap-1" aria-live="polite">
      {sedangUnggah.map((item) => (
        <li key={item.id} className="flex items-center gap-2 rounded-md bg-layer-1 px-2 py-1 text-12 text-secondary">
          <Loader2 className="size-3.5 shrink-0 animate-spin" aria-hidden />
          <span className="min-w-0 flex-1 truncate">{t("navigasi_lampiran_ui.uploading", { name: item.name })}</span>
          <span className="shrink-0 tabular-nums">{item.progress}%</span>
          <span className="h-1 w-16 shrink-0 overflow-hidden rounded-full bg-layer-3" aria-hidden>
            <span className="block h-full bg-accent-primary" style={{ width: `${item.progress}%` }} />
          </span>
        </li>
      ))}
      {gagal.map((item) => (
        <li
          key={item.id}
          role="alert"
          className="flex items-center gap-2 rounded-md bg-danger-subtle px-2 py-1 text-12 text-danger-primary"
        >
          <Paperclip className="size-3.5 shrink-0" aria-hidden />
          <span className="min-w-0 flex-1 truncate">{item.pesan}</span>
          <button
            type="button"
            onClick={() => onTutupGagal(item.id)}
            className="grid size-6 shrink-0 place-items-center rounded-sm hover:bg-danger-subtle sentuh:size-9"
            aria-label={t("navigasi_lampiran_ui.dismiss")}
          >
            <X className="size-3.5" />
          </button>
        </li>
      ))}
    </ul>
  );
});
