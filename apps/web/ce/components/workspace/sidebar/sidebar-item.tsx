/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { IWorkspaceSidebarNavigationItem } from "@plane/constants";
import { SidebarItemBase } from "@/components/workspace/sidebar/sidebar-item";
// local imports
import { ChatUnreadBadge } from "./chat-unread-badge";

type Props = {
  item: IWorkspaceSidebarNavigationItem;
};

// SidebarItemBase menyembunyikan item nav dinamis yang tidak ter-pin
// (`if (!isPinned && !staticItems.includes(item.key)) return null`), dan default
// preferensi adalah TIDAK ter-pin. Akibatnya fitur kustom kita tidak pernah
// muncul di sidebar siapa pun kecuali tiap user mem-pin-nya sendiri lewat
// "Customize navigation", yang tidak akan dilakukan orang yang belum tahu
// fiturnya ada. Didaftarkan di sini supaya selalu tampil, memakai titik
// ekstensi yang memang sudah disediakan upstream.
// ⚠️ Mem-pin lewat "Customize navigation" TIDAK berpengaruh untuk kunci di
// daftar ini. Backend hanya menyimpan preferensi untuk kunci yang terdaftar di
// WorkspaceUserPreference.UserPreferenceKeys, dan PATCH-nya `continue` diam-diam
// untuk kunci yang tidak dikenal. Jadi centangnya tersimpan di layar lalu hilang
// saat halaman dimuat ulang. Karena itulah daftar ini ada.
// "tugas_lintas_divisi" SENGAJA tidak ada: keputusan user — lintas divisi
// dikerjakan dari daftar project (direktur melihat semua divisi), bukan dari
// menu sendiri. Endpoint + halamannya tetap hidup, hanya tidak dipin di sini.
const PARADISE_ALWAYS_VISIBLE_ITEMS = ["wiki", "dashboard_divisi", "initiatives", "chat"];

// `additionalRender` adalah titik ekstensi yang memang sudah disediakan
// SidebarItemBase untuk menempelkan sesuatu di kanan label, dan itu yang dipakai
// upstream untuk lencana notifikasi. Dipakai ulang di sini, bukan menambah props
// baru ke komponen bersama.
const renderTambahan = (itemKey: string, workspaceSlug: string) =>
  itemKey === "chat" ? <ChatUnreadBadge workspaceSlug={workspaceSlug} /> : null;

export function SidebarItem({ item }: Props) {
  return (
    <SidebarItemBase
      item={item}
      additionalStaticItems={PARADISE_ALWAYS_VISIBLE_ITEMS}
      additionalRender={renderTambahan}
    />
  );
}
