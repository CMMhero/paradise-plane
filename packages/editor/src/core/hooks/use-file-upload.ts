/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Editor, NodeViewProps } from "@tiptap/core";
import type { DragEvent } from "react";
import { useCallback, useEffect, useState } from "react";
// helpers
import type { EFileError } from "@/helpers/file";
import { isFileValid } from "@/helpers/file";
// plugins
import { insertFilesSafely } from "@/plugins/drop";
// types
import type { TEditorCommands } from "@/types";

type TUploaderArgs = {
  acceptedMimeTypes: string[];
  editorCommand: (file: File) => Promise<string | undefined>;
  handleProgressStatus?: (isUploading: boolean) => void;
  loadFileFromFileSystem?: (file: string) => void;
  maxFileSize: number;
  onInvalidFile: (error: EFileError, file: File, message: string) => void;
  /** Paradise: called when the upload itself fails, so the user is told instead of nothing happening */
  onUploadError?: (error: unknown, file: File) => void;
  onUpload: (url: string, file: File) => void;
};

export const useUploader = (args: TUploaderArgs) => {
  const {
    acceptedMimeTypes,
    editorCommand,
    handleProgressStatus,
    loadFileFromFileSystem,
    maxFileSize,
    onInvalidFile,
    onUploadError,
    onUpload,
  } = args;
  // states
  const [isUploading, setIsUploading] = useState(false);

  const uploadFile = useCallback(
    async (file: File) => {
      handleProgressStatus?.(true);
      setIsUploading(true);
      const isValid = isFileValid({
        acceptedMimeTypes,
        file,
        maxFileSize,
        onError: (error, message) => onInvalidFile(error, file, message),
      });
      if (!isValid) {
        handleProgressStatus?.(false);
        setIsUploading(false);
        return;
      }
      try {
        if (loadFileFromFileSystem) {
          const reader = new FileReader();
          // oxlint-disable-next-line unicorn/prefer-add-event-listener -- kept as is: restructuring it is out of scope for this release
          reader.onload = () => {
            if (reader.result) {
              loadFileFromFileSystem(reader.result as string);
            } else {
              console.error("Failed to read the file: reader.result is null");
            }
          };
          // oxlint-disable-next-line unicorn/prefer-add-event-listener -- kept as is: restructuring it is out of scope for this release
          reader.onerror = () => {
            console.error("Error reading file");
          };
          reader.readAsDataURL(file);
        }
        const url = await editorCommand(file);

        if (!url) {
          throw new Error("Something went wrong while uploading the file.");
        }
        onUpload(url, file);
      } catch (error) {
        // the host's upload function throws the real cause (network, size, type...); surface it
        // instead of only logging, which left the block stuck on "Add a file" with no explanation
        console.error("useFileUpload: Error in uploading file", error);
        onUploadError?.(error, file);
      } finally {
        handleProgressStatus?.(false);
        setIsUploading(false);
      }
    },
    [
      acceptedMimeTypes,
      editorCommand,
      handleProgressStatus,
      loadFileFromFileSystem,
      maxFileSize,
      onInvalidFile,
      onUploadError,
      onUpload,
    ]
  );

  return { isUploading, uploadFile };
};

type TDropzoneArgs = {
  editor: Editor;
  getPos: NodeViewProps["getPos"];
  type: Extract<TEditorCommands, "attachment" | "image">;
  uploader: (file: File) => Promise<void>;
};

export const useDropZone = (args: TDropzoneArgs) => {
  const { editor, getPos, type, uploader } = args;
  // states
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [draggedInside, setDraggedInside] = useState<boolean>(false);

  useEffect(() => {
    const dragStartHandler = () => {
      setIsDragging(true);
    };

    const dragEndHandler = () => {
      setIsDragging(false);
    };

    document.body.addEventListener("dragstart", dragStartHandler);
    document.body.addEventListener("dragend", dragEndHandler);

    return () => {
      document.body.removeEventListener("dragstart", dragStartHandler);
      document.body.removeEventListener("dragend", dragEndHandler);
    };
  }, []);

  const onDrop = useCallback(
    async (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDraggedInside(false);
      const filesList = e.dataTransfer.files;
      const pos = getPos();

      if (filesList.length === 0 || !editor.isEditable || pos === undefined) {
        return;
      }

      await uploadFirstFileAndInsertRemaining({
        editor,
        filesList,
        pos,
        type,
        uploader,
      });
    },
    [editor, type, uploader, getPos]
  );
  const onDragEnter = useCallback(() => setDraggedInside(true), []);
  const onDragLeave = useCallback(() => setDraggedInside(false), []);

  return {
    isDragging,
    draggedInside,
    onDragEnter,
    onDragLeave,
    onDrop,
  };
};

type TMultipleFileArgs = {
  editor: Editor;
  filesList: FileList | File[];
  pos: number;
  type: Extract<TEditorCommands, "attachment" | "image">;
  uploader: (file: File) => Promise<void>;
};

// Upload the first file and insert the remaining ones for uploading multiple files
export const uploadFirstFileAndInsertRemaining = async (args: TMultipleFileArgs) => {
  const { editor, filesList, pos, type, uploader } = args;
  const filesArray = Array.from(filesList);
  if (filesArray.length === 0) {
    console.error("No files found to upload.");
    return;
  }

  // Upload the first file
  const firstFile = filesArray[0];
  uploader(firstFile);
  // Insert the remaining files
  const remainingFiles = filesArray.slice(1);
  if (remainingFiles.length > 0) {
    const docSize = editor.state.doc.content.size;
    const posOfNextFileToBeInserted = Math.min(pos + 1, docSize);
    insertFilesSafely({
      editor,
      files: remainingFiles,
      initialPos: posOfNextFileToBeInserted,
      event: "drop",
      type,
    });
  }
};
