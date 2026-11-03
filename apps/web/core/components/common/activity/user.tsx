/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// types
import type { TWorkspaceBaseActivity } from "@plane/types";
// components
import { MemberProfileTrigger } from "@/components/member-profile";
// store hooks
import { useMember } from "@/hooks/store/use-member";

type TUser = {
  activity: TWorkspaceBaseActivity;
  customUserName?: string;
};

export const User = observer(function User(props: TUser) {
  const { activity, customUserName } = props;
  // store hooks
  const { getUserDetails } = useMember();
  // derived values
  const actorDetail = getUserDetails(activity.actor);

  return (
    <>
      {customUserName || actorDetail?.display_name.includes("-intake") ? (
        <span className="font-medium text-primary">{customUserName || "Sistem"}</span>
      ) : (
        <MemberProfileTrigger userId={actorDetail?.id}>
          <span className="font-medium text-primary hover:underline">{actorDetail?.display_name}</span>
        </MemberProfileTrigger>
      )}
    </>
  );
});
