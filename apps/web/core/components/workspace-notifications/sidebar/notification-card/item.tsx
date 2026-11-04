/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import { CalendarClock, Clock } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Avatar } from "@plane/ui";
import { cn, generateWorkItemLink, getFileURL } from "@plane/utils";
// hooks
import { useWorkspaceNotifications } from "@/hooks/store/notifications";
import { useNotification } from "@/hooks/store/notifications/use-notification";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useProject } from "@/hooks/store/use-project";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useAppRouter } from "@/hooks/use-app-router";
// local imports
import { NotificationContent } from "./content";
import { NotificationItemActions } from "./options";
import { formatFullDateTime, formatRelativeTime } from "./time";

/**
 * `split`  : tampilan penuh /notifications, klik memilih baris dan membuka detail di kanan.
 * `popover`: popover lonceng, klik membuka work item / obrolan di halamannya sendiri.
 */
export type TNotificationItemVariant = "split" | "popover";

type TNotificationItem = {
  workspaceSlug: string;
  notificationId: string;
  variant?: TNotificationItemVariant;
  /** Dipanggil sesudah baris di popover diklik (menutup popover). */
  onNavigate?: () => void;
};

/**
 * Kustomisasi Paradise: baris ringkas tiga lapis, bukan kartu 48px dua baris.
 *   1. Pelaku + apa yang terjadi (maks. 2 baris)
 *   2. KODE-12 Judul work item / cuplikan pesan
 *   3. Project · waktu (atau "ditunda sampai ...")
 * Titik belum-dibaca di kiri, menu aksi "..." di kanan (lihat options/root.tsx).
 */
export const NotificationItem = observer(function NotificationItem({
  workspaceSlug,
  notificationId,
  variant = "split",
  onNavigate,
}: TNotificationItem) {
  const { t, currentLocale } = useTranslation();
  const router = useAppRouter();
  const { currentSelectedNotificationId, setCurrentSelectedNotificationId } = useWorkspaceNotifications();
  const { asJson: notification, markNotificationAsRead } = useNotification(notificationId);
  const { getIsIssuePeeked, setPeekIssue } = useIssueDetail();
  const { getWorkspaceBySlug } = useWorkspace();
  const { getProjectById } = useProject();

  // derived values
  const projectId = notification?.project || undefined;
  const issue = notification?.data?.issue;
  const issueId = issue?.id || undefined;
  const workspace = getWorkspaceBySlug(workspaceSlug);
  const notificationField = notification?.data?.issue_activity.field || undefined;
  const triggeredBy = notification.triggered_by_details || undefined;
  // Kustomisasi Paradise: baris DM (tanpa project) dan baris tenggat (tanpa pemicu).
  const isChat = notificationField === "chat";
  const isDeadline = notificationField === "deadline";
  const chatSenderId = notification?.data?.chat?.pengirim_id;
  const isUnread = !notification.read_at;
  const isSelected = variant === "split" && currentSelectedNotificationId === notification?.id;
  const projectName = projectId ? getProjectById(projectId)?.name : undefined;
  const workItemKey = issue?.identifier && issue?.sequence_id ? `${issue.identifier}-${issue.sequence_id}` : undefined;

  const markAsRead = async () => {
    if (!isUnread) return;
    try {
      await markNotificationAsRead(workspaceSlug);
    } catch (error) {
      console.error(error);
    }
  };

  /** Pilih baris di tampilan penuh: intake lewat InboxContentRoot, sisanya peek overview. */
  const selectInSplitView = () => {
    if (!projectId || !issueId) return;
    setPeekIssue(undefined);
    setCurrentSelectedNotificationId(notificationId);
    if (notification?.is_inbox_issue === false && !getIsIssuePeeked(issueId)) {
      setPeekIssue({ workspaceSlug, projectId, issueId });
    }
  };

  const chatHref = `/${workspaceSlug}/chat/${chatSenderId ? `?dengan=${chatSenderId}` : ""}`;
  const fullViewHref = `/${workspaceSlug}/notifications/`;
  // Intake (is_inbox_issue) tidak punya halaman /browse; ia hanya terbuka di tampilan penuh.
  const opensInFullView = !isChat && (notification?.is_inbox_issue === true || !workItemKey);
  const popoverHref = isChat
    ? chatHref
    : opensInFullView
      ? fullViewHref
      : generateWorkItemLink({
          workspaceSlug,
          projectId,
          issueId,
          projectIdentifier: issue?.identifier,
          sequenceId: issue?.sequence_id,
        });

  const handleSplitClick = async () => {
    if (isChat) {
      await markAsRead();
      router.push(chatHref);
      return;
    }
    selectInSplitView();
    await markAsRead();
  };

  const handlePopoverClick = () => {
    if (opensInFullView) selectInSplitView();
    void markAsRead();
    onNavigate?.();
  };

  if (!workspaceSlug || !notificationId || !notification?.id || !notificationField || !workspace?.id) return <></>;
  if (!projectId && !isChat) return <></>;

  const createdAt = notification.created_at;
  const meta: ReactNode = notification.snoozed_till ? (
    <span className="flex min-w-0 items-center gap-1">
      <Clock className="size-3 shrink-0" aria-hidden />
      <span className="truncate">
        {t("notification_ui.snoozed_until", { date: formatFullDateTime(notification.snoozed_till, currentLocale) })}
      </span>
    </span>
  ) : (
    <time dateTime={createdAt} title={formatFullDateTime(createdAt, currentLocale)} className="shrink-0">
      {formatRelativeTime(createdAt, currentLocale)}
    </time>
  );

  const body = (
    <>
      <span
        aria-hidden
        className={cn("size-1.5 shrink-0 self-center rounded-full", isUnread ? "bg-accent-primary" : "bg-transparent")}
      />
      <span className="relative flex size-8 shrink-0 items-center justify-center rounded-full bg-layer-1">
        {triggeredBy ? (
          <Avatar
            name={triggeredBy.display_name || triggeredBy.first_name}
            src={getFileURL(triggeredBy.avatar_url)}
            size={32}
            shape="circle"
            showTooltip={false}
            className="text-caption-sm-medium"
          />
        ) : isDeadline ? (
          <CalendarClock className="size-4 text-tertiary" aria-hidden />
        ) : null}
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span
          className={cn("line-clamp-2 text-body-xs-regular break-words", isUnread ? "text-primary" : "text-secondary")}
        >
          <NotificationContent
            notification={notification}
            workspaceId={workspace.id}
            workspaceSlug={workspaceSlug}
            projectId={projectId ?? ""}
          />
        </span>
        {isChat ? (
          <span className="truncate text-caption-sm-regular text-secondary">
            {notification?.data?.issue_activity.new_value}
          </span>
        ) : (
          <span className="flex min-w-0 items-baseline gap-1.5 text-caption-sm-regular">
            {workItemKey && <span className="shrink-0 text-caption-sm-medium text-tertiary">{workItemKey}</span>}
            <span className="truncate text-secondary">{issue?.name}</span>
          </span>
        )}
        <span className="flex min-w-0 items-center gap-1 text-caption-sm-regular text-tertiary">
          {projectName && (
            <>
              <span className="truncate">{projectName}</span>
              <span aria-hidden>·</span>
            </>
          )}
          {meta}
        </span>
      </span>
    </>
  );

  const bodyClassName = "flex min-w-0 flex-1 items-start gap-2.5 py-2.5 pl-2 text-left";

  return (
    <div
      className={cn(
        "group relative flex items-start gap-1 border-b border-subtle pr-2 transition-colors hover:bg-layer-transparent-hover",
        { "bg-layer-transparent-selected": isSelected }
      )}
    >
      {variant === "popover" ? (
        <Link href={popoverHref} onClick={handlePopoverClick} className={bodyClassName}>
          {body}
        </Link>
      ) : (
        <button
          type="button"
          aria-current={isSelected || undefined}
          onClick={() => void handleSplitClick()}
          className={bodyClassName}
        >
          {body}
        </button>
      )}
      <div className="pt-2">
        <NotificationItemActions workspaceSlug={workspaceSlug} notificationId={notificationId} variant={variant} />
      </div>
    </div>
  );
});
