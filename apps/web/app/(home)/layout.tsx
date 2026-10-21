/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Outlet } from "react-router";
// types
import type { Route } from "./+types/layout";

// Judul WAJIB disebut di sini. Meta anak MENGGANTIKAN meta induk di React
// Router, bukan menambah, jadi mengekspor meta tanpa title membuang judul dari
// root dan menyisakan judul entah dari mana di layar pertama yang dilihat semua
// karyawan. Bunyinya disamakan dengan sign-up/layout.tsx: ini memang layar
// masuk, `AuthBase` di halaman ini dipanggil dengan EAuthModes.SIGN_IN.
export const meta: Route.MetaFunction = () => [
  { title: "Masuk - Paradise Task Tracker" },
  { name: "robots", content: "index, nofollow" },
  { name: "viewport", content: "width=device-width, initial-scale=1, minimum-scale=1, viewport-fit=cover" },
];

export default function HomeLayout() {
  return <Outlet />;
}
