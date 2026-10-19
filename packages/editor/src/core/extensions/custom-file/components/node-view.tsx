/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: node berkas non-gambar
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { NodeViewWrapper } from "@tiptap/react";
import type { NodeViewProps } from "@tiptap/react";
import { ChevronDown, ChevronRight, Download, Paperclip } from "lucide-react";
import type { ChangeEvent } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
// plane imports
import { cn } from "@plane/utils";
// constants
import { ACCEPTED_ATTACHMENT_MIME_TYPES } from "@/constants/config";
// helpers
import type { EFileError } from "@/helpers/file";
// hooks
import { useUploader, useDropZone } from "@/hooks/use-file-upload";
// local imports
import type { CustomFileExtensionType, TCustomFileAttributes } from "../types";
import {
  formatFileSize,
  getFileComponentFileMap,
  getFileComponentMaxFileSize,
  getFilePreviewKind,
  resolveFileMimeType,
  toInlineSrc,
} from "../utils";

/** tinggi bingkai pratinjau, px */
const FRAME_HEIGHT_COLLAPSED = 420;
const FRAME_HEIGHT_EXPANDED = 800;

export type CustomFileNodeViewProps = Omit<NodeViewProps, "extension" | "updateAttributes"> & {
  extension: CustomFileExtensionType;
  node: NodeViewProps["node"] & {
    attrs: TCustomFileAttributes;
  };
  updateAttributes: (attrs: Partial<TCustomFileAttributes>) => void;
};

export function CustomFileNodeView(props: CustomFileNodeViewProps) {
  const { editor, extension, getPos, node, selected, updateAttributes } = props;
  const { id: fileEntityId, name, size, src, type } = node.attrs;
  // states
  const [downloadSrc, setDownloadSrc] = useState<string | undefined>(undefined);
  const [viewSrc, setViewSrc] = useState<string | undefined>(undefined);
  const [isPreviewOpen, setIsPreviewOpen] = useState(true);
  const [isFrameExpanded, setIsFrameExpanded] = useState(false);
  const [hasFailed, setHasFailed] = useState(false);
  // refs
  const fileInputRef = useRef<HTMLInputElement>(null);
  const hasTriggeredFilePickerRef = useRef(false);
  const hasTriedUploadingOnMountRef = useRef(false);
  // derived values
  const fileComponentFileMap = useMemo(() => getFileComponentFileMap(editor), [editor]);
  const isTouchDevice = !!editor.storage.utility.isTouchDevice;
  const isUploaded = !!src;

  // resolve both URLs once the asset exists: one forces a download (the button),
  // the other renders in place (player / frame). The card itself renders from the
  // stored name/size, so neither is needed just to show the row.
  useEffect(() => {
    if (!src) {
      setDownloadSrc(undefined);
      setViewSrc(undefined);
      return;
    }
    let isStale = false;
    const resolveSources = async () => {
      try {
        const [download, view] = await Promise.all([
          extension.options.getFileDownloadSource?.(src),
          extension.options.getFileSource?.(src),
        ]);
        if (isStale) return;
        setDownloadSrc(download);
        setViewSrc(view);
      } catch (error) {
        console.error("Error resolving file sources:", error);
        if (!isStale) setHasFailed(true);
      }
    };
    void resolveSources();
    return () => {
      isStale = true;
    };
  }, [src, extension.options]);

  const onUpload = useCallback(
    (url: string, file: File) => {
      if (!url || !fileEntityId) return;
      // name and size are stored on the node so the card can render without a
      // round trip, and still reads correctly if the asset later 404s
      updateAttributes({
        src: url,
        name: file.name,
        size: file.size,
        // MIME disimpan saat unggah supaya bentuk pratinjau tidak perlu ditebak
        // dari ekstensi setiap kali halaman dibuka
        type: file.type || null,
      });
      fileComponentFileMap?.delete(fileEntityId);
    },
    [fileComponentFileMap, fileEntityId, updateAttributes]
  );

  const uploadFileEditorCommand = useCallback(
    async (file: File) => await extension.options.uploadFile?.(fileEntityId ?? "", file),
    [extension.options, fileEntityId]
  );

  const handleProgressStatus = useCallback(
    (isUploading: boolean) => {
      editor.storage.utility.uploadInProgress = isUploading;
    },
    [editor]
  );

  const handleInvalidFile = useCallback((_error: EFileError, _file: File, message: string) => {
    alert(message);
  }, []);

  const { isUploading, uploadFile } = useUploader({
    acceptedMimeTypes: ACCEPTED_ATTACHMENT_MIME_TYPES,
    editorCommand: uploadFileEditorCommand,
    handleProgressStatus,
    maxFileSize: getFileComponentMaxFileSize(editor),
    onInvalidFile: handleInvalidFile,
    onUpload,
  });

  const { draggedInside, onDrop, onDragEnter, onDragLeave } = useDropZone({
    editor,
    getPos,
    // "attachment" is the upstream name for every non-image file
    type: "attachment",
    uploader: uploadFile,
  });

  // open the picker (or start the drop upload) once the node mounts, so a slash
  // command lands the user straight in the file dialog
  useEffect(() => {
    if (hasTriedUploadingOnMountRef.current) return;

    const meta = fileComponentFileMap?.get(fileEntityId ?? "");
    if (!meta) {
      hasTriedUploadingOnMountRef.current = true;
      return;
    }
    if (meta.event === "drop" && "file" in meta) {
      hasTriedUploadingOnMountRef.current = true;
      void uploadFile(meta.file);
    } else if (meta.event === "insert" && fileInputRef.current && !hasTriggeredFilePickerRef.current) {
      if (meta.hasOpenedFileInputOnce) return;
      // a touch device shows its own sheet; forcing a click there is disruptive
      if (!isTouchDevice) fileInputRef.current.click();
      hasTriggeredFilePickerRef.current = true;
      fileComponentFileMap?.set(fileEntityId ?? "", { ...meta, hasOpenedFileInputOnce: true });
    }
  }, [fileEntityId, fileComponentFileMap, isTouchDevice, uploadFile]);

  const onFileChange = useCallback(
    async (e: ChangeEvent<HTMLInputElement>) => {
      e.preventDefault();
      const selectedFile = e.target.files?.[0];
      if (!selectedFile) return;
      await uploadFile(selectedFile);
    },
    [uploadFile]
  );

  const handleDownload = useCallback(() => {
    if (!downloadSrc) return;
    // noopener/noreferrer: the asset URL is presigned and points at storage we
    // do not want handed window.opener
    window.open(downloadSrc, "_blank", "noopener,noreferrer");
  }, [downloadSrc]);

  // ---- uploaded state: card header + in-place preview ----
  if (isUploaded) {
    const mimeType = resolveFileMimeType(type, name);
    const previewKind = getFilePreviewKind(mimeType);
    const canPreview = previewKind !== "none" && !!viewSrc && !hasFailed;
    // iframe memuat lewat navigasi, jadi ia butuh disposition=inline; <video>,
    // <audio> dan <img> mengabaikan header itu dan boleh pakai URL apa adanya
    const inlineSrc = viewSrc ? toInlineSrc(viewSrc) : undefined;
    const isFramed = previewKind === "pdf" || previewKind === "text";
    const frameTitle = name || "Pratinjau berkas";

    return (
      <NodeViewWrapper>
        <div
          className={cn("file-component my-2 overflow-hidden rounded-lg border border-subtle bg-layer-2", {
            "border-accent-strong": selected,
            "border-danger-strong bg-danger-subtle": hasFailed,
          })}
          contentEditable={false}
        >
          {/* baris judul */}
          <div className="flex items-center gap-3 px-3 py-2.5">
            {canPreview ? (
              <button
                type="button"
                onClick={() => setIsPreviewOpen((prev) => !prev)}
                className="grid size-4 shrink-0 place-items-center rounded text-tertiary hover:text-secondary"
                aria-expanded={isPreviewOpen}
                aria-label={isPreviewOpen ? "Sembunyikan pratinjau" : "Tampilkan pratinjau"}
              >
                {isPreviewOpen ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
              </button>
            ) : (
              <Paperclip className="size-4 shrink-0 text-tertiary" />
            )}
            <div className="flex min-w-0 flex-1 flex-col">
              <span className="truncate text-14 font-medium text-primary" title={name ?? undefined}>
                {name || "Untitled file"}
              </span>
              <span className="text-11 text-tertiary">
                {size !== null && formatFileSize(size)}
                {/* dikatakan terus terang, bukan dibiarkan jadi kartu kosong
                    yang bikin orang mengira pratinjaunya rusak */}
                {previewKind === "none" && " · tidak bisa dipratinjau di web"}
              </span>
            </div>
            {isFramed && isPreviewOpen && (
              <button
                type="button"
                onClick={() => setIsFrameExpanded((prev) => !prev)}
                className="shrink-0 rounded-md px-2 py-1 text-12 font-medium text-secondary hover:bg-layer-3-hover hover:text-primary"
              >
                {isFrameExpanded ? "Perkecil" : "Perbesar"}
              </button>
            )}
            <button
              type="button"
              onClick={handleDownload}
              disabled={!downloadSrc}
              className="flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-12 font-medium text-secondary transition-all duration-200 ease-in-out hover:bg-layer-3-hover hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
              aria-label={`Download ${name || "file"}`}
            >
              <Download className="size-3.5" />
              <span>Download</span>
            </button>
          </div>

          {/* pratinjau */}
          {canPreview && isPreviewOpen && (
            <div className="border-t border-subtle bg-layer-1">
              {previewKind === "video" && (
                // preload="metadata": jangan tarik seluruh video sampai
                // ditonton - satu halaman bisa memuat beberapa lampiran
                // ponytail: tanpa <track> caption. Menyisipkan track kosong cuma
                // menyenangkan linter tanpa menolong siapa pun - caption untuk
                // video unggahan user butuh berkas .vtt tersendiri, itu fitur
                // terpisah kalau memang dibutuhkan.
                // oxlint-disable-next-line jsx-a11y/media-has-caption
                <video src={viewSrc} controls preload="metadata" className="max-h-[480px] w-full bg-black" />
              )}
              {/* oxlint-disable-next-line jsx-a11y/media-has-caption -- lihat alasan di atas */}
              {previewKind === "audio" && <audio src={viewSrc} controls preload="metadata" className="w-full p-3" />}
              {previewKind === "image" && (
                <img src={viewSrc} alt={name ?? "Lampiran"} className="max-h-[480px] w-full object-contain" />
              )}
              {isFramed && (
                <iframe
                  src={inlineSrc}
                  title={frameTitle}
                  // Chrome MENOLAK memuat viewer PDF bawaannya di iframe
                  // ber-sandbox, token apa pun - diuji bertiga (allow-same-origin,
                  // allow-scripts, dan keduanya): semuanya membalas ikon dokumen
                  // rusak, hanya iframe tanpa atribut sandbox yang render. Jadi
                  // khusus PDF atributnya dilepas. Risikonya kecil: MinIO membalas
                  // Content-Type application/pdf dan Chrome tidak menebak ulang
                  // tipe definitif itu jadi HTML, jadi yang jalan adalah viewer
                  // PDF - bukan dokumen yang bisa menjalankan skrip.
                  // Berkas teks tidak punya batasan itu, jadi justru dikunci
                  // penuh (sandbox="") - lebih ketat dari allow-same-origin dan
                  // tetap terbaca.
                  sandbox={previewKind === "pdf" ? undefined : ""}
                  className="w-full bg-white"
                  style={{ height: isFrameExpanded ? FRAME_HEIGHT_EXPANDED : FRAME_HEIGHT_COLLAPSED }}
                />
              )}
            </div>
          )}
        </div>
      </NodeViewWrapper>
    );
  }

  // ---- pending / uploading state: the drop zone ----
  const displayMessage = isUploading
    ? "Uploading..."
    : draggedInside && editor.isEditable
      ? "Drop file here"
      : "Add a file";

  return (
    <NodeViewWrapper>
      {/* the drop target stays a plain <div> because useDropZone types its
          handlers to HTMLDivElement; the clickable part is a real <button> so a
          keyboard-only user can still reach the file picker */}
      <div onDrop={onDrop} onDragOver={onDragEnter} onDragLeave={onDragLeave} contentEditable={false}>
        <button
          type="button"
          disabled={!editor.isEditable}
          className={cn(
            "file-upload-component my-2 flex w-full cursor-default items-center justify-start gap-2 rounded-lg border border-dashed border-subtle bg-layer-3 px-2 py-3 text-left text-tertiary transition-all duration-200 ease-in-out",
            {
              "cursor-pointer hover:bg-layer-3-hover hover:text-secondary": editor.isEditable,
              "bg-layer-3-hover text-secondary": draggedInside && editor.isEditable,
              "bg-accent-primary/10 text-accent-secondary": selected && editor.isEditable,
            }
          )}
          onClick={() => fileInputRef.current?.click()}
        >
          <Paperclip className="size-4 shrink-0" />
          <span className="flex-1 text-14 font-medium">{displayMessage}</span>
          <input
            className="size-0 overflow-hidden"
            ref={fileInputRef}
            hidden
            type="file"
            accept={ACCEPTED_ATTACHMENT_MIME_TYPES.join(",")}
            onChange={onFileChange}
          />
        </button>
      </div>
    </NodeViewWrapper>
  );
}
