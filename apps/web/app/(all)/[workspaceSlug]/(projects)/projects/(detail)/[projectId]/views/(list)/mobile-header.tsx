/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// components
import { ViewListMobileHeader } from "@/components/views/view-list-mobile-header";
// hooks
import { useMember } from "@/hooks/store/use-member";

export const ViewMobileHeader = observer(function ViewMobileHeader() {
  const {
    project: { projectMemberIds },
  } = useMember();

  return <ViewListMobileHeader memberIds={projectMemberIds ?? undefined} />;
});
