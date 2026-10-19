/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tab Calendar di Your Work
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// components
import { PageHead } from "@/components/core/page-title";
import { ProfileCalendarPage } from "@/components/profile/profile-calendar";

function ProfileCalendarRoute() {
  return (
    <>
      <PageHead title="Profile - Calendar" />
      <ProfileCalendarPage />
    </>
  );
}

export default ProfileCalendarRoute;
