/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Handle } from "hast-util-to-mdast";
// local imports
import { createTextNode } from "./common";
import type { TCustomComponentsMetaData } from "./types";

type TArgs = {
  metaData: TCustomComponentsMetaData;
};

export const parseCustomComponents = (args: TArgs): Record<string, Handle> => {
  const { metaData } = args;

  const getFileAssetDetails = (id: string) => metaData.file_assets.find((asset) => asset.id === id);

  // Paradise (KEP-91): @all, #kanal, dan #work item. Dulu ketiganya keluar sebagai `[@]()`.
  const rujukanMarkdown = (jenis: string, id: string): string | undefined => {
    if (jenis === "everyone_mention") return "@all";
    if (jenis !== "channel_mention" && jenis !== "issue_mention") return undefined;
    const rujukan = metaData.reference_mentions?.find((r) => r.id === id);
    // Tanpa label: id apa adanya, sama dengan yang ditampilkan penyunting.
    return rujukan ? `[#${rujukan.label}](${rujukan.url})` : `#${id}`;
  };

  return {
    "image-component": (_state, node) => {
      const properties = node.properties || {};
      const src = String(properties.src);
      const fileAssetDetails = getFileAssetDetails(src);
      if (!src || !fileAssetDetails) return createTextNode("");
      return createTextNode(`![${fileAssetDetails.name}](${fileAssetDetails.url})`);
    },
    img: (_state, node) => {
      const properties = node.properties || {};
      const src = String(properties.src);
      const alt = String(properties.alt);
      if (!src || !alt) return createTextNode("");
      return createTextNode(`![${alt || "Image"}](${src})`);
    },
    "mention-component": (_state, node) => {
      const properties = node.properties || {};
      const mentionType = String(properties.entity_name);
      const rujukan = rujukanMarkdown(mentionType, String(properties.entity_identifier));
      if (rujukan) return createTextNode(`${rujukan} `);

      let url: string = "";
      let tag: string = "@";
      if (mentionType === "user_mention") {
        const userId = String(properties.entity_identifier);
        const userDetails = metaData.user_mentions.find((user) => user.id === userId);
        if (!userDetails) return createTextNode("");
        url = userDetails.url || "";
        tag = `@${userDetails.display_name || "Unknown user"}`;
      }

      return createTextNode(`[${tag}](${url}) `);
    },
  };
};
