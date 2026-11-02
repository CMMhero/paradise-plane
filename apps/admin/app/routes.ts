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
    // Paradise: bawaan project baru, tab kedua menu Workspaces.
    route("workspace/project-defaults", "./(all)/(dashboard)/bawaan-project/page.tsx"),
    route("email", "./(all)/(dashboard)/email/page.tsx"),
    route("authentication", "./(all)/(dashboard)/authentication/page.tsx"),
    route("authentication/github", "./(all)/(dashboard)/authentication/github/page.tsx"),
    route("authentication/gitlab", "./(all)/(dashboard)/authentication/gitlab/page.tsx"),
    route("authentication/google", "./(all)/(dashboard)/authentication/google/page.tsx"),
    route("authentication/gitea", "./(all)/(dashboard)/authentication/gitea/page.tsx"),
    // Paradise: API keys = AI, Image library, Google. Satu menu dengan tab.
    route("api-keys", "./(all)/(dashboard)/ai/page.tsx"),
    route("api-keys/image", "./(all)/(dashboard)/image/page.tsx"),
    route("api-keys/google", "./(all)/(dashboard)/kredensial-google/page.tsx"),
    // Paradise: modul, saklar, dan angka operasional (KEP-40). Dulu di .env.
    route("features", "./(all)/(dashboard)/fitur/page.tsx"),
    // Paradise: Members = Accounts + Organization + New member defaults, satu
    // menu dengan tab (lihat components/common/section-tabs.tsx).
    route("members", "./(all)/(dashboard)/members/page.tsx"),
    route("members/organization", "./(all)/(dashboard)/organisasi/page.tsx"),
    route("members/defaults", "./(all)/(dashboard)/bawaan-member/page.tsx"),
    // Paradise: Logs = Activity (sesi & riwayat masuk) + Audit log + Trash,
    // satu menu dengan tab. Jejak audit sengaja HANYA di God Mode.
    route("logs", "./(all)/(dashboard)/activity/page.tsx"),
    route("logs/audit", "./(all)/(dashboard)/logs/page.tsx"),
    route("logs/trash", "./(all)/(dashboard)/trash/page.tsx"),
    // Alamat lama tetap hidup supaya bookmark tidak jatuh ke 404.
    route("activity", "./(all)/(dashboard)/alamat-lama.tsx", { id: "lama-activity" }),
    route("activity/audit-log", "./(all)/(dashboard)/alamat-lama.tsx", { id: "lama-audit" }),
    route("trash", "./(all)/(dashboard)/alamat-lama.tsx", { id: "lama-trash" }),
    route("ai", "./(all)/(dashboard)/alamat-lama.tsx", { id: "lama-ai" }),
    route("image", "./(all)/(dashboard)/alamat-lama.tsx", { id: "lama-image" }),
  ]),
  // Catch-all route for 404 handling - must be last
  route("*", "./components/404.tsx"),
] satisfies RouteConfig;
