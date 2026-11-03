/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Editor, JSONContent } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
// constants
import { CORE_EXTENSIONS } from "@/constants/extension";
import { ACCEPTED_ATTACHMENT_MIME_TYPES, ACCEPTED_IMAGE_MIME_TYPES } from "@/constants/config";
// types
import type { TAttachedFile, TEditorCommands, TExtensions, TFileHandler } from "@/types";

type Props = {
  disabledExtensions?: TExtensions[];
  flaggedExtensions?: TExtensions[];
  editor: Editor;
  fileHandler?: TFileHandler;
};

type TRoutedFiles = {
  /** files the editor renders itself (inline images, file blocks) */
  inline: File[];
  /** files handed to the host app through `fileHandler.attachFiles` */
  attach: File[];
};

const isInlineImage = (file: File, disabledExtensions?: TExtensions[]) =>
  ACCEPTED_IMAGE_MIME_TYPES.includes(file.type) && !disabledExtensions?.includes("image");

/**
 * Splits pasted/dropped files. Without an `attachFiles` host hook nothing
 * changes: images and the accepted attachment types go into the editor, the
 * rest is ignored as before. With the hook, inline images stay inline and
 * every other file (any type, the host validates it) becomes an attachment.
 */
const routeFiles = (files: File[], fileHandler?: TFileHandler, disabledExtensions?: TExtensions[]): TRoutedFiles => {
  if (fileHandler?.attachFiles) {
    return {
      inline: files.filter((f) => isInlineImage(f, disabledExtensions)),
      attach: files.filter((f) => !isInlineImage(f, disabledExtensions)),
    };
  }
  return {
    inline: files.filter(
      (f) => ACCEPTED_IMAGE_MIME_TYPES.includes(f.type) || ACCEPTED_ATTACHMENT_MIME_TYPES.includes(f.type)
    ),
    attach: [],
  };
};

const buildAttachmentLinks = (editor: Editor, attached: TAttachedFile[]): JSONContent[] => {
  const hasLinkMark = !!editor.schema.marks[CORE_EXTENSIONS.CUSTOM_LINK];
  return attached.flatMap((file, index) => [
    ...(index > 0 ? [{ type: "text", text: " " }] : []),
    {
      type: "text",
      text: file.name,
      ...(hasLinkMark
        ? { marks: [{ type: CORE_EXTENSIONS.CUSTOM_LINK, attrs: { href: file.url, target: "_blank" } }] }
        : {}),
    },
  ]);
};

/**
 * Hands files to the host and, once they are attached, drops a link to each
 * one into the text. The position is clamped because the user keeps typing
 * while the upload runs. If the editor is gone (comment already sent) the
 * attachments still exist on the work item, only the links are skipped.
 */
const attachFilesThroughHost = async (editor: Editor, fileHandler: TFileHandler, files: File[], pos: number) => {
  if (!fileHandler.attachFiles || files.length === 0) return;
  let attached: TAttachedFile[] = [];
  try {
    attached = await fileHandler.attachFiles(files);
  } catch (error) {
    // the host already reported the failure to the user
    console.error("Error while attaching files:", error);
    return;
  }
  if (attached.length === 0 || editor.isDestroyed || !editor.isEditable) return;
  const safePos = Math.min(pos, editor.state.doc.content.size);
  editor
    .chain()
    .insertContentAt(safePos, [...buildAttachmentLinks(editor, attached), { type: "text", text: " " }])
    .run();
};

const handleFiles = (args: {
  disabledExtensions?: TExtensions[];
  flaggedExtensions?: TExtensions[];
  editor: Editor;
  fileHandler?: TFileHandler;
  files: File[];
  pos: number;
}): boolean => {
  const { disabledExtensions, flaggedExtensions, editor, fileHandler, files, pos } = args;
  const { inline, attach } = routeFiles(files, fileHandler, disabledExtensions);
  if (inline.length === 0 && attach.length === 0) return false;

  if (inline.length > 0) {
    void insertFilesSafely({
      disabledExtensions,
      flaggedExtensions,
      editor,
      files: inline,
      initialPos: pos,
      event: "drop",
    });
  }
  if (attach.length > 0 && fileHandler) {
    void attachFilesThroughHost(editor, fileHandler, attach, pos + inline.length);
  }
  return true;
};

export const DropHandlerPlugin = (props: Props): Plugin => {
  const { disabledExtensions, flaggedExtensions, editor, fileHandler } = props;

  return new Plugin({
    key: new PluginKey("drop-handler-plugin"),
    props: {
      handlePaste: (view, event) => {
        const files = Array.from(event.clipboardData?.files ?? []);
        if (!editor.isEditable || files.length === 0) return false;
        event.preventDefault();
        handleFiles({
          disabledExtensions,
          flaggedExtensions,
          editor,
          fileHandler,
          files,
          pos: view.state.selection.from,
        });
        // the files were ours to handle even if none were accepted: never let
        // the browser paste a file path or a broken blob into the text
        return true;
      },
      handleDrop: (view, event, _slice, moved) => {
        const files = Array.from(event.dataTransfer?.files ?? []);
        if (!editor.isEditable || moved || files.length === 0) return false;
        event.preventDefault();
        const coordinates = view.posAtCoords({ left: event.clientX, top: event.clientY });
        return handleFiles({
          disabledExtensions,
          flaggedExtensions,
          editor,
          fileHandler,
          files,
          pos: coordinates?.pos ?? view.state.selection.from,
        });
      },
    },
  });
};

type InsertFilesSafelyArgs = {
  disabledExtensions?: TExtensions[];
  flaggedExtensions?: TExtensions[];
  editor: Editor;
  event: "insert" | "drop";
  files: File[];
  initialPos: number;
  type?: Extract<TEditorCommands, "attachment" | "image">;
};

export const insertFilesSafely = async (args: InsertFilesSafelyArgs) => {
  const { disabledExtensions, editor, event, files, initialPos, type } = args;
  let pos = initialPos;

  for (const file of files) {
    // safe insertion
    const docSize = editor.state.doc.content.size;
    pos = Math.min(pos, docSize);

    let fileType: "image" | "attachment" | null = null;

    try {
      if (type) {
        if (["image", "attachment"].includes(type)) fileType = type;
        else throw new Error("Wrong file type passed");
      } else {
        if (ACCEPTED_IMAGE_MIME_TYPES.includes(file.type)) fileType = "image";
        else if (ACCEPTED_ATTACHMENT_MIME_TYPES.includes(file.type)) fileType = "attachment";
      }
      // insert file depending on the type at the current position
      if (fileType === "image" && !disabledExtensions?.includes("image")) {
        editor.commands.insertImageComponent({
          file,
          pos,
          event,
        });
      } else if (fileType === "attachment") {
        editor.commands.insertFileComponent({
          file,
          pos,
          event,
        });
      }
    } catch (error) {
      console.error(`Error while ${event}ing file:`, error);
    }

    // Move to the next position
    pos += 1;
  }
};
