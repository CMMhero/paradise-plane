/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { PanelLeft } from "lucide-react";
// hooks
import { useAppTheme } from "@/hooks/store/use-app-theme";
import { isSidebarToggleVisible } from "@/plane-web/components/desktop";
import { IconButton } from "@plane/propel/icon-button";

export const AppSidebarToggleButton = observer(function AppSidebarToggleButton() {
  // store hooks
  const { toggleSidebar, sidebarPeek, toggleSidebarPeek, sidebarCollapsed } = useAppTheme();
  const { t } = useTranslation();

  if (!isSidebarToggleVisible()) return null;
  return (
    <IconButton
      size="base"
      variant="ghost"
      icon={PanelLeft}
      aria-label={t(
        sidebarCollapsed
          ? "aria_labels.projects_sidebar.expand_sidebar"
          : "aria_labels.projects_sidebar.collapse_sidebar"
      )}
      onClick={() => {
        if (sidebarPeek) toggleSidebarPeek(false);
        toggleSidebar();
      }}
    />
  );
});
