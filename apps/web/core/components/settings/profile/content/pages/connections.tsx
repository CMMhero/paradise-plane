/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: sambungan Google Calendar
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { Button } from "@plane/propel/button";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
// services
import { GoogleCalendarService, type TGoogleCalendarStatus } from "@/services/google_calendar.service";

const layanan = new GoogleCalendarService();

function waktuLokal(iso: string | null): string {
  if (!iso) return "belum pernah";
  return new Date(iso).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" });
}

export const ConnectionsProfileSettings = observer(function ConnectionsProfileSettings() {
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
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Google Calendar tersambung" });
    } else if (hasil === "batal") {
      setToast({ type: TOAST_TYPE.INFO, title: "Penyambungan dibatalkan" });
    } else {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Penyambungan gagal",
        message: q.get("sebab") ?? undefined,
      });
    }
    window.history.replaceState({}, "", window.location.pathname);
    void muat();
  }, [muat]);

  const sambung = async () => {
    setSibuk(true);
    try {
      window.location.href = await layanan.urlSambung();
    } catch (e: unknown) {
      setSibuk(false);
      setToast({
        type: TOAST_TYPE.ERROR,
        title: "Tidak bisa memulai penyambungan",
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
        title: "Sambungan diputus",
        // Disebut eksplisit supaya orang tidak panik mencari acaranya hilang,
        // dan tidak pula mengira tenggat lamanya masih akan diperbarui.
        message: "Acara yang sudah ada tetap di kalender Anda, tapi tidak lagi diperbarui.",
      });
      await muat();
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Gagal memutus sambungan" });
    } finally {
      setSibuk(false);
    }
  };

  return (
    <section className="flex flex-col gap-6">
      <div>
        <h3 className="text-xl font-medium">Sambungan</h3>
        <p className="text-sm mt-1 text-secondary">
          Hubungkan layanan lain supaya tenggat Anda muncul di tempat Anda sudah terbiasa melihatnya.
        </p>
      </div>

      <div className="rounded-lg border border-subtle p-5">
        <div className="flex items-start justify-between gap-6">
          <div className="min-w-0">
            <h4 className="font-medium">Google Calendar</h4>
            <p className="text-sm mt-1 text-secondary">
              Work item yang ditugaskan kepada Anda dan punya tenggat akan muncul sebagai acara sepanjang hari. Tenggat
              yang digeser ikut berpindah sendiri, dan yang selesai akan hilang dari kalender.
            </p>

            {status?.tersambung && (
              // Tidak menampilkan alamat akun Google di sini: izin yang kita
              // minta tidak mencakup pembacaan profil, jadi nilainya tidak
              // tersedia tanpa meminta izin tambahan yang tidak sepadan.
              <dl className="text-sm mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                <dt className="text-secondary">Status</dt>
                <dd>Tersambung</dd>
                <dt className="text-secondary">Sinkron terakhir</dt>
                <dd>{waktuLokal(status.terakhir_sinkron)}</dd>
              </dl>
            )}

            {status?.galat_terakhir && (
              <p className="text-sm text-danger mt-3">
                Sinkronisasi terakhir gagal. Coba putuskan lalu sambungkan ulang. ({status.galat_terakhir})
              </p>
            )}

            {status && !status.tersedia && (
              // Tanpa penjelasan ini, tombol yang mati terlihat seperti aplikasi
              // yang rusak, dan orang akan melapor ke IT alih-alih ke yang bisa
              // mengisinya di God Mode.
              <p className="text-sm mt-3 text-secondary">
                Belum tersedia di instance ini. Administrator perlu mengisi kredensial Google Calendar lebih dulu.
              </p>
            )}
          </div>

          <div className="shrink-0">
            {status?.tersambung ? (
              <Button variant="secondary" onClick={putus} disabled={sibuk}>
                Putuskan
              </Button>
            ) : (
              <Button variant="primary" onClick={sambung} disabled={sibuk || !status?.tersedia}>
                Sambungkan
              </Button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
});
