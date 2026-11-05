/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { EditorState } from "@tiptap/pm/state";
import { ReactNodeViewRenderer } from "@tiptap/react";
// types
import type { TMentionHandler } from "@/types";
// extension config
import { CustomMentionExtensionConfig } from "./extension-config";
// node view
import type { MentionNodeViewProps } from "./mention-node-view";
import { MentionNodeView } from "./mention-node-view";
// utils
import { renderMentionsDropdown } from "./utils";

export function CustomMentionExtension(props: TMentionHandler) {
  const {
    searchCallback,
    searchHashCallback,
    tip,
    renderComponent,
    getMentionedEntityDetails,
    getMentionedEntityLabel,
  } = props;
  return CustomMentionExtensionConfig.extend({
    addOptions(this) {
      return {
        ...this.parent?.(),
        renderComponent,
        getMentionedEntityDetails,
        getMentionedEntityLabel,
      };
    },

    addNodeView() {
      return ReactNodeViewRenderer((nodeViewProps) => (
        <MentionNodeView {...nodeViewProps} node={nodeViewProps.node as MentionNodeViewProps["node"]} />
      ));
    },
  }).configure({
    // Paradise (KEP-91): Tiptap menerima banyak pemicu lewat `suggestions`; `#` dipasang hanya bila ada callback-nya.
    suggestions: [
      {
        char: "@",
        render: renderMentionsDropdown({ searchCallback, tip }),
        allowSpaces: true,
      },
      ...(searchHashCallback
        ? [
            {
              char: "#",
              render: renderMentionsDropdown({ searchCallback: searchHashCallback, tip }),
              allowSpaces: false,
              // Di awal baris "# " adalah aturan heading markdown: "#" saja tidak boleh membuka dropdown,
              // baru boleh bila sudah ada karakter sesudahnya (mis. "#12" atau "#umum").
              allow: ({ state, range }: { state: EditorState; range: { from: number; to: number } }) => {
                const $from = state.doc.resolve(range.from);
                // sama dengan aturan bawaan (node mention harus boleh di sini), plus tidak di blok kode
                const mentionType = state.schema.nodes[CustomMentionExtensionConfig.name];
                if ($from.parent.type.spec.code || !mentionType) return false;
                if (!$from.parent.type.contentMatch.matchType(mentionType)) return false;
                const isLineStart = range.from === $from.start();
                return !isLineStart || range.to - range.from > 1;
              },
            },
          ]
        : []),
    ],
  });
}
