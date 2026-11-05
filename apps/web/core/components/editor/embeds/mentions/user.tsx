/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { cn } from "@plane/utils";
// components
import { MemberProfileTrigger } from "@/components/member-profile";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useUser } from "@/hooks/store/user";

type Props = {
  id: string;
};

// Paradise: chip mention membuka kartu profil anggota (MemberProfileTrigger),
// menggantikan popover hover upstream yang hanya memuat nama dan peran project.
export const EditorUserMention = observer(function EditorUserMention(props: Props) {
  const { id } = props;
  // store hooks
  const { data: currentUser } = useUser();
  const { getUserDetails } = useMember();
  // derived values
  const userDetails = getUserDetails(id);

  if (!userDetails) {
    return (
      <div className="not-prose inline rounded-sm bg-layer-1 px-1 py-0.5 text-tertiary no-underline">
        @suspended user
      </div>
    );
  }

  return (
    <div
      className={cn(
        "not-prose inline rounded-sm bg-accent-subtle-active px-1 py-0.5 text-accent-primary no-underline",
        {
          "bg-label-yellow-bg text-label-yellow-text": id === currentUser?.id,
        }
      )}
    >
      <MemberProfileTrigger userId={id} openOnHover>
        <span className="hover:underline">@{userDetails?.display_name}</span>
      </MemberProfileTrigger>
    </div>
  );
});
