/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: popover lonceng Inbox
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { Maximize2 } from "lucide-react";
import useSWR from "swr";
// plane imports
import { ENotificationLoader, ENotificationQueryParamType } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { IconButton } from "@plane/propel/icon-button";
import { InboxIcon } from "@plane/propel/icons";
import { Popover } from "@plane/propel/popover";
import { getNumberCount } from "@plane/utils";
// components
import { SaklarSuara } from "@/components/notifikasi/saklar-suara";
// hooks
import { useWorkspaceNotifications } from "@/hooks/store/notifications";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useAppRouter } from "@/hooks/use-app-router";
// local imports
import { NotificationEmptyState } from "../sidebar/empty-state";
import { AppliedFilters } from "../sidebar/filters/applied-filter";
import { NotificationMarkAllReadButton } from "../sidebar/header/options";
import { NotificationOptionsMenu } from "../sidebar/header/options/options-menu";
import { NotificationsLoader } from "../sidebar/loader";
import { NotificationItem } from "../sidebar/notification-card/item";
import { NotificationTabs } from "../sidebar/tabs";

/** Baris yang dirender di popover. Sisanya lewat "Lihat semua" (tampilan penuh memuat 300). */
const POPOVER_ITEM_LIMIT = 40;

// Kunci SWR yang SAMA dengan NotificationsRoot dan top nav: satu cache, tanpa permintaan ganda.
const KUNCI_JUMLAH_NOTIF = "WORKSPACE_UNREAD_NOTIFICATION_COUNT";
const kunciDaftar = (workspaceSlug: string) => `WORKSPACE_NOTIFICATION_${workspaceSlug}`;

type TNotificationsPopover = {
  workspaceSlug: string;
};

/**
 * Lonceng Inbox di top nav: buka di tempat seperti dropdown notifikasi YouTube,
 * tanpa meninggalkan halaman. Tombol "perluas" membuka /notifications (tampilan
 * terbagi) yang tetap hidup.
 *
 * Satu store dengan tampilan penuh (tab, filter, daftar), jadi filter yang
 * dipasang di sini tetap terpasang saat diperluas.
 *
 * Lapisan: positioner z-30 (di atas top nav z-[27] dan peek overview z-25);
 * popover bersarang di dalamnya (menu opsi, suara, aksi baris) z-40.
 */
export const NotificationsPopover = observer(function NotificationsPopover({ workspaceSlug }: TNotificationsPopover) {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const { unreadNotificationsCount, getUnreadNotificationsCount } = useWorkspaceNotifications();

  useSWR(
    workspaceSlug ? KUNCI_JUMLAH_NOTIF : null,
    workspaceSlug ? () => getUnreadNotificationsCount(workspaceSlug) : null
  );

  const isMentionsEnabled = unreadNotificationsCount.mention_unread_notifications_count > 0;
  const totalNotifications = isMentionsEnabled
    ? unreadNotificationsCount.mention_unread_notifications_count
    : unreadNotificationsCount.total_unread_notifications_count;
  const label =
    totalNotifications > 0
      ? `${t("notification.label")}, ${t("notification_ui.unread_count", { count: totalNotifications })}`
      : t("notification.label");

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <div className="relative flex shrink-0">
        <Popover.Button
          render={
            <IconButton
              variant="ghost"
              size="lg"
              icon={InboxIcon}
              iconClassName="size-5"
              aria-label={label}
              title={label}
            />
          }
        />
        {totalNotifications > 0 && (
          <span
            aria-hidden
            className="pointer-events-none absolute top-0 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-control bg-danger-primary px-1 text-10 leading-none font-semibold text-on-color"
          >
            {isMentionsEnabled ? "@" : ""}
            {getNumberCount(totalNotifications)}
          </span>
        )}
      </div>
      <Popover.Panel
        side="bottom"
        align="end"
        sideOffset={6}
        positionerClassName="z-30"
        // Lebar 26rem, di layar sempit hampir selebar layar (Base UI menggesernya
        // supaya tetap di dalam viewport). Tinggi dibatasi dvh: top nav 40px + jarak.
        className="flex max-h-[min(38rem,calc(100dvh-4rem))] w-[min(26rem,calc(100vw-1rem))] flex-col overflow-hidden rounded-popover border-[0.5px] border-strong bg-surface-1 shadow-raised-200"
      >
        <NotificationsPopoverContent workspaceSlug={workspaceSlug} onClose={() => setIsOpen(false)} />
      </Popover.Panel>
    </Popover>
  );
});

type TNotificationsPopoverContent = {
  workspaceSlug: string;
  onClose: () => void;
};

const NotificationsPopoverContent = observer(function NotificationsPopoverContent({
  workspaceSlug,
  onClose,
}: TNotificationsPopoverContent) {
  const { t } = useTranslation();
  const router = useAppRouter();
  const { getWorkspaceBySlug } = useWorkspace();
  const { loader, getNotifications, notificationIdsByWorkspaceId, currentNotificationTab, paginationInfo } =
    useWorkspaceNotifications();

  const workspace = getWorkspaceBySlug(workspaceSlug);
  const notificationIds = workspace ? notificationIdsByWorkspaceId(workspace.id) : undefined;
  const visibleIds = notificationIds?.slice(0, POPOVER_ITEM_LIMIT) ?? [];
  const hasMore = (notificationIds?.length ?? 0) > POPOVER_ITEM_LIMIT || !!paginationInfo?.next_page_results;
  const fullViewHref = `/${workspaceSlug}/notifications/`;

  // Panel hanya terpasang selama terbuka, jadi tiap buka = revalidasi daftar.
  const { error, mutate } = useSWR(workspace ? kunciDaftar(workspaceSlug) : null, () =>
    getNotifications(
      workspaceSlug,
      notificationIds ? ENotificationLoader.MUTATION_LOADER : ENotificationLoader.INIT_LOADER,
      notificationIds ? ENotificationQueryParamType.CURRENT : ENotificationQueryParamType.INIT
    )
  );

  const openFullView = () => {
    onClose();
    router.push(fullViewHref);
  };

  const renderList = () => {
    if (loader === ENotificationLoader.INIT_LOADER) return <NotificationsLoader rows={5} />;
    if (error && visibleIds.length === 0)
      return (
        <div role="alert" className="flex flex-col items-center gap-2 px-4 py-10 text-center">
          <p className="text-body-xs-regular text-secondary">{t("notification_ui.load_failed")}</p>
          <Button variant="secondary" size="sm" onClick={() => void mutate()}>
            {t("common.retry")}
          </Button>
        </div>
      );
    if (visibleIds.length === 0)
      return (
        <div className="flex justify-center px-4 py-8">
          <NotificationEmptyState currentNotificationTab={currentNotificationTab} />
        </div>
      );
    return visibleIds.map((notificationId) => (
      <NotificationItem
        key={notificationId}
        workspaceSlug={workspaceSlug}
        notificationId={notificationId}
        variant="popover"
        onNavigate={onClose}
      />
    ));
  };

  return (
    <>
      <div className="flex shrink-0 items-center gap-1 border-b border-subtle py-1.5 pr-1.5 pl-3">
        <p className="min-w-0 flex-1 truncate text-body-sm-semibold text-primary">{t("notification.label")}</p>
        <NotificationMarkAllReadButton workspaceSlug={workspaceSlug} />
        <SaklarSuara size="base" />
        <NotificationOptionsMenu workspaceSlug={workspaceSlug} />
        <IconButton
          variant="ghost"
          size="base"
          icon={Maximize2}
          aria-label={t("notification_ui.open_full_view")}
          title={t("notification_ui.open_full_view")}
          onClick={openFullView}
        />
      </div>

      <div className="flex h-9 shrink-0 border-b border-subtle px-1">
        <NotificationTabs />
      </div>

      <AppliedFilters workspaceSlug={workspaceSlug} />

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">{renderList()}</div>

      <div className="flex shrink-0 justify-center border-t border-subtle p-1.5">
        <Button variant="ghost" size="sm" onClick={openFullView} className="w-full">
          {hasMore ? t("notification_ui.see_all") : t("notification_ui.open_full_view")}
        </Button>
      </div>
    </>
  );
});
