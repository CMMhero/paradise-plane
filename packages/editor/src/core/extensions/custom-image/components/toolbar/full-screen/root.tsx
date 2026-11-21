/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Maximize } from "lucide-react";
// plane imports
import { useImageGallery } from "@plane/propel/image-gallery";
import { Tooltip } from "@plane/propel/tooltip";

type Props = {
  image: {
    src: string;
  };
  isTouchDevice: boolean;
};

/**
 * Opens the image in the gallery of its scope: every image of the editor, or
 * of the whole work item / page the editor is part of (Paradise).
 */
export function ImageFullScreenActionRoot(props: Props) {
  const { image, isTouchDevice } = props;
  const gallery = useImageGallery();

  return (
    <Tooltip tooltipContent="View in full screen" disabled={isTouchDevice}>
      <button
        type="button"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          const button = e.currentTarget;
          const item = button.closest("[data-image-gallery-src]");
          const opened = !!gallery && gallery.open(item ?? image.src, button);
          if (!opened) window.open(image.src, "_blank", "noopener,noreferrer");
        }}
        className="grid h-full flex-shrink-0 place-items-center text-on-color/60 transition-colors hover:text-on-color"
        aria-label="View image in full screen"
      >
        <Maximize className="size-3" />
      </button>
    </Tooltip>
  );
}
