/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: teks galeri gambar
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo } from "react";
import type { ReactNode } from "react";
import { useTranslation } from "@plane/i18n";
import { ImageGallery } from "@plane/propel/image-gallery";
import type { TImageGalleryLabels } from "@plane/propel/image-gallery";

/** Gives every image gallery in the app (editors, attachments, chat) translated texts. */
export function ImageGalleryI18nProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const labels = useMemo<TImageGalleryLabels>(
    () => ({
      dialog: t("image_gallery.dialog"),
      close: t("image_gallery.close"),
      previous: t("image_gallery.previous"),
      next: t("image_gallery.next"),
      zoomIn: t("image_gallery.zoom_in"),
      zoomOut: t("image_gallery.zoom_out"),
      resetZoom: t("image_gallery.reset_zoom"),
      download: t("image_gallery.download"),
      openInNewTab: t("image_gallery.open_in_new_tab"),
      loadError: t("image_gallery.load_error"),
      counter: (current, total) => t("image_gallery.counter", { current, total }),
    }),
    [t]
  );
  return <ImageGallery.Provider labels={labels}>{children}</ImageGallery.Provider>;
}
