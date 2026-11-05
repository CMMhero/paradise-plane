/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { mergeAttributes } from "@tiptap/core";
import type { MentionOptions } from "@tiptap/extension-mention";
import { Mention } from "@tiptap/extension-mention";
import type { MarkdownSerializerState } from "@tiptap/pm/markdown";
import type { Node as NodeType } from "@tiptap/pm/model";
// types
import type { TMentionHandler } from "@/types";
// local types
import type { TMentionComponentAttributes } from "./types";
import { EMentionComponentAttributeNames } from "./types";

export type TMentionExtensionOptions = MentionOptions & {
  renderComponent: TMentionHandler["renderComponent"];
  getMentionedEntityDetails: TMentionHandler["getMentionedEntityDetails"];
  getMentionedEntityLabel?: TMentionHandler["getMentionedEntityLabel"];
};

export const CustomMentionExtensionConfig = Mention.extend<TMentionExtensionOptions>({
  addAttributes() {
    return {
      [EMentionComponentAttributeNames.ID]: {
        default: null,
      },
      [EMentionComponentAttributeNames.ENTITY_IDENTIFIER]: {
        default: null,
      },
      [EMentionComponentAttributeNames.ENTITY_NAME]: {
        default: null,
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: "mention-component",
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return ["mention-component", mergeAttributes(HTMLAttributes)];
  },

  renderText({ node }) {
    return getMentionDisplayText(this.options, node);
  },

  addStorage() {
    const options = this.options;
    return {
      markdown: {
        serialize(state: MarkdownSerializerState, node: NodeType) {
          state.write(getMentionDisplayText(options, node));
        },
      },
    };
  },
});

function getMentionDisplayText(options: TMentionExtensionOptions, node: NodeType): string {
  const attrs = node.attrs as TMentionComponentAttributes;
  const mentionEntityId = attrs[EMentionComponentAttributeNames.ENTITY_IDENTIFIER];
  const entityName = attrs[EMentionComponentAttributeNames.ENTITY_NAME];
  // Paradise (KEP-91): @all, #kanal, #work item punya awalan dan label sendiri.
  if (entityName === "everyone_mention") return "@all";
  if (entityName === "channel_mention" || entityName === "issue_mention") {
    const label = options.getMentionedEntityLabel?.(entityName, mentionEntityId ?? "");
    return `#${label ?? mentionEntityId}`;
  }
  const mentionEntityDetails = options.getMentionedEntityDetails?.(mentionEntityId ?? "");
  return `@${mentionEntityDetails?.display_name ?? attrs[EMentionComponentAttributeNames.ID] ?? mentionEntityId}`;
}
