/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: galeri gambar (teks)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/** Every text the viewer shows or announces. The app passes translated ones through `ImageGallery.Provider`. */
export type TImageGalleryLabels = {
  dialog: string;
  close: string;
  previous: string;
  next: string;
  zoomIn: string;
  zoomOut: string;
  resetZoom: string;
  download: string;
  openInNewTab: string;
  loadError: string;
  /** read by screen readers when the image changes, e.g. "Image 3 of 12" */
  counter: (current: number, total: number) => string;
};

export const DEFAULT_IMAGE_GALLERY_LABELS: TImageGalleryLabels = {
  dialog: "Image viewer",
  close: "Close image viewer",
  previous: "Previous image",
  next: "Next image",
  zoomIn: "Zoom in",
  zoomOut: "Zoom out",
  resetZoom: "Reset zoom",
  download: "Download image",
  openInNewTab: "Open image in new tab",
  loadError: "This image couldn't load. You can still move to the other images.",
  counter: (current, total) => `Image ${current} of ${total}`,
};
