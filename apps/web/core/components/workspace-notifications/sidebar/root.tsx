/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { Header, Row, ERowVariant, EHeaderVariant, ContentWrapper } from "@plane/ui";
import { cn } from "@plane/utils";
// hooks
import { useWorkspaceNotifications } from "@/hooks/store/notifications";
import { useWorkspace } from "@/hooks/store/use-workspace";
// plane web components
import { ExtendedAppHeader } from "@/plane-web/components/common/extended-app-header";
import { NotificationListRoot } from "@/plane-web/components/workspace-notifications/list-root";
// local imports
import { NotificationEmptyState } from "./empty-state";
import { AppliedFilters } from "./filters/applied-filter";
import { NotificationSidebarHeader } from "./header";
import { NotificationsLoader } from "./loader";
import { NotificationTabs } from "./tabs";

export const NotificationsSidebarRoot = observer(function NotificationsSidebarRoot() {
  const { workspaceSlug } = useParams();
  // hooks
  const { getWorkspaceBySlug } = useWorkspace();
  const { currentSelectedNotificationId, loader, notificationIdsByWorkspaceId, currentNotificationTab } =
    useWorkspaceNotifications();

  // derived values
  const workspace = workspaceSlug ? getWorkspaceBySlug(workspaceSlug.toString()) : undefined;
  const notificationIds = workspace ? notificationIdsByWorkspaceId(workspace.id) : undefined;

  if (!workspaceSlug || !workspace) return <></>;

  return (
    <div
      className={cn(
        // Paradise: lebar tetap 22/26rem, bukan 3/12. Di layar 1280px 3/12 cuma
        // ~250px, terlalu sempit untuk header (tombol "..." keluar) dan untuk baris.
        "relative z-[10] h-full flex-shrink-0 border-0 border-subtle bg-surface-1 transition-all max-md:overflow-hidden md:w-[22rem] md:border-r lg:w-[26rem]",
        currentSelectedNotificationId ? "w-0" : "w-full"
      )}
    >
      <div className="relative flex h-full w-full flex-col">
        {/* items-center + gap: tombol buka sidebar (ExtendedAppHeader) dulu menempel
            di atas karena Row tidak memusatkan isinya. Sama dengan AppHeader. */}
        <Row className="flex h-header flex-shrink-0 items-center gap-2 border-b border-subtle">
          <ExtendedAppHeader header={<NotificationSidebarHeader workspaceSlug={workspaceSlug.toString()} />} />
        </Row>

        <Header variant={EHeaderVariant.SECONDARY} className="justify-start">
          <NotificationTabs />
        </Header>

        {/* applied filters */}
        <AppliedFilters workspaceSlug={workspaceSlug.toString()} />

        {/* rendering notifications */}
        {loader === "init-loader" ? (
          <div className="relative h-full w-full overflow-hidden">
            <NotificationsLoader />
          </div>
        ) : (
          <>
            {notificationIds && notificationIds.length > 0 ? (
              <ContentWrapper variant={ERowVariant.HUGGING}>
                <NotificationListRoot workspaceSlug={workspaceSlug.toString()} workspaceId={workspace?.id} />
              </ContentWrapper>
            ) : (
              <div className="relative flex h-full w-full items-center justify-center">
                <NotificationEmptyState currentNotificationTab={currentNotificationTab} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
});
