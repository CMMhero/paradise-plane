/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Links, Meta, Outlet, Scripts } from "react-router";
// assets
import appleTouchIcon from "@/app/assets/favicon/apple-touch-icon.png?url";
import favicon16 from "@/app/assets/favicon/favicon-16x16.png?url";
import favicon32 from "@/app/assets/favicon/favicon-32x32.png?url";
import faviconIco from "@/app/assets/favicon/favicon.ico?url";
import siteWebmanifest from "@/app/assets/favicon/site.webmanifest?url";
import { LogoSpinner } from "@/components/common/logo-spinner";
import globalStyles from "@/styles/globals.css?url";
// types
import type { Route } from "./+types/root";
// local imports
import ErrorPage from "./error";
import { AppProviders } from "./providers";
// fonts (side-effect imports, memuat font global)
// oxlint-disable no-unassigned-import
import "@fontsource-variable/inter";
import interVariableWoff2 from "@fontsource-variable/inter/files/inter-latin-wght-normal.woff2?url";
// Berat 400 SAJA, bukan seluruh paket.
//
// `@fontsource/material-symbols-rounded` polos menarik EMPAT berat (100, 200,
// 300, 400), masing-masing sekitar 340 sampai 380 KB dalam woff2, plus woff
// cadangannya. Totalnya sekitar 1,45 MB woff2 dan 1,9 MB woff.
//
// Tiga di antaranya TIDAK PERNAH BISA terpakai. Utility `.material-symbols-rounded`
// di `packages/tailwind-config/variables.css` menyetel `font-weight: normal`
// secara eksplisit, dan itu berarti 400. Tidak ada satu pun tempat di aplikasi
// yang merender ikon ini pada berat lain.
//
// Aman kalaupun suatu saat ada yang merendernya di dalam teks tebal: peramban
// memilih @font-face terdekat yang tersedia, jadi ikonnya tetap tampil pada
// ketebalan 400. Untuk huruf IKON itu justru yang diinginkan, karena ketebalan
// goresnya jadi seragam di seluruh aplikasi.
import "@fontsource/material-symbols-rounded/400.css";
import "@fontsource/ibm-plex-mono";
// oxlint-enable no-unassigned-import

const APP_TITLE = "Paradise Publish | Halaman publik PT Paradise Perkasa";
const APP_DESCRIPTION = "Halaman publik Paradise Task Tracker: PT Paradise Perkasa";

export const links: Route.LinksFunction = () => [
  { rel: "apple-touch-icon", sizes: "180x180", href: appleTouchIcon },
  { rel: "icon", type: "image/png", sizes: "32x32", href: favicon32 },
  { rel: "icon", type: "image/png", sizes: "16x16", href: favicon16 },
  { rel: "shortcut icon", href: faviconIco },
  { rel: "manifest", href: siteWebmanifest },
  { rel: "stylesheet", href: globalStyles },
  {
    rel: "preload",
    href: interVariableWoff2,
    as: "font",
    type: "font/woff2",
    crossOrigin: "anonymous",
  },
];

export const headers: Route.HeadersFunction = () => ({
  "Referrer-Policy": "origin-when-cross-origin",
  "X-Content-Type-Options": "nosniff",
  "X-DNS-Prefetch-Control": "on",
  "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
});

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="robots" content="noindex, nofollow" />
        <Meta />
        <Links />
      </head>
      <body>
        <div id="editor-portal" />
        <AppProviders>{children}</AppProviders>
        <Scripts />
      </body>
    </html>
  );
}

export const meta: Route.MetaFunction = () => [
  { title: APP_TITLE },
  { name: "description", content: APP_DESCRIPTION },
  { property: "og:title", content: APP_TITLE },
  { property: "og:description", content: APP_DESCRIPTION },
  {
    name: "keywords",
    content: "manajemen proyek, halaman publik, internal, PT Paradise Perkasa",
  },
  // `twitter:site` DIBUANG, lihat alasan yang sama di apps/web/app/root.tsx.
];

export default function Root() {
  return <Outlet />;
}

export function HydrateFallback() {
  return (
    <div className="relative flex h-screen w-full items-center justify-center bg-surface-1">
      <LogoSpinner />
    </div>
  );
}

export function ErrorBoundary({ error: _error }: Route.ErrorBoundaryProps) {
  return <ErrorPage />;
}
