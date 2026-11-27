/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: node berkas non-gambar
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { ReactNodeViewRenderer } from "@tiptap/react";
import { v4 as uuidv4 } from "uuid";
// constants
import { ACCEPTED_ATTACHMENT_MIME_TYPES } from "@/constants/config";
// helpers
import { isFileValid } from "@/helpers/file";
import { insertEmptyParagraphAtNodeBoundaries } from "@/helpers/insert-empty-paragraph-at-node-boundary";
// types
import type { TFileHandler } from "@/types";
// local imports
import type { CustomFileNodeViewProps } from "./components/node-view";
import { CustomFileNodeView } from "./components/node-view";
import { CustomFileExtensionConfig } from "./extension-config";
import type { CustomFileExtensionOptions, CustomFileExtensionStorage } from "./types";
import { ECustomFileAttributeNames } from "./types";
import { DEFAULT_FILE_CARD_LABELS, getFileComponentFileMap, getLoneAttachmentLinkAttrs } from "./utils";

type Props = {
  fileHandler: TFileHandler;
  isEditable: boolean;
};

export function CustomFileExtension(props: Props) {
  const { fileHandler, isEditable } = props;
  // derived values
  const { getAssetDownloadSrc, getAssetSrc, resolveAttachmentLink, fileCardLabels } = fileHandler;

  return CustomFileExtensionConfig.extend<CustomFileExtensionOptions, CustomFileExtensionStorage>({
    selectable: isEditable,
    draggable: isEditable,

    addOptions() {
      const upload = "upload" in fileHandler ? fileHandler.upload : undefined;
      return {
        ...this.parent?.(),
        getFileDownloadSource: getAssetDownloadSrc,
        getFileSource: getAssetSrc,
        uploadFile: upload,
        labels: fileCardLabels ?? DEFAULT_FILE_CARD_LABELS,
      };
    },

    parseHTML() {
      const rules = this.parent?.() ?? [];
      if (!resolveAttachmentLink) return rules;
      // Read-time only: the stored HTML keeps its link until the user edits and saves.
      return [
        ...rules,
        {
          tag: "p",
          // above the paragraph rule (50), which takes over whenever this one declines
          priority: 60,
          getAttrs: (element) => getLoneAttachmentLinkAttrs(element, resolveAttachmentLink) ?? false,
        },
      ];
    },

    addStorage() {
      const maxFileSize = "validation" in fileHandler ? fileHandler.validation?.maxFileSize : 0;

      return {
        fileMap: new Map(),
        maxFileSize,
        // node berkas tidak punya padanan markdown; jangan serialisasi apa pun
        markdown: {
          serialize() {},
        },
      };
    },

    addCommands() {
      return {
        insertFileComponent:
          (commandProps) =>
          ({ commands }) => {
            // berkas yang di-drop divalidasi sebelum node dibuat, supaya tidak
            // meninggalkan kartu kosong yang tak bisa dihapus user
            if (
              commandProps?.file &&
              !isFileValid({
                acceptedMimeTypes: ACCEPTED_ATTACHMENT_MIME_TYPES,
                file: commandProps.file,
                maxFileSize: this.storage.maxFileSize,
                onError: (_error, message) => alert(message),
              })
            ) {
              return false;
            }

            const fileId = uuidv4();
            const fileComponentFileMap = getFileComponentFileMap(this.editor);

            if (fileComponentFileMap) {
              if (commandProps?.event === "drop" && commandProps.file) {
                fileComponentFileMap.set(fileId, {
                  file: commandProps.file,
                  event: commandProps.event,
                });
              } else if (commandProps.event === "insert") {
                fileComponentFileMap.set(fileId, {
                  event: commandProps.event,
                  hasOpenedFileInputOnce: false,
                });
              }
            }

            const attributes = {
              [ECustomFileAttributeNames.ID]: fileId,
            };

            if (commandProps.pos) {
              return commands.insertContentAt(commandProps.pos, {
                type: this.name,
                attrs: attributes,
              });
            }
            return commands.insertContent({
              type: this.name,
              attrs: attributes,
            });
          },
      };
    },

    addKeyboardShortcuts() {
      return {
        ArrowDown: insertEmptyParagraphAtNodeBoundaries("down", this.name),
        ArrowUp: insertEmptyParagraphAtNodeBoundaries("up", this.name),
      };
    },

    addNodeView() {
      return ReactNodeViewRenderer((nodeViewProps) => (
        <CustomFileNodeView {...nodeViewProps} node={nodeViewProps.node as CustomFileNodeViewProps["node"]} />
      ));
    },
  });
}
