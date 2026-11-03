/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu profil anggota
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Avatar + nama satu anggota yang membuka kartu profilnya saat diklik. Dipakai
 * di tempat yang menampilkan orang sebagai DATA (assignee, pembuat), bukan
 * sebagai kontrol pilihan.
 */

import { observer } from "mobx-react";
import { Avatar } from "@plane/ui";
import { cn, getFileURL } from "@plane/utils";
// hooks
import { useMember } from "@/hooks/store/use-member";
// local
import { MemberProfileTrigger } from "./member-profile-trigger";

type Props = {
  userId: string;
  className?: string;
};

export const MemberNameChip = observer(function MemberNameChip({ userId, className }: Props) {
  const { getUserDetails } = useMember();
  const user = getUserDetails(userId);
  if (!user) return null;
  return (
    <MemberProfileTrigger userId={userId} className={cn("min-w-0", className)}>
      <span className="flex min-w-0 items-center gap-1.5 rounded-sm px-1 py-0.5 hover:bg-layer-transparent-hover">
        <Avatar src={getFileURL(user.avatar_url ?? "")} name={user.display_name} size="md" showTooltip={false} />
        <span className="truncate text-body-xs-medium leading-5 text-primary">{user.display_name}</span>
      </span>
    </MemberProfileTrigger>
  );
});
