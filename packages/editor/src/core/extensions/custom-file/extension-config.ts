/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: node berkas non-gambar
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Node, mergeAttributes } from "@tiptap/core";
// constants
import { CORE_EXTENSIONS } from "@/constants/extension";
// local imports
import type {
  CustomFileExtensionOptions,
  CustomFileExtensionStorage,
  CustomFileExtensionType,
  InsertFileComponentProps,
  TCustomFileAttributes,
} from "./types";
import { ECustomFileAttributeNames } from "./types";

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    [CORE_EXTENSIONS.CUSTOM_FILE]: {
      insertFileComponent: ({ file, pos, event }: InsertFileComponentProps) => ReturnType;
    };
  }
  interface Storage {
    [CORE_EXTENSIONS.CUSTOM_FILE]: CustomFileExtensionStorage;
  }
}

const DEFAULT_CUSTOM_FILE_ATTRIBUTES: TCustomFileAttributes = {
  [ECustomFileAttributeNames.ID]: null,
  [ECustomFileAttributeNames.SOURCE]: null,
  [ECustomFileAttributeNames.NAME]: null,
  [ECustomFileAttributeNames.SIZE]: null,
  [ECustomFileAttributeNames.TYPE]: null,
};

/**
 * Skema saja, tanpa props React. Dipakai bersama oleh editor di browser DAN oleh
 * server Live lewat CoreEditorExtensionsWithoutProps -> yjs-utils. Node yang tidak
 * terdaftar di skema server akan HILANG diam-diam saat Y.Doc dikonversi ke
 * JSON/HTML, jadi konfigurasi ini wajib dipisah dari node view-nya.
 */
export const CustomFileExtensionConfig: CustomFileExtensionType = Node.create<
  CustomFileExtensionOptions,
  CustomFileExtensionStorage
>({
  name: CORE_EXTENSIONS.CUSTOM_FILE,
  group: "block",
  atom: true,

  addAttributes() {
    return Object.values(ECustomFileAttributeNames).reduce(
      (acc, value) => {
        acc[value] = { default: DEFAULT_CUSTOM_FILE_ATTRIBUTES[value] };
        return acc;
      },
      {} as Record<ECustomFileAttributeNames, { default: TCustomFileAttributes[ECustomFileAttributeNames] }>
    );
  },

  parseHTML() {
    return [
      {
        tag: "file-component",
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return ["file-component", mergeAttributes(HTMLAttributes)];
  },
});
