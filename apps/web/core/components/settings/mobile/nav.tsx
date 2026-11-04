/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useRef } from "react";
import { observer } from "mobx-react";
import { Menu } from "lucide-react";
import { useOutsideClickDetector } from "@plane/hooks";
import { useTranslation } from "@plane/i18n";
import { useUserSettings } from "@/hooks/store/user";
import { IconButton } from "@plane/propel/icon-button";

type Props = {
  hamburgerContent: React.ComponentType<{ className?: string; isMobile?: boolean }>;
  activePath: string;
};

export const SettingsMobileNav = observer(function SettingsMobileNav(props: Props) {
  const { hamburgerContent: HamburgerContent, activePath } = props;
  // refs
  const sidebarRef = useRef<HTMLDivElement>(null);
  // store hooks
  const { sidebarCollapsed, toggleSidebar } = useUserSettings();
  const { t } = useTranslation();

  useOutsideClickDetector(sidebarRef, () => {
    if (!sidebarCollapsed) toggleSidebar(true);
  });

  return (
    <div className="flex min-h-12 items-center gap-3 border-b border-subtle bg-surface-1 px-page-x py-2 md:hidden">
      <div ref={sidebarRef} className="relative z-20 w-fit">
        {!sidebarCollapsed && (
          <div className="absolute top-10.5 left-0 z-20">
            <HamburgerContent className="max-h-100 rounded-lg border border-subtle pb-3" />
          </div>
        )}
        <IconButton variant="secondary" className="group shrink-0" icon={Menu} onClick={() => toggleSidebar()} />
      </div>
      {/* Judul halaman. Dulu diawali ">" tanpa apa-apa di depannya. */}
      <span className="min-w-0 truncate text-14 font-medium text-primary">{t(activePath)}</span>
    </div>
  );
});
