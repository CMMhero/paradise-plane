/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: alamat God Mode lama
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Activity, Trash, AI, dan Image pindah ke bawah Logs dan API keys. Bookmark
 * ke alamat lama diteruskan ke tab yang sama, bukan jatuh ke 404.
 */

import { Navigate, useLocation } from "react-router";

const ALAMAT_BARU: Record<string, string> = {
  "/activity": "/logs/",
  "/activity/audit-log": "/logs/audit/",
  "/trash": "/logs/trash/",
  "/ai": "/api-keys/",
  "/image": "/api-keys/image/",
};

export default function AlamatLama() {
  const { pathname } = useLocation();
  return <Navigate to={ALAMAT_BARU[pathname.replace(/\/+$/, "")] ?? "/general/"} replace />;
}
