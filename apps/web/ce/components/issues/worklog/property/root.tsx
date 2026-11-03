/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Time Tracking
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { isParadiseFeatureEnabled } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { useCallback, useEffect, useState } from "react";
import { observer } from "mobx-react";
import { Clock, Plus, Trash2 } from "lucide-react";
// plane imports
import { IconButton } from "@plane/propel/icon-button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Input } from "@plane/ui";
// hooks
import { useUser } from "@/hooks/store/user";
// services
import { IssueWorkLogService, type TIssueWorkLog } from "@/services/issue/issue_worklog.service";

type TIssueWorklogProperty = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled: boolean;
};

const worklogService = new IssueWorkLogService();

type TTerjemah = (key: string, params?: Record<string, unknown>) => string;

const formatDuration = (minutes: number, t: TTerjemah): string => {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h > 0 && m > 0) return t("division_dashboard_ui.duration_hm", { h, m });
  if (h > 0) return t("division_dashboard_ui.duration_h", { h });
  return t("division_dashboard_ui.duration_m", { m });
};

const displayName = (log: TIssueWorkLog, t: TTerjemah): string => {
  const d = log.logged_by_detail;
  if (!d) return t("chat_ui.member");
  return d.display_name || [d.first_name, d.last_name].filter(Boolean).join(" ") || t("chat_ui.member");
};

const IssueWorklogPropertyContent = observer(function IssueWorklogPropertyContent(props: TIssueWorklogProperty) {
  const { t } = useTranslation();
  const { workspaceSlug, projectId, issueId, disabled } = props;
  // store
  const { data: currentUser } = useUser();
  // state
  const [logs, setLogs] = useState<TIssueWorkLog[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [hours, setHours] = useState("");
  const [minutes, setMinutes] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchLogs = useCallback(async () => {
    if (!workspaceSlug || !projectId || !issueId) return;
    try {
      const res = await worklogService.list(workspaceSlug, projectId, issueId);
      setLogs(res.work_logs ?? []);
      setTotal(res.total_duration ?? 0);
    } catch {
      // senyap: sidebar tak boleh crash kalau gagal muat
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug, projectId, issueId]);

  useEffect(() => {
    void fetchLogs();
  }, [fetchLogs]);

  const handleAdd = async () => {
    const duration = (parseInt(hours || "0", 10) || 0) * 60 + (parseInt(minutes || "0", 10) || 0);
    if (duration <= 0) {
      setToast({ type: TOAST_TYPE.ERROR, title: t("worklog_ui.empty_title"), message: t("worklog_ui.empty_message") });
      return;
    }
    setIsSubmitting(true);
    try {
      await worklogService.create(workspaceSlug, projectId, issueId, { duration, description: description.trim() });
      setHours("");
      setMinutes("");
      setDescription("");
      await fetchLogs();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("worklog_ui.logged_title"),
        message: t("worklog_ui.logged_message", { duration: formatDuration(duration, t) }),
      });
    } catch (err: unknown) {
      const message = (err as { error?: string })?.error ?? t("worklog_ui.save_failed");
      setToast({ type: TOAST_TYPE.ERROR, title: t("worklog_ui.failed"), message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (log: TIssueWorkLog) => {
    try {
      await worklogService.remove(workspaceSlug, projectId, issueId, log.id);
      await fetchLogs();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("worklog_ui.deleted_title"),
        message: t("worklog_ui.deleted_message"),
      });
    } catch (err: unknown) {
      const message = (err as { error?: string })?.error ?? t("worklog_ui.delete_failed");
      setToast({ type: TOAST_TYPE.ERROR, title: t("worklog_ui.failed"), message });
    }
  };

  if (isLoading) return <></>;

  return (
    <div className="flex w-full flex-col gap-2 border-t border-subtle py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-13 text-secondary">
          <Clock className="size-4" />
          <span>{t("worklog_ui.title")}</span>
        </div>
        {total > 0 && (
          <span className="rounded-control bg-layer-3 px-1.5 py-0.5 text-12 font-medium text-primary">
            {formatDuration(total, t)}
          </span>
        )}
      </div>

      {logs.length > 0 && (
        <div className="flex flex-col gap-1">
          {logs.map((log) => {
            const canDelete = !disabled && currentUser?.id === log.logged_by;
            return (
              <div
                key={log.id}
                className="group flex items-start justify-between gap-2 rounded-item px-1 py-1 hover:bg-layer-2"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5 text-12">
                    <span className="font-medium text-primary">{formatDuration(log.duration, t)}</span>
                    <span className="text-tertiary">·</span>
                    <span className="truncate text-tertiary">{displayName(log, t)}</span>
                  </div>
                  {log.description && <p className="truncate text-12 text-tertiary">{log.description}</p>}
                </div>
                {canDelete && (
                  <IconButton
                    variant="ghost"
                    size="sm"
                    icon={Trash2}
                    onClick={() => handleDelete(log)}
                    className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
                    aria-label={t("worklog_ui.delete")}
                  />
                )}
              </div>
            );
          })}
        </div>
      )}

      {!disabled && (
        <div className="flex items-center gap-1.5">
          <Input
            type="number"
            min={0}
            placeholder={t("worklog_ui.hours")}
            value={hours}
            onChange={(e) => setHours(e.target.value)}
            mode="primary"
            inputSize="xs"
            className="w-14 text-12 focus:border-accent-strong"
          />
          <Input
            type="number"
            min={0}
            max={59}
            placeholder={t("worklog_ui.minutes")}
            value={minutes}
            onChange={(e) => setMinutes(e.target.value)}
            mode="primary"
            inputSize="xs"
            className="w-16 text-12 focus:border-accent-strong"
          />
          <Input
            type="text"
            placeholder={t("worklog_ui.note_placeholder")}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            mode="primary"
            inputSize="xs"
            className="min-w-0 flex-1 text-12 focus:border-accent-strong"
          />
          <IconButton
            variant="primary"
            size="base"
            icon={Plus}
            disabled={isSubmitting}
            onClick={handleAdd}
            aria-label={t("worklog_ui.add")}
          />
        </div>
      )}
    </div>
  );
});

/** Dimatikan lewat PARADISE_FEATURES.timeTracking: tak ada panel, tak ada request worklog. */
export function IssueWorklogProperty(props: TIssueWorklogProperty) {
  if (!isParadiseFeatureEnabled("timeTracking")) return null;
  return <IssueWorklogPropertyContent {...props} />;
}
