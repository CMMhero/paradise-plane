/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { index, layout, route } from "@react-router/dev/routes";
import type { RouteConfig } from "@react-router/dev/routes";

export default [
  layout("./(all)/(home)/layout.tsx", [index("./(all)/(home)/page.tsx")]),
  layout("./(all)/(dashboard)/layout.tsx", [
    route("general", "./(all)/(dashboard)/general/page.tsx"),
    route("workspace", "./(all)/(dashboard)/workspace/page.tsx"),
    route("workspace/create", "./(all)/(dashboard)/workspace/create/page.tsx"),
    route("email", "./(all)/(dashboard)/email/page.tsx"),
    route("authentication", "./(all)/(dashboard)/authentication/page.tsx"),
    route("authentication/github", "./(all)/(dashboard)/authentication/github/page.tsx"),
    route("authentication/gitlab", "./(all)/(dashboard)/authentication/gitlab/page.tsx"),
    route("authentication/google", "./(all)/(dashboard)/authentication/google/page.tsx"),
    route("authentication/gitea", "./(all)/(dashboard)/authentication/gitea/page.tsx"),
    route("ai", "./(all)/(dashboard)/ai/page.tsx"),
    route("image", "./(all)/(dashboard)/image/page.tsx"),
    // Kustomisasi Paradise, jejak audit sengaja HANYA di sini, tidak
    // ada padanannya di aplikasi utama.
    route("logs", "./(all)/(dashboard)/logs/page.tsx"),
    // TPA, tong sampah lintas project, hanya Super Admin.
    route("trash", "./(all)/(dashboard)/trash/page.tsx"),
    // Kelola member, satu-satunya pintu masuk akun selama signup mati.
    route("members", "./(all)/(dashboard)/members/page.tsx"),
    // Struktur divisi -> departemen -> project (KEP-29).
    route("organisasi", "./(all)/(dashboard)/organisasi/page.tsx"),
    // Pemantauan sesi & keaktifan, siapa sedang memakai, kick, riwayat 3 bulan.
    route("activity", "./(all)/(dashboard)/activity/page.tsx"),
    // Owner Panel bidang kendali SaaS. Rutenya SELALU terdaftar; yang
    // bersyarat adalah menunya di sidebar, dan halamannya sendiri sudah
    // menangani keadaan "bidang kendali tidak aktif di deployment ini".
    // Rute yang ikut bersyarat berarti tautan langsung mendarat di 404
    // yang tidak menjelaskan apa-apa.
    route("companies", "./(all)/(dashboard)/companies/page.tsx"),
  ]),
  // Catch-all route for 404 handling - must be last
  route("*", "./components/404.tsx"),
] satisfies RouteConfig;
