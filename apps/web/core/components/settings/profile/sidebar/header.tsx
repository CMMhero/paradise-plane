/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { ArrowLeft } from "lucide-react";
import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { IconButton } from "@plane/propel/icon-button";
import { Avatar } from "@plane/ui";
import { getFileURL } from "@plane/utils";
// hooks
import { useUser } from "@/hooks/store/user";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useAppRouter } from "@/hooks/use-app-router";

export const ProfileSettingsSidebarHeader = observer(function ProfileSettingsSidebarHeader() {
  // router
  const router = useAppRouter();
  // store hooks
  const { data: currentUser } = useUser();
  const { getWorkspaceRedirectionUrl } = useWorkspace();
  const { t } = useTranslation();

  return (
    <div className="shrink-0">
      {/* Kustomisasi Paradise: halaman ini di luar layout workspace, jadi tak ada
          sidebar utama maupun top bar. Tanpa panah ini satu-satunya jalan pulang
          adalah tombol Back browser. Polanya cermin header Workspace settings. */}
      <div className="flex items-center gap-1 pb-3 text-body-md-medium">
        <IconButton
          variant="ghost"
          size="base"
          icon={ArrowLeft}
          aria-label={t("back_to_workspace")}
          onClick={() => router.push(getWorkspaceRedirectionUrl())}
        />
        <p>{t("back_to_workspace")}</p>
      </div>
      <div className="flex items-center gap-2">
        <div className="shrink-0">
          <Avatar
            src={getFileURL(currentUser?.avatar_url ?? "")}
            name={currentUser?.display_name}
            size={32}
            shape="circle"
            className="text-16"
          />
        </div>
        <div className="truncate">
          <p className="truncate text-body-sm-medium">
            {currentUser?.first_name} {currentUser?.last_name}
          </p>
          <p className="truncate text-caption-md-regular">{currentUser?.email}</p>
        </div>
      </div>
    </div>
  );
});
