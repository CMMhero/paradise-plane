/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: saklar notifikasi peramban
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { BellRing } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { ToggleSwitch } from "@plane/ui";
import useLocalStorage from "@/hooks/use-local-storage";
import { KUNCI_NOTIF_PERAMBAN, KUNCI_SPANDUK, izinPeramban, tampilkanNotifPeramban } from "./peramban";
import type { TIzinPeramban } from "./peramban";

/**
 * Bagian "Browser notifications" di popup suara (halaman Chat & panel
 * Pemberitahuan).
 *
 * Ini juga satu-satunya jalan menyalakan izin sesudah spanduk izin ditutup
 * dengan "Nanti saja". `requestPermission` dipanggil dari klik, bukan efek:
 * Safari menolak diam-diam permintaan yang bukan dari sentuhan pengguna.
 *
 * Izin dibaca saat komponen dipasang (popup dibuka), jadi izin yang diubah di
 * pengaturan peramban terbaca begitu popup dibuka lagi.
 */
export function SaklarPeramban() {
  const { t } = useTranslation();
  const { storedValue: nyala, setValue: setNyala } = useLocalStorage<boolean>(KUNCI_NOTIF_PERAMBAN, true);
  const { setValue: setSpandukDitutup } = useLocalStorage<boolean>(KUNCI_SPANDUK, false);
  const [izin, setIzin] = useState<TIzinPeramban>(() => izinPeramban());
  const aktif = nyala !== false && izin === "granted";
  const terkunci = izin === "denied" || izin === "tidak-didukung";

  const ubah = async () => {
    if (aktif) {
      setNyala(false);
      return;
    }
    setNyala(true);
    if (izin === "default") setIzin(await Notification.requestPermission());
    // Izin sudah diurus dari sini; spanduk di pojok kiri bawah tidak perlu menawarkan lagi.
    setSpandukDitutup(true);
  };

  const uji = () => {
    const terkirim = tampilkanNotifPeramban({
      judul: t("notification_ui.browser_test_title"),
      isi: t("notification_ui.browser_test_body"),
      tag: "uji-notifikasi-peramban",
    });
    if (!terkirim) setToast({ type: TOAST_TYPE.ERROR, title: t("notification_ui.browser_unsupported") });
  };

  const keterangan =
    izin === "denied"
      ? t("notification_ui.browser_blocked")
      : izin === "tidak-didukung"
        ? t("notification_ui.browser_unsupported")
        : t("notification_ui.browser_hint");

  return (
    <div className="flex flex-col gap-2 border-t border-subtle pt-3">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-12 text-secondary">
          <BellRing className="size-3.5" />
          {t("notification_ui.browser_title")}
        </span>
        <ToggleSwitch
          value={aktif}
          label={t("notification_ui.browser_title")}
          disabled={terkunci}
          onChange={() => void ubah()}
        />
      </div>
      <p className={`text-11 ${izin === "denied" ? "text-danger-primary" : "text-tertiary"}`}>{keterangan}</p>
      {aktif ? (
        <Button variant="secondary" size="base" onClick={uji} className="w-full">
          {t("notification_ui.browser_test")}
        </Button>
      ) : null}
    </div>
  );
}
