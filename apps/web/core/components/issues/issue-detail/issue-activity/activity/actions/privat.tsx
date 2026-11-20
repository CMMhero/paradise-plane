/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: aktivitas tugas privat (P29)
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { LockIcon } from "@plane/propel/icons";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// components
import { IssueActivityBlockComponent } from "./";

type TIssuePrivateActivity = { activityId: string; ends: "top" | "bottom" | undefined };

export const IssuePrivateActivity = observer(function IssuePrivateActivity(props: TIssuePrivateActivity) {
  const { activityId, ends } = props;
  const { t } = useTranslation();
  const {
    activity: { getActivityById },
  } = useIssueDetail();

  const activity = getActivityById(activityId);

  if (!activity) return <></>;
  return (
    <IssueActivityBlockComponent
      icon={<LockIcon className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />}
      activityId={activityId}
      ends={ends}
    >
      <>{activity.new_value === "true" ? t("privat.activity.on") : t("privat.activity.off")}</>
    </IssueActivityBlockComponent>
  );
});
