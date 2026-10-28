/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: sambungan Google Calendar
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
// services
import { GoogleCalendarService, type TGoogleCalendarStatus } from "@/services/google_calendar.service";

const layanan = new GoogleCalendarService();

function waktuLokal(iso: string | null, lokal: string, belumPernah: string): string {
  if (!iso) return belumPernah;
  return new Date(iso).toLocaleString(lokal, { dateStyle: "medium", timeStyle: "short" });
}

export const ConnectionsProfileSettings = observer(function ConnectionsProfileSettings() {
  const { t, currentLocale } = useTranslation();
  const [status, setStatus] = useState<TGoogleCalendarStatus | null>(null);
  const [sibuk, setSibuk] = useState(false);

  const muat = useCallback(async () => {
    try {
      setStatus(await layanan.status());
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    void muat();
  }, [muat]);

  // Callback Google mengembalikan pengguna ke halaman ini dengan hasilnya di
  // query string. Dibaca sekali lalu DIBERSIHKAN dari URL, supaya menyegarkan
  // halaman tidak memunculkan ulang notifikasi lama.
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const hasil = q.get("status");
    if (!hasil) return;

    if (hasil === "tersambung") {
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("connections_ui.connected_toast") });
    } else if (hasil === "batal") {
      setToast({ type: TOAST_TYPE.INFO, title: t("connections_ui.cancelled_toast") });
    } else {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("connections_ui.failed_toast"),
        message: q.get("sebab") ?? undefined,
      });
    }
    window.history.replaceState({}, "", window.location.pathname);
    void muat();
  }, [muat, t]);

  const sambung = async () => {
    setSibuk(true);
    try {
      window.location.href = await layanan.urlSambung();
    } catch (e: unknown) {
      setSibuk(false);
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("connections_ui.start_failed"),
        message: (e as { error?: string })?.error,
      });
    }
  };

  const putus = async () => {
    setSibuk(true);
    try {
      await layanan.putus();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("connections_ui.disconnected_title"),
        // Disebut eksplisit supaya orang tidak panik mencari acaranya hilang,
        // dan tidak pula mengira tenggat lamanya masih akan diperbarui.
        message: t("connections_ui.disconnected_message"),
      });
      await muat();
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: t("connections_ui.disconnect_failed") });
    } finally {
      setSibuk(false);
    }
  };

  return (
    <section className="flex flex-col gap-6">
      <div>
        <h3 className="text-xl font-medium">{t("connections_ui.title")}</h3>
        <p className="text-sm mt-1 text-secondary">{t("connections_ui.description")}</p>
      </div>

      <div className="rounded-lg border border-subtle p-5">
        <div className="flex items-start justify-between gap-6">
          <div className="min-w-0">
            <h4 className="font-medium">Google Calendar</h4>
            <p className="text-sm mt-1 text-secondary">{t("connections_ui.google_description")}</p>

            {status?.tersambung && (
              // Tidak menampilkan alamat akun Google di sini: izin yang kita
              // minta tidak mencakup pembacaan profil, jadi nilainya tidak
              // tersedia tanpa meminta izin tambahan yang tidak sepadan.
              <dl className="text-sm mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                <dt className="text-secondary">{t("connections_ui.status")}</dt>
                <dd>{t("connections_ui.connected")}</dd>
                <dt className="text-secondary">{t("connections_ui.last_sync")}</dt>
                <dd>{waktuLokal(status.terakhir_sinkron, currentLocale, t("connections_ui.never"))}</dd>
              </dl>
            )}

            {status?.galat_terakhir && (
              <p className="text-sm text-danger mt-3">
                {t("connections_ui.sync_failed", { error: status.galat_terakhir })}
              </p>
            )}

            {status && !status.tersedia && (
              // Tanpa penjelasan ini, tombol yang mati terlihat seperti aplikasi
              // yang rusak, dan orang akan melapor ke IT alih-alih ke yang bisa
              // mengisinya di God Mode.
              <p className="text-sm mt-3 text-secondary">{t("connections_ui.unavailable")}</p>
            )}
          </div>

          <div className="shrink-0">
            {status?.tersambung ? (
              <Button variant="secondary" onClick={putus} disabled={sibuk}>
                {t("connections_ui.disconnect")}
              </Button>
            ) : (
              <Button variant="primary" onClick={sambung} disabled={sibuk || !status?.tersedia}>
                {t("connections_ui.connect")}
              </Button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
});
