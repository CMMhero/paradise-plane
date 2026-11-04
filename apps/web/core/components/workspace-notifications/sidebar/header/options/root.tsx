/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { CheckCheck } from "lucide-react";
// plane imports
import { ENotificationLoader } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { IconButton } from "@plane/propel/icon-button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Tooltip } from "@plane/propel/tooltip";
import { Spinner } from "@plane/ui";
// components
import { SaklarSuara } from "@/components/notifikasi/saklar-suara";
// hooks
import { useWorkspaceNotifications } from "@/hooks/store/notifications";
import { usePlatformOS } from "@/hooks/use-platform-os";
// local imports
import { NotificationOptionsMenu } from "./options-menu";

type TNotificationHeaderOptions = {
  workspaceSlug: string;
};

export const NotificationMarkAllReadButton = observer(function NotificationMarkAllReadButton({
  workspaceSlug,
}: TNotificationHeaderOptions) {
  const { t } = useTranslation();
  const { isMobile } = usePlatformOS();
  const { loader, markAllNotificationsAsRead } = useWorkspaceNotifications();
  const label = t("notification.options.mark_all_as_read");

  const handleMarkAllNotificationsAsRead = async () => {
    // NOTE: loader dipakai supaya permintaan tidak berulang selama yang pertama berjalan.
    if (loader) return;
    try {
      await markAllNotificationsAsRead(workspaceSlug);
    } catch (error) {
      console.error(error);
      setToast({ type: TOAST_TYPE.ERROR, title: t("common.error.label"), message: t("common.error.message") });
    }
  };

  return (
    <Tooltip tooltipContent={label} isMobile={isMobile} position="bottom">
      <IconButton
        size="base"
        variant="ghost"
        icon={loader === ENotificationLoader.MARK_ALL_AS_READY ? Spinner : CheckCheck}
        aria-label={label}
        onClick={() => void handleMarkAllNotificationsAsRead()}
      />
    </Tooltip>
  );
});

/**
 * Tombol kanan header Inbox, dipakai di tampilan penuh DAN di popover lonceng.
 *
 * Dulu lima tombol (tandai semua, refresh, filter, suara xl, menu). Filter dan
 * menu memakai PopoverMenu @plane/ui yang akarnya `w-full h-full`, jadi di kolom
 * sempit keduanya berebut lebar penuh dan tombol "..." terdorong keluar header.
 * Sekarang tiga tombol berukuran sama; refresh, filter, dan tampilan pindah ke
 * satu menu.
 */
export const NotificationSidebarHeaderOptions = observer(function NotificationSidebarHeaderOptions({
  workspaceSlug,
}: TNotificationHeaderOptions) {
  return (
    <div className="flex shrink-0 items-center gap-1">
      <NotificationMarkAllReadButton workspaceSlug={workspaceSlug} />
      <SaklarSuara size="base" />
      <NotificationOptionsMenu workspaceSlug={workspaceSlug} />
    </div>
  );
});
