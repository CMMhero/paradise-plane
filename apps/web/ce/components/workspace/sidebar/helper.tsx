/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { BookText, LayoutDashboard, Link2, MessageSquare, Target } from "lucide-react";
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
// components
import type { TTintHue } from "@/components/common/tint";
import { TINT_ICON_CLASS } from "@/components/common/tint";

// Paradise: tiap item navigasi punya rona ikon sendiri supaya sidebar tidak
// abu-abu seragam dan item lebih cepat dikenali. Teksnya tetap netral, yang
// berwarna hanya ikonnya. Item yang tak terdaftar tetap mewarisi warna teks.
const NAV_ICON_HUE: Record<string, TTintHue> = {
  home: "indigo",
  your_work: "emerald",
  inbox: "orange",
  projects: "purple",
  views: "pink",
  active_cycles: "yellow",
  analytics: "indigo",
  drafts: "grey",
  archives: "grey",
  stickies: "yellow",
  wiki: "crimson",
  dashboard_divisi: "emerald",
  initiatives: "pink",
  chat: "indigo",
  quick_links: "emerald",
};

export const getSidebarNavigationItemIcon = (key: string, extraClassName: string = "") => {
  const hue = NAV_ICON_HUE[key];
  const className = cn(hue && TINT_ICON_CLASS[hue], extraClassName);
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
    case "quick_links":
      return <Link2 className={cn("size-4 flex-shrink-0", className)} />;
  }
};
