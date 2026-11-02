/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { CheckCircle2, Clock, XCircle } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
// components
import { IssueActivityBlockComponent } from "@/components/issues/issue-detail/issue-activity/activity/actions/helpers/activity-block";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";

export type TAdditionalActivityRoot = {
  activityId: string;
  showIssue?: boolean;
  ends: "top" | "bottom" | undefined;
  field: string | undefined;
};

// Kustomisasi Paradise (KEP-55): log persetujuan ditulis server sebagai
// `field="approval"` dengan kata kerja requested / approved / rejected
// (`catat_aktivitas_persetujuan` di `plane/utils/hierarki.py`).
const IKON_PERSETUJUAN = {
  requested: <Clock className="h-3.5 w-3.5 text-warning-primary" aria-hidden="true" />,
  approved: <CheckCircle2 className="h-3.5 w-3.5 text-success-primary" aria-hidden="true" />,
  rejected: <XCircle className="h-3.5 w-3.5 text-danger-primary" aria-hidden="true" />,
} as const;

type TVerbPersetujuan = keyof typeof IKON_PERSETUJUAN;

const ApprovalActivity = observer(function ApprovalActivity(props: Omit<TAdditionalActivityRoot, "field">) {
  const { activityId, ends } = props;
  const { t } = useTranslation();
  const {
    activity: { getActivityById },
  } = useIssueDetail();

  const activity = getActivityById(activityId);
  const verb = activity?.verb as TVerbPersetujuan | undefined;
  if (!activity || !verb || !(verb in IKON_PERSETUJUAN)) return <></>;

  return (
    <IssueActivityBlockComponent icon={IKON_PERSETUJUAN[verb]} activityId={activityId} ends={ends}>
      {t(`issue.approval.activity.${verb}`)}
      {activity.new_value && (
        <span className="text-tertiary"> {t("issue.approval.activity.reason", { reason: activity.new_value })}</span>
      )}
    </IssueActivityBlockComponent>
  );
});

export const AdditionalActivityRoot = observer(function AdditionalActivityRoot(props: TAdditionalActivityRoot) {
  const { field, ...rest } = props;
  if (field === "approval") return <ApprovalActivity {...rest} />;
  return <></>;
});
