/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback } from "react";
// plane imports
import type { TFileHandler } from "@plane/editor";
import { getEditorAssetDownloadSrc, getEditorAssetSrc } from "@plane/utils";
// hooks
import { useEditorAsset } from "@/hooks/store/use-editor-asset";
// plane web hooks
import { useExtendedEditorConfig } from "@/hooks/editor/use-extended-editor-config";
import { useFileSize } from "@/hooks/use-file-size";
import { useUploadErrorReporter } from "@/hooks/use-upload-error-reporter";
// services
import { FileService } from "@/services/file.service";
const fileService = new FileService();

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
          if (path?.startsWith("http")) {
            return path;
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
          if (path?.startsWith("http")) {
            return path;
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
        ...getExtendedEditorFileHandlers({ projectId, workspaceSlug }),
      };
    },
    [assetsUploadPercentage, getExtendedEditorFileHandlers, maxFileSize, reportUploadError]
  );

  return {
    getEditorFileHandlers,
  };
};
