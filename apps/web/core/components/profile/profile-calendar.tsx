/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tab Calendar di Your Work
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import useSWR from "swr";
// components
import { ProfileIssuesCalendarLayout } from "@/components/issues/issue-layouts/calendar/roots/profile-issues-root";
import { IssuePeekOverview } from "@/components/issues/peek-overview";
// hooks
import { useIssues } from "@/hooks/store/use-issues";
import { IssuesStoreContext } from "@/hooks/use-issue-layout-store";
// types
import { EIssuesStoreType } from "@plane/types";

/** Kalender hanya masuk akal untuk pekerjaan yang DIBEBANKAN ke orangnya. */
const TAMPILAN = "assigned";

/**
 * Kalender work item milik user di halaman Your Work.
 *
 * Sengaja tab tersendiri, bukan tambahan pilihan layout di tab Assigned.
 * Kalender menuntut work item punya `target_date`; menaruhnya sebagai layout
 * membuat orang yang mengganti layout tiba-tiba melihat daftar yang jauh lebih
 * pendek tanpa penjelasan, karena work item tanpa tenggat lenyap begitu saja.
 * Sebagai tab tersendiri, harapan orang sudah benar sejak awal: ini pandangan
 * tenggat, bukan daftar seluruh tugas.
 */
export const ProfileCalendarPage = observer(function ProfileCalendarPage() {
  const { workspaceSlug, userId } = useParams();
  // store hooks
  const {
    issues: { setViewId },
    issuesFilter: { fetchFilters },
  } = useIssues(EIssuesStoreType.PROFILE);

  // Store profil menolak memuat apa pun sebelum viewId disetel.
  useEffect(() => {
    if (setViewId) setViewId(TAMPILAN);
  }, [setViewId]);

  useSWR(
    workspaceSlug && userId ? `PROFILE_CALENDAR_FILTERS_${workspaceSlug}_${userId}` : null,
    async () => {
      if (workspaceSlug && userId) await fetchFilters(workspaceSlug.toString(), userId.toString());
    },
    { revalidateIfStale: false, revalidateOnFocus: false }
  );

  return (
    <IssuesStoreContext.Provider value={EIssuesStoreType.PROFILE}>
      <div className="flex h-full w-full flex-col overflow-hidden">
        <ProfileIssuesCalendarLayout viewId={TAMPILAN} />
      </div>
      <IssuePeekOverview />
    </IssuesStoreContext.Provider>
  );
});
