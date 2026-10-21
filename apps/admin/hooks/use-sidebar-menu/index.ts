/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// hooks
import { useInstance } from "@/hooks/store";
// local imports
import { coreSidebarMenuLinks } from "./core";
import type { TSidebarMenuItem } from "./types";

export function useSidebarMenu(): TSidebarMenuItem[] {
  const { config } = useInstance();

  return [
    coreSidebarMenuLinks.general,
    coreSidebarMenuLinks.email,
    coreSidebarMenuLinks.authentication,
    coreSidebarMenuLinks.members,
    // Penempatan orang di Member membaca pilihan dari sini (KEP-29).
    coreSidebarMenuLinks.organisasi,
    // Tepat di bawah Member: lihat siapa sedang aktif di sini, lalu tindak
    // orangnya di Member.
    coreSidebarMenuLinks.activity,
    coreSidebarMenuLinks.workspace,
    coreSidebarMenuLinks.ai,
    coreSidebarMenuLinks.image,
    coreSidebarMenuLinks.logs,
    coreSidebarMenuLinks.trash,
    // Hanya muncul di deployment pemilik produk. Menu yang menuju halaman mati
    // di tiap instance pasang-sendiri membuat orang mengira produknya rusak,
    // dan yang paling sering dibuka orang yang mengira begitu adalah tiket
    // dukungan.
    ...(config?.is_control_plane_enabled ? [coreSidebarMenuLinks.companies] : []),
  ];
}
