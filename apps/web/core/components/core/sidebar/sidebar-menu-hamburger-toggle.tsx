/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { PanelRight } from "lucide-react";
import { useAppTheme } from "@/hooks/store/use-app-theme";

export const SidebarHamburgerToggle = observer(function SidebarHamburgerToggle() {
  // store hooks
  const { toggleSidebar } = useAppTheme();

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    toggleSidebar();
  };

  return (
    <button
      type="button"
      // Tombol ini 28px, di bawah ambang nyaman 44px, dan di layar sempit ia
      // SATU-SATUNYA jalan membuka navigasi. `data-sentuh-lega` melebarkan area
      // sentuhnya lewat pseudo-element di perangkat berpenunjuk kasar saja;
      // ukuran tombol dan ikonnya tidak berubah sedikit pun, jadi tata letak di
      // desktop persis seperti sebelumnya.
      data-sentuh-lega
      className="group grid size-7 flex-shrink-0 place-items-center rounded-sm bg-surface-2 transition-all hover:bg-layer-1"
      onClick={handleClick}
    >
      <PanelRight className="size-3.5 text-secondary transition-all group-hover:text-primary" />
    </button>
  );
});
