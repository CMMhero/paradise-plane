/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useMemo } from "react";
// plane imports
import { API_BASE_URL } from "@plane/constants";
import type { TFileCardLabels, TFileHandler } from "@plane/editor";
import { useTranslation } from "@plane/i18n";
import { getEditorAssetDownloadSrc, getEditorAssetSrc, getFileURL } from "@plane/utils";
// components
import { resolveAttachmentLink } from "@/components/issues/attachment/tautan-lampiran";
// hooks
import { useEditorAsset } from "@/hooks/store/use-editor-asset";
// plane web hooks
import { useExtendedEditorConfig } from "@/hooks/editor/use-extended-editor-config";
import { useFileSize } from "@/hooks/use-file-size";
import { useUploadErrorReporter } from "@/hooks/use-upload-error-reporter";
// services
import { FileService } from "@/services/file.service";
const fileService = new FileService();

/**
 * Full URLs and API paths (work item attachments) pass through; anything else is an editor asset id.
 * `//host` and `/\host` are protocol-relative to browsers, so they would load from another site.
 */
const isUrlOrPath = (path: string) => /^https?:\/\//i.test(path) || /^\/(?![/\\])/.test(path);

const resolveAttachmentLinkHere = (href: string) =>
  resolveAttachmentLink(href, { apiBaseUrl: API_BASE_URL, pageOrigin: window.location.origin });

type TArgs = {
  projectId?: string;
  uploadFile: TFileHandler["upload"];
  duplicateFile: TFileHandler["duplicate"];
  /** Paradise: non-image paste/drop goes to the host, see TFileHandler.attachFiles */
  attachFiles?: TFileHandler["attachFiles"];
  workspaceId: string;
  workspaceSlug: string;
};

export const useEditorConfig = () => {
  // store hooks
  const { assetsUploadPercentage } = useEditorAsset();
  // file size
  const { maxFileSize } = useFileSize();
  const reportUploadError = useUploadErrorReporter();
  const { getExtendedEditorFileHandlers } = useExtendedEditorConfig();
  const { t } = useTranslation();
  const fileCardLabels = useMemo<TFileCardLabels>(
    () => ({
      download: t("file_card.download"),
      showPreview: t("file_card.show_preview"),
      hidePreview: t("file_card.hide_preview"),
      expand: t("file_card.expand"),
      collapse: t("file_card.collapse"),
      noPreview: t("file_card.no_preview"),
      untitled: t("file_card.untitled"),
    }),
    [t]
  );

  const getEditorFileHandlers = useCallback(
    (args: TArgs): TFileHandler => {
      const { projectId, uploadFile, duplicateFile, attachFiles, workspaceId, workspaceSlug } = args;

      return {
        assetsUploadStatus: assetsUploadPercentage,
        cancel: fileService.cancelUpload,
        checkIfAssetExists: async (assetId: string) => {
          const res = await fileService.checkIfAssetExists(workspaceSlug, assetId);
          return res?.exists ?? false;
        },
        delete: async (src: string) => {
          if (src?.startsWith("http")) {
            await fileService.deleteOldWorkspaceAsset(workspaceId, src);
          } else {
            await fileService.deleteNewAsset(
              getEditorAssetSrc({
                assetId: src,
                projectId,
                workspaceSlug,
              }) ?? ""
            );
          }
        },
        getAssetDownloadSrc: async (path) => {
          if (!path) return "";
          if (isUrlOrPath(path)) {
            return getFileURL(path) ?? "";
          } else {
            return (
              getEditorAssetDownloadSrc({
                assetId: path,
                projectId,
                workspaceSlug,
              }) ?? ""
            );
          }
        },
        getAssetSrc: async (path) => {
          if (!path) return "";
          if (isUrlOrPath(path)) {
            return getFileURL(path) ?? "";
          } else {
            return (
              getEditorAssetSrc({
                assetId: path,
                projectId,
                workspaceSlug,
              }) ?? ""
            );
          }
        },
        restore: async (src: string) => {
          if (src?.startsWith("http")) {
            await fileService.restoreOldEditorAsset(workspaceId, src);
          } else {
            await fileService.restoreNewAsset(workspaceSlug, src);
          }
        },
        upload: uploadFile,
        duplicate: duplicateFile,
        attachFiles,
        // Paradise: failed uploads (paste, drop, picker) end in a toast instead of only console.error
        onUploadFailure: (error, file) => reportUploadError(error, { name: file.name }),
        validation: {
          maxFileSize,
        },
        resolveAttachmentLink: resolveAttachmentLinkHere,
        fileCardLabels,
        ...getExtendedEditorFileHandlers({ projectId, workspaceSlug }),
      };
    },
    [assetsUploadPercentage, fileCardLabels, getExtendedEditorFileHandlers, maxFileSize, reportUploadError]
  );

  return {
    getEditorFileHandlers,
  };
};
