/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState, useRef } from "react";
import { observer } from "mobx-react";
import { HelpCircle, MoveLeft } from "lucide-react";
import { Transition } from "@headlessui/react";
import { WEB_BASE_URL } from "@plane/constants";
// plane internal packages
import { NewTabIcon } from "@plane/propel/icons";
import { Tooltip } from "@plane/propel/tooltip";
import { cn } from "@plane/utils";
// hooks
import { useInstance, useTheme } from "@/hooks/store";

// Daftar `helpOptions` DIBUANG. Isinya tiga tautan vendor, `docs.plane.so`,
// `forum.plane.so`, dan issue tracker `makeplane/plane`, dan tidak satu pun
// melayani kantor ini: dokumentasinya untuk produk berbayar mereka, forumnya
// tidak tahu instance kita ada, dan bug fork ini bukan bug mereka.
//
// Sengaja TIDAK diganti tautan karangan. Ini pelajaran yang sama dengan
// `SUPPORT_EMAIL` di `packages/constants/src/endpoints.ts`: menyuruh orang ke
// alamat yang tidak dilayani lebih buruk daripada tidak menyuruh ke mana pun.
// Kalau IT nanti punya halaman panduan internal, tambahkan di sini.
//
// Popovernya tetap ada karena isi satunya lagi masih berguna: nomor versi
// instance, justru itu yang dicari admin waktu menekan tombol ini.

export const AdminSidebarHelpSection = observer(function AdminSidebarHelpSection() {
  // states
  const [isNeedHelpOpen, setIsNeedHelpOpen] = useState(false);
  // store
  const { instance } = useInstance();
  const { isSidebarCollapsed, toggleSidebar } = useTheme();
  // refs
  const helpOptionsRef = useRef<HTMLDivElement | null>(null);

  const redirectionLink = encodeURI(WEB_BASE_URL + "/");

  return (
    <div
      className={cn(
        "flex h-14 w-full flex-shrink-0 items-center justify-between gap-1 self-baseline border-t border-subtle bg-surface-1 px-4",
        {
          "h-auto flex-col py-1.5": isSidebarCollapsed,
        }
      )}
    >
      <div className={`flex items-center gap-1 ${isSidebarCollapsed ? "flex-col justify-center" : "w-full"}`}>
        <Tooltip
          tooltipContent="Buka Paradise Task Tracker"
          position="right"
          className="ml-4"
          disabled={!isSidebarCollapsed}
        >
          <a
            href={redirectionLink}
            className={`relative flex items-center gap-1 rounded-sm bg-layer-1 px-2 py-1 text-body-xs-medium whitespace-nowrap text-secondary`}
          >
            <NewTabIcon width={14} height={14} />
            {!isSidebarCollapsed && "Buka Paradise Task Tracker"}
          </a>
        </Tooltip>
        <Tooltip tooltipContent="Versi instance" position={isSidebarCollapsed ? "right" : "top"} className="ml-4">
          <button
            type="button"
            className={`ml-auto grid place-items-center rounded-md p-1.5 text-secondary outline-none hover:bg-layer-1-hover hover:text-primary ${
              isSidebarCollapsed ? "w-full" : ""
            }`}
            onClick={() => setIsNeedHelpOpen((prev) => !prev)}
          >
            <HelpCircle className="size-4" />
          </button>
        </Tooltip>
        <Tooltip tooltipContent="Toggle sidebar" position={isSidebarCollapsed ? "right" : "top"} className="ml-4">
          <button
            type="button"
            className={`grid place-items-center rounded-md p-1.5 text-secondary outline-none hover:bg-layer-1-hover hover:text-primary ${
              isSidebarCollapsed ? "w-full" : ""
            }`}
            onClick={() => toggleSidebar(!isSidebarCollapsed)}
          >
            <MoveLeft className={`size-4 duration-300 ${isSidebarCollapsed ? "rotate-180" : ""}`} />
          </button>
        </Tooltip>
      </div>

      <div className="relative">
        <Transition
          show={isNeedHelpOpen}
          enter="transition ease-out duration-100"
          enterFrom="transform opacity-0 scale-95"
          enterTo="transform opacity-100 scale-100"
          leave="transition ease-in duration-75"
          leaveFrom="transform opacity-100 scale-100"
          leaveTo="transform opacity-0 scale-95"
        >
          <div
            className={`absolute bottom-2 z-[15] min-w-[10rem] ${
              isSidebarCollapsed ? "left-full" : "-left-[75px]"
            } rounded-sm bg-surface-1 p-1 whitespace-nowrap shadow-raised-100`}
            ref={helpOptionsRef}
          >
            {/* `divide-y` ikut dilepas dari pembungkus di atas: pemisah garis
                hanya masuk akal kalau ada dua kelompok, dan sekarang tinggal satu. */}
            <div className="px-2 py-1 text-10">Versi: v{instance?.current_version}</div>
          </div>
        </Transition>
      </div>
    </div>
  );
});
