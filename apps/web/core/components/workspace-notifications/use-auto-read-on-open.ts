/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Inbox menandai dibaca sendiri saat dibuka
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useRef } from "react";
// hooks
import { useWorkspaceNotifications } from "@/hooks/store/notifications";

/**
 * Jeda sebelum daftar ditandai dibaca. Titik "belum dibaca" sempat terlihat, jadi
 * orang tahu mana yang baru, dan membuka-lalu-menutup sekilas tidak menghabiskan
 * notifikasinya (penghitung waktunya dibatalkan saat Inbox ditutup).
 */
const JEDA_TANDAI_DIBACA_MS = 2500;

/**
 * Inbox yang dibuka (tampilan penuh atau popover lonceng) menandai notifikasinya
 * dibaca sendiri, sekali per pembukaan. Memakai aksi "tandai semua dibaca" yang
 * sama dengan tombolnya, jadi cakupannya mengikuti tab dan filter yang sedang
 * terpasang: yang tidak terlihat (tab Mentions saat tab All dibuka, arsip,
 * ditunda) tidak ikut tersentuh. Kabar yang masuk selagi Inbox terbuka tetap
 * belum dibaca sampai dibuka lagi.
 */
export const useAutoReadOnOpen = (workspaceSlug: string | undefined) => {
  const { loader, unreadNotificationsCount, markAllNotificationsAsRead } = useWorkspaceNotifications();
  const sudah = useRef(false);
  const adaBelumDibaca =
    unreadNotificationsCount.total_unread_notifications_count +
      unreadNotificationsCount.mention_unread_notifications_count >
    0;
  // Tunggu daftarnya selesai dimuat; `loader` juga terisi saat tombol "tandai semua" berjalan.
  const siap = !loader && adaBelumDibaca;

  useEffect(() => {
    if (!workspaceSlug || sudah.current || !siap) return;
    const penghitung = window.setTimeout(() => {
      sudah.current = true;
      markAllNotificationsAsRead(workspaceSlug).catch((error) => console.error(error));
    }, JEDA_TANDAI_DIBACA_MS);
    return () => window.clearTimeout(penghitung);
  }, [workspaceSlug, siap, markAllNotificationsAsRead]);
};
