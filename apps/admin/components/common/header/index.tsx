/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { usePathname } from "next/navigation";
import { Menu, Settings } from "lucide-react";
// icons
import { IconButton } from "@plane/propel/icon-button";
import { Breadcrumbs } from "@plane/ui";
// components
import { BreadcrumbLink } from "../breadcrumb-link";
// hooks
import { useTheme } from "@/hooks/store";
import { CommandPalette } from "@/components/command-palette/command-palette";
// local imports
import { CORE_HEADER_SEGMENT_LABELS } from "./core";
import { EXTENDED_HEADER_SEGMENT_LABELS } from "./extended";

export const HamburgerToggle = observer(function HamburgerToggle() {
  const { isSidebarCollapsed, toggleSidebar } = useTheme();
  return (
    <IconButton
      variant="ghost"
      size="base"
      icon={Menu}
      aria-label="Toggle sidebar"
      className="md:hidden"
      onClick={() => toggleSidebar(!isSidebarCollapsed)}
    />
  );
});

const HEADER_SEGMENT_LABELS = {
  ...CORE_HEADER_SEGMENT_LABELS,
  ...EXTENDED_HEADER_SEGMENT_LABELS,
};

// Paradise: unlabeled segments read as sentence case, not caps.
const toSentenceCase = (segment: string): string => {
  const words = segment.replace(/[-_]+/g, " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
};

// Function to dynamically generate breadcrumb items based on pathname
const generateBreadcrumbItems = (pathname: string) => {
  const pathSegments = pathname.split("/").slice(1); // removing the first empty string.
  pathSegments.pop();

  let currentUrl = "";
  const breadcrumbItems = pathSegments.map((segment) => {
    currentUrl += "/" + segment;
    return {
      title: HEADER_SEGMENT_LABELS[segment] ?? toSentenceCase(segment),
      href: currentUrl,
    };
  });
  return breadcrumbItems;
};

export const AdminHeader = observer(function AdminHeader() {
  const pathName = usePathname();

  const breadcrumbItems = generateBreadcrumbItems(pathName || "");

  return (
    <div className="relative z-10 flex h-header w-full flex-shrink-0 flex-row items-center justify-between gap-x-2 gap-y-4 border-b border-subtle bg-surface-1 p-4">
      <div className="flex w-full flex-grow items-center gap-2 overflow-ellipsis whitespace-nowrap">
        <HamburgerToggle />
        {breadcrumbItems.length >= 0 && (
          <div>
            <Breadcrumbs>
              <Breadcrumbs.Item
                component={
                  <BreadcrumbLink
                    href="/general/"
                    label="Settings"
                    icon={<Settings className="h-4 w-4 text-tertiary" />}
                  />
                }
              />
              {breadcrumbItems.map(
                (item) =>
                  item.title && (
                    <Breadcrumbs.Item
                      key={item.title}
                      component={<BreadcrumbLink href={item.href} label={item.title} />}
                    />
                  )
              )}
            </Breadcrumbs>
          </div>
        )}
      </div>
      <CommandPalette />
    </div>
  );
});
