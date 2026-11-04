/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { NOTIFICATION_TABS } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { cn, getNumberCount } from "@plane/utils";
// components
import { CountChip } from "@/components/common/count-chip";
// hooks
import { useWorkspaceNotifications } from "@/hooks/store/notifications";

/**
 * Tab All / Mentions, dipakai tampilan penuh dan popover lonceng. Diangkat dari
 * sidebar/root.tsx (dulu `div role="button"`); sekarang tombol `role="tab"`.
 * Pemanggil yang menentukan tinggi barisnya.
 */
export const NotificationTabs = observer(function NotificationTabs() {
  const { t } = useTranslation();
  const { unreadNotificationsCount, currentNotificationTab, setCurrentNotificationTab } = useWorkspaceNotifications();

  return (
    <div role="tablist" className="flex h-full items-stretch">
      {NOTIFICATION_TABS.map((tab) => {
        const isActive = currentNotificationTab === tab.value;
        const count = tab.count(unreadNotificationsCount);
        return (
          <button
            key={tab.value}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => {
              if (!isActive) setCurrentNotificationTab(tab.value);
            }}
            className={cn(
              "relative flex items-center gap-1 px-3 text-body-xs-medium transition-colors",
              isActive ? "text-accent-primary" : "text-primary hover:text-secondary"
            )}
          >
            {t(tab.i18n_label)}
            {count > 0 && <CountChip count={getNumberCount(count)} />}
            {isActive && (
              <span aria-hidden className="absolute right-0 bottom-0 left-0 rounded-t-md border border-accent-strong" />
            )}
          </button>
        );
      })}
    </div>
  );
});
