/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Activity, Building2, Image, BrainCog, Cog, Mail, Network, ScrollText, Trash2, Users } from "lucide-react";
// plane imports
import { LockIcon, WorkspaceIcon } from "@plane/propel/icons";
// types
import type { TSidebarMenuItem } from "./types";

export type TCoreSidebarMenuKey =
  | "general"
  | "email"
  | "workspace"
  | "authentication"
  | "ai"
  | "image"
  | "logs"
  | "trash"
  | "members"
  | "organisasi"
  | "activity"
  | "companies";

export const coreSidebarMenuLinks: Record<TCoreSidebarMenuKey, TSidebarMenuItem> = {
  general: {
    Icon: Cog,
    name: "General",
    description: "Identify your instances and get key details.",
    href: `/general/`,
  },
  email: {
    Icon: Mail,
    name: "Email",
    description: "Configure your SMTP controls.",
    href: `/email/`,
  },
  workspace: {
    Icon: WorkspaceIcon,
    name: "Workspaces",
    description: "Manage all workspaces on this instance.",
    href: `/workspace/`,
  },
  authentication: {
    Icon: LockIcon,
    name: "Authentication",
    description: "Configure authentication modes.",
    href: `/authentication/`,
  },
  ai: {
    Icon: BrainCog,
    name: "Artificial intelligence",
    description: "Configure your OpenAI creds.",
    href: `/ai/`,
  },
  image: {
    Icon: Image,
    // Sisa merek upstream di God Mode, apps/web & apps/space sudah dibersihkan
    // di `a407ce0`/`07a6fe2`, apps/admin belum ikut disapu.
    name: "Pustaka gambar",
    description: "Izinkan pustaka gambar pihak ketiga.",
    href: `/image/`,
  },
  // Kustomisasi Paradise, jejak audit sengaja HANYA di God Mode.
  companies: {
    Icon: Building2,
    name: "Pelanggan",
    description: "Perusahaan berlangganan, pemakaian, dan tagihannya.",
    href: `/companies/`,
  },
  logs: {
    Icon: ScrollText,
    name: "Jejak audit",
    description: "Siapa mengubah apa di seluruh instance.",
    href: `/logs/`,
  },
  trash: {
    Icon: Trash2,
    name: "TPA",
    description: "Barang terhapus dari seluruh project.",
    href: `/trash/`,
  },
  members: {
    Icon: Users,
    name: "Member",
    description: "Buat akun, atur hak akses, pantau aktivitas.",
    href: `/members/`,
  },
  organisasi: {
    Icon: Network,
    name: "Struktur organisasi",
    description: "Divisi, departemen, dan project di dalamnya.",
    href: `/organisasi/`,
  },
  activity: {
    Icon: Activity,
    name: "Aktivitas",
    description: "Siapa sedang memakai, dan riwayat keluar-masuk.",
    href: `/activity/`,
  },
};
