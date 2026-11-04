/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { CheckCircle2, Clock, Network, XCircle } from "lucide-react";
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

const humanizeField = (field: string | null | undefined) => (field ?? "item").replace(/_/g, " ");

// Safety net for any IssueActivity.field the web has no dedicated renderer for
// (custom Paradise fields, future upstream fields). Shows field + old -> new
// so a row is never just an actor and a timestamp.
const GenericActivity = observer(function GenericActivity(props: Omit<TAdditionalActivityRoot, "showIssue">) {
  const { activityId, ends, field } = props;
  const {
    activity: { getActivityById },
  } = useIssueDetail();

  const activity = getActivityById(activityId);
  if (!activity) return <></>;

  const name = humanizeField(field ?? activity.field);
  const verb = activity.verb ? activity.verb.replace(/_/g, " ") : "changed";
  const hasChange = Boolean(activity.old_value || activity.new_value);

  return (
    <IssueActivityBlockComponent
      icon={<Network className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />}
      activityId={activityId}
      ends={ends}
    >
      <>
        {verb} <span className="font-medium text-primary">{name}</span>
        {hasChange && (
          <>
            {": "}
            {activity.old_value && <span className="text-tertiary">{activity.old_value}</span>}
            {activity.old_value && activity.new_value && " -> "}
            {activity.new_value && <span className="font-medium text-primary">{activity.new_value}</span>}
          </>
        )}
        .
      </>
    </IssueActivityBlockComponent>
  );
});

const ApprovalActivity = observer(function ApprovalActivity(props: Omit<TAdditionalActivityRoot, "field">) {
  const { activityId, ends } = props;
  const { t } = useTranslation();
  const {
    activity: { getActivityById },
  } = useIssueDetail();

  const activity = getActivityById(activityId);
  const verb = activity?.verb as TVerbPersetujuan | undefined;
  if (!activity) return <></>;
  // Unknown verb: never render an empty line, fall back to the generic row.
  if (!verb || !(verb in IKON_PERSETUJUAN))
    return <GenericActivity activityId={activityId} ends={ends} field="approval" />;

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
  return <GenericActivity {...rest} field={field} />;
});
