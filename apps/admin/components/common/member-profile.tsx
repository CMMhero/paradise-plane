/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: kartu profil anggota di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Bungkus avatar/nama akun mana pun di God Mode supaya klik membuka kartu
 * profilnya, kartu yang sama dengan di apps/web (`@plane/propel/member-profile-card`).
 * Datanya dari endpoint instance admin `members/<id>/profile/`, baru diminta
 * saat kartu dibuka.
 *
 *   <MemberProfileTrigger userId={id}>...</MemberProfileTrigger>
 */

import { useState } from "react";
import type { ReactNode } from "react";
import useSWR from "swr";
// plane imports
import {
  MemberProfileBadge,
  MemberProfileFields,
  MemberProfileHeader,
  MemberProfilePopover,
  MemberProfileSkeleton,
  type TMemberProfilePlacement,
} from "@plane/propel/member-profile-card";
import { InstanceMemberService, type TInstanceMemberProfile } from "@plane/services";
import { Avatar } from "@plane/propel/avatar";
import { getFileURL } from "@plane/utils";
import { avatarTone } from "./paradise-styles";

const memberService = new InstanceMemberService();

const LABELS = {
  placement: "Placement",
  morePlacements: (count: number) => `+${count} more`,
  email: "Email",
  phoneExtension: "Phone extension",
  notSet: "Not set",
};
const LEVEL_LABELS: Record<number, string> = { 10: "Staff", 20: "Supervisor", 30: "Manager", 40: "Director" };

const toPlacements = (profile: TInstanceMemberProfile): TMemberProfilePlacement[] =>
  profile.penempatan
    .filter((p) => p.departemen || p.divisi)
    .map((p) => ({
      key: `${p.departemen?.id ?? ""}-${p.divisi?.id ?? ""}`,
      division: p.divisi,
      department: p.departemen,
      levelLabel: LEVEL_LABELS[p.tingkat] ?? null,
    }));

function ProfileCard({ userId }: { userId: string }) {
  const { data: profile, error } = useSWR<TInstanceMemberProfile>(
    `GODMODE_MEMBER_PROFILE_${userId}`,
    () => memberService.profil(userId),
    { revalidateOnFocus: false, dedupingInterval: 60_000, shouldRetryOnError: false }
  );
  if (error) return <p className="text-12 text-tertiary">Could not load this profile.</p>;
  if (!profile) return <MemberProfileSkeleton />;
  const fullName = [profile.first_name, profile.last_name].filter(Boolean).join(" ") || profile.display_name;
  const tone = avatarTone(profile.display_name || profile.email);
  return (
    <>
      <MemberProfileHeader
        avatar={
          <Avatar
            src={getFileURL(profile.avatar_url ?? "")}
            name={profile.display_name || profile.email}
            size={40}
            className="text-18"
            showTooltip={false}
            fallbackBackgroundColor={tone.bg}
            fallbackTextColor={tone.text}
          />
        }
        fullName={fullName}
        handle={profile.display_name}
        badges={!profile.is_active ? <MemberProfileBadge tone="danger">Deactivated</MemberProfileBadge> : null}
      />
      <MemberProfileFields
        labels={LABELS}
        placements={toPlacements(profile)}
        email={profile.email}
        phoneExtension={profile.phone_extension}
      />
    </>
  );
}

export function MemberProfileTrigger({
  userId,
  name,
  children,
  className,
}: {
  userId: string | null | undefined;
  /** Dipakai untuk label pembaca layar. */
  name: string;
  children: ReactNode;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  if (!userId) return <>{children}</>;
  return (
    <MemberProfilePopover
      open={open}
      onOpenChange={setOpen}
      ariaLabel={`Open profile of ${name}`}
      triggerClassName={className}
      card={open ? <ProfileCard userId={userId} /> : null}
    >
      {children}
    </MemberProfilePopover>
  );
}
