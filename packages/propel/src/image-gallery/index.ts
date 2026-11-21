/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: galeri gambar
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { ImageGalleryProvider, ImageGalleryScope } from "./scope";
import { ImageGalleryViewer } from "./viewer";

export * from "./gallery";
export * from "./labels";
export * from "./scope";
export * from "./viewer";

/** Compound access: `ImageGallery.Provider` (texts), `ImageGallery.Scope` (one gallery), `ImageGallery.Viewer`. */
export const ImageGallery = {
  Provider: ImageGalleryProvider,
  Scope: ImageGalleryScope,
  Viewer: ImageGalleryViewer,
};
