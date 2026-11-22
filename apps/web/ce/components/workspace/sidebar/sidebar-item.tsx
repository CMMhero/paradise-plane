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

// Persetujuan hanya bagi yang punya wewenang memutuskan (`useNavPersetujuanTerlihat`).

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
  return <SidebarItemBase item={item} additionalRender={renderTambahan} />;
}
