/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: alamat God Mode lama
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Bookmarks to any earlier God Mode address are forwarded to the same page in
 * the KEP-83 menu tree (see alamat-lama-map.ts), not dropped into the 404.
 */

import { Navigate, useLocation } from "react-router";
import { ALAMAT_BARU } from "@/app/alamat-lama-map";

export default function AlamatLama() {
  const { pathname, search } = useLocation();
  const target = ALAMAT_BARU[pathname.replace(/\/+$/, "")] ?? "/general/";
  return <Navigate to={`${target}${search}`} replace />;
}
