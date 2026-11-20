/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useParams } from "next/navigation";
import type { IWorkspaceSidebarNavigationItem } from "@plane/constants";
import { getNumberCount } from "@plane/utils";
import { CountChip } from "@/components/common/count-chip";
import { useAntreanWorkspace } from "@/components/issues/workspace-approvals/use-antrean-workspace";
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
// "persetujuan" dan "tugas_lintas_divisi" kembali (keputusan user 2026-11-20).
// Persetujuan hanya bagi yang punya wewenang memutuskan (`useNavPersetujuanTerlihat`).
const PARADISE_ALWAYS_VISIBLE_ITEMS = [
  "wiki",
  "dashboard_divisi",
  "kinerja",
  "initiatives",
  "persetujuan",
  "tugas_lintas_divisi",
  "chat",
];

/**
 * Menu Persetujuan hanya untuk yang punya wewenang memutuskan; staf tidak
 * melihatnya. Selama balasannya belum datang menu disembunyikan, supaya tidak
 * berkedip muncul lalu hilang bagi staf.
 */
export const useNavPersetujuanTerlihat = (workspaceSlug: string | undefined) =>
  useAntreanWorkspace(workspaceSlug).data?.boleh_memutuskan ?? false;

function PersetujuanBadge({ workspaceSlug }: { workspaceSlug: string }) {
  const jumlah = useAntreanWorkspace(workspaceSlug).data?.jumlah ?? 0;
  if (jumlah <= 0) return null;
  return (
    <div className="ml-auto">
      <CountChip count={getNumberCount(jumlah)} />
    </div>
  );
}

// `additionalRender` adalah titik ekstensi yang memang sudah disediakan
// SidebarItemBase untuk menempelkan sesuatu di kanan label, dan itu yang dipakai
// upstream untuk lencana notifikasi. Dipakai ulang di sini, bukan menambah props
// baru ke komponen bersama.
const renderTambahan = (itemKey: string, workspaceSlug: string) => {
  if (itemKey === "chat") return <ChatUnreadBadge workspaceSlug={workspaceSlug} />;
  if (itemKey === "persetujuan") return <PersetujuanBadge workspaceSlug={workspaceSlug} />;
  return null;
};

export function SidebarItem({ item }: Props) {
  const { workspaceSlug } = useParams();
  const persetujuanTerlihat = useNavPersetujuanTerlihat(
    item.key === "persetujuan" ? workspaceSlug?.toString() : undefined
  );
  if (item.key === "persetujuan" && !persetujuanTerlihat) return null;
  return (
    <SidebarItemBase
      item={item}
      additionalStaticItems={PARADISE_ALWAYS_VISIBLE_ITEMS}
      additionalRender={renderTambahan}
    />
  );
}
