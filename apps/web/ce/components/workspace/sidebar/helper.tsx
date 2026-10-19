/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { BookText, LayoutDashboard, MessageSquare, Target } from "lucide-react";
import {
  AnalyticsIcon,
  ArchiveIcon,
  CycleIcon,
  DraftIcon,
  HomeIcon,
  InboxIcon,
  MultipleStickyIcon,
  ProjectIcon,
  ViewsIcon,
  YourWorkIcon,
} from "@plane/propel/icons";
import { cn } from "@plane/utils";

export const getSidebarNavigationItemIcon = (key: string, className: string = "") => {
  switch (key) {
    case "home":
      return <HomeIcon className={cn("size-4 flex-shrink-0", className)} />;
    case "inbox":
      return <InboxIcon className={cn("size-4 flex-shrink-0", className)} />;
    case "projects":
      return <ProjectIcon className={cn("size-4 flex-shrink-0", className)} />;
    case "views":
      return <ViewsIcon className={cn("size-4 flex-shrink-0", className)} />;
    case "active_cycles":
      return <CycleIcon className={cn("size-4 flex-shrink-0", className)} />;
    case "analytics":
      return <AnalyticsIcon className={cn("size-4 flex-shrink-0", className)} />;
    case "your_work":
      return <YourWorkIcon className={cn("size-4 flex-shrink-0", className)} />;
    case "drafts":
      return <DraftIcon className={cn("size-4 flex-shrink-0", className)} />;
    case "archives":
      return <ArchiveIcon className={cn("size-4 flex-shrink-0", className)} />;
    case "stickies":
      return <MultipleStickyIcon className={cn("size-4 flex-shrink-0", className)} />;
    // Item kustom Paradise. Tanpa case di sini switch mengembalikan
    // undefined dan itemnya tampil TANPA ikon, itu yang terjadi pada
    // dashboard_divisi & initiatives sejak dibuat.
    case "wiki":
      return <BookText className={cn("size-4 flex-shrink-0", className)} />;
    case "dashboard_divisi":
      return <LayoutDashboard className={cn("size-4 flex-shrink-0", className)} />;
    case "initiatives":
      return <Target className={cn("size-4 flex-shrink-0", className)} />;
    // "tugas_lintas_divisi" tidak ada: nav-nya dibuang (keputusan user), jadi
    // ikonnya ikut dibuang. Route + halamannya tetap hidup sebagai deep-link.
    case "chat":
      return <MessageSquare className={cn("size-4 flex-shrink-0", className)} />;
  }
};
