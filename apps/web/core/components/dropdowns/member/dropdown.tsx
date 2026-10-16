/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import type { LucideIcon } from "lucide-react";
// hooks
import { useMember } from "@/hooks/store/use-member";
// local imports
import { MemberDropdownBase } from "./base";
import type { MemberDropdownProps } from "./types";

type TMemberDropdownProps = {
  icon?: LucideIcon;
  memberIds?: string[];
  onClose?: () => void;
  optionsClassName?: string;
  projectId?: string;
  renderByDefault?: boolean;
} & MemberDropdownProps;

export const MemberDropdown = observer(function MemberDropdown(props: TMemberDropdownProps) {
  const { memberIds: propsMemberIds, projectId, hanyaDiriSendiri } = props;
  // router params
  const { workspaceSlug } = useParams();
  // store hooks
  const {
    getUserDetails,
    getMemberIds,
    project: { getProjectMemberIds, fetchProjectMembers },
    workspace: { workspaceMemberIds, fetchWorkspaceMembers },
  } = useMember();

  // Mode staf: daftar disaring ke diri sendiri DULU, sebelum fallback ke
  // anggota project/workspace. `hanyaDiriSendiri=null` = nonaktif.
  const dasar = propsMemberIds
    ? propsMemberIds
    : projectId
      ? getProjectMemberIds(projectId, false)
      : workspaceMemberIds;
  const memberIds =
    hanyaDiriSendiri != null ? (dasar ?? []).filter((id) => id === hanyaDiriSendiri) : dasar;

  const onDropdownOpen = () => {
    if (!memberIds && projectId && workspaceSlug) fetchProjectMembers(workspaceSlug.toString(), projectId);
    // Daftar di atas hanya berisi ID. NAMA-nya diambil `getUserDetails` dari
    // `memberRoot.memberMap`, dan di seluruh apps/web map itu cuma punya SATU
    // penulis: `fetchWorkspaceMembers` (workspace-member.store.ts:240), yang
    // dipanggil sekali saja di WorkspaceAuthWrapper lewat useSWR ber-
    // `revalidateIfStale: false`.
    //
    // Akibatnya kalau map itu kosong saat dropdown dibuka, tiap baris tampil
    // sebagai avatar "?" tanpa nama, dan TIDAK ADA yang akan mengisinya:
    // membuka-tutup dropdown pun tidak menolong karena hanya anggota project
    // yang dimuat ulang. Muat-malas namanya di sini, memakai pola yang sudah
    // dipakai baris di atas untuk anggota project.
    if (workspaceSlug && getMemberIds().length === 0) fetchWorkspaceMembers(workspaceSlug.toString());
  };

  return (
    <MemberDropdownBase
      {...props}
      getUserDetails={getUserDetails}
      memberIds={memberIds ?? []}
      onDropdownOpen={onDropdownOpen}
    />
  );
});
