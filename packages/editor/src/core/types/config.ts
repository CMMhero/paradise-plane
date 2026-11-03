/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import type { TExtendedFileHandler } from "@/plane-editor/types/config";

export type TFileHandler = {
  assetsUploadStatus: Record<string, number>; // blockId => progress percentage
  cancel: () => void;
  checkIfAssetExists: (assetId: string) => Promise<boolean>;
  delete: (assetSrc: string) => Promise<void>;
  getAssetDownloadSrc: (path: string) => Promise<string>;
  getAssetSrc: (path: string) => Promise<string>;
  restore: (assetSrc: string) => Promise<void>;
  upload: (blockId: string, file: File) => Promise<string>;
  duplicate: (assetId: string) => Promise<string>;
  validation: {
    /**
     * @description max file size in bytes
     * @example enter 5242880(5 * 1024 * 1024) for 5MB
     */
    maxFileSize: number;
  };
  /**
   * Paradise: when set, pasted or dropped files that are NOT inline images are
   * handed to the host app (for example to become work item attachments)
   * instead of becoming an in-editor file block. The editor inserts a link for
   * every file the host reports as attached. Upload progress and errors are the
   * host's job, it owns the attachment store.
   */
  attachFiles?: (files: File[]) => Promise<TAttachedFile[]>;
} & TExtendedFileHandler;

export type TAttachedFile = {
  name: string;
  url: string;
};

export type TEditorFontStyle = "sans-serif" | "serif" | "monospace";

export type TEditorFontSize = "small-font" | "large-font" | "mobile-font";

export type TEditorLineSpacing = "regular" | "small" | "mobile-regular";

export type TDisplayConfig = {
  fontStyle?: TEditorFontStyle;
  fontSize?: TEditorFontSize;
  lineSpacing?: TEditorLineSpacing;
  wideLayout?: boolean;
};

export type TUserDetails = {
  color: string;
  id: string;
  name: string;
  cookie?: string;
};

export type TRealtimeConfig = {
  url: string;
};

export type IMarking = {
  type: "heading";
  level: number;
  text: string;
  sequence: number;
};
