/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: avatar yang membuka kartu profil
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import type { LucideIcon } from "lucide-react";
import { MembersPropertyIcon } from "@plane/propel/icons";
// plane ui
import { Avatar, AvatarGroup } from "@plane/ui";
import { cn, getFileURL } from "@plane/utils";
// components
import { MemberProfileTrigger } from "@/components/member-profile/member-profile-trigger";
// hooks
import { useMember } from "@/hooks/store/use-member";

type TAvatarSize = "sm" | "md" | "base" | "lg" | number;

type AvatarProps = {
  showTooltip: boolean;
  userIds: string | string[] | null;
  icon?: LucideIcon;
  size?: TAvatarSize;
  /** Klik avatar membuka kartu profil anggota (lihat MemberProfileTrigger). */
  showProfileCard?: boolean;
};

type MemberAvatarProps = {
  userId: string;
  showProfileCard: boolean;
  // Diisi AvatarGroup lewat cloneElement.
  size?: TAvatarSize;
  showTooltip?: boolean;
};

const MemberAvatar = observer(function MemberAvatar({ userId, showProfileCard, size, showTooltip }: MemberAvatarProps) {
  const { getUserDetails } = useMember();
  const userDetails = getUserDetails(userId);
  if (!userDetails) return null;
  const avatar = (
    <Avatar
      src={getFileURL(userDetails.avatar_url ?? "")}
      name={userDetails.display_name}
      size={size}
      showTooltip={showTooltip}
    />
  );
  if (!showProfileCard) return avatar;
  return (
    <MemberProfileTrigger userId={userId} className="rounded-full">
      {avatar}
    </MemberProfileTrigger>
  );
});

export const ButtonAvatars = observer(function ButtonAvatars(props: AvatarProps) {
  const { showTooltip, userIds, icon: Icon, size = "md", showProfileCard = false } = props;
  // store hooks
  const { getUserDetails } = useMember();

  if (Array.isArray(userIds)) {
    const knownIds = userIds.filter((userId) => getUserDetails(userId));
    if (knownIds.length > 0)
      return (
        <AvatarGroup size={size} showTooltip={!showTooltip}>
          {knownIds.map((userId) => (
            <MemberAvatar key={userId} userId={userId} showProfileCard={showProfileCard} />
          ))}
        </AvatarGroup>
      );
  } else if (userIds) {
    return <MemberAvatar userId={userIds} showProfileCard={showProfileCard} size={size} showTooltip={!showTooltip} />;
  }

  return Icon ? (
    <Icon className="h-3 w-3 flex-shrink-0" />
  ) : (
    <MembersPropertyIcon className={cn("mx-[4px] h-3 w-3 flex-shrink-0")} />
  );
});
