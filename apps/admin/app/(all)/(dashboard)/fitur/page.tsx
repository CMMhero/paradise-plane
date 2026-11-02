/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: saklar fitur di God Mode
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Satu-satunya tempat menyalakan/mematikan modul dan fitur Paradise serta
 * mengatur angka operasionalnya (KEP-40). Dulu tiap saklar tinggal di
 * `apps/api/.env` dan baru berlaku sesudah `docker compose up -d`; sekarang
 * nilainya di InstanceConfiguration dan dibaca ulang tiap dipanggil
 * (apps/api/plane/utils/saklar_instance.py).
 */

import { Fragment, useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import useSWR from "swr";
import { PARADISE_MODULE_DEFAULTS } from "@plane/constants";
import { setPromiseToast } from "@plane/propel/toast";
import type {
  TInstanceParadiseModuleKeys,
  TInstanceParadiseNumberKeys,
  TInstanceParadiseToggleKeys,
  TParadiseModule,
} from "@plane/types";
import { Loader, ToggleSwitch } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
import { Section, SettingRow } from "@/components/common/paradise";
// hooks
import { useInstance } from "@/hooks/store";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import type { Route } from "./+types/page";
import { InputAngka } from "./angka";

/** Kunci saklar modul, sama seperti `MODUL_APLIKASI` di server. */
const kunciModul = (modul: TParadiseModule) => `ENABLE_${modul.toUpperCase()}` as TInstanceParadiseModuleKeys;

/** Nilai saat barisnya belum ada di database. Cermin `SAKLAR_BAWAAN` di server. */
const BAWAAN = {
  ENABLE_DEADLINE_REMINDER: "0",
  ENABLE_CHAT_EMAIL: "0",
  ENABLE_GOOGLE_CALENDAR_SYNC: "0",
  ENABLE_TUGAS_KE_DM: "1",
  HIERARKI_GERBANG_TUGAS: "0",
  ...Object.fromEntries(
    Object.entries(PARADISE_MODULE_DEFAULTS).map(([modul, nyala]) => [
      kunciModul(modul as TParadiseModule),
      nyala ? "1" : "0",
    ])
  ),
} as Record<TInstanceParadiseToggleKeys, "0" | "1">;

/** Urutan tampil di God Mode, mengikuti letak menunya di aplikasi. */
const KELOMPOK_MODUL: {
  judul: "group_sidebar" | "group_workspace" | "group_project" | "group_work_item";
  modul: TParadiseModule[];
}[] = [
  { judul: "group_sidebar", modul: ["inbox", "your_work", "stickies", "drafts", "quick_links"] },
  {
    judul: "group_workspace",
    modul: ["dashboards", "initiatives", "views", "analytics", "chat", "wiki", "archives"],
  },
  { judul: "group_project", modul: ["work_items", "modules", "pages", "intake", "approvals"] },
  { judul: "group_work_item", modul: ["time_tracking", "estimates"] },
];

/** [bawaan, min, maks]. Cermin `SETELAN_ANGKA` di server, yang juga menolak nilai di luar rentang. */
const ANGKA: Record<TInstanceParadiseNumberKeys, [number, number, number]> = {
  CHAT_EMAIL_QUIET_MINUTES: [10, 1, 1440],
  CHAT_EMAIL_INTERVAL_MINUTES: [60, 5, 10080],
  LOGIN_HISTORY_RETENTION_DAYS: [90, 7, 730],
  TRASH_RETENTION_DAYS: [60, 1, 3650],
  DASHBOARD_PERHATIAN_PERSEN: [5, 1, 100],
  DASHBOARD_KRITIS_PERSEN: [15, 1, 100],
};

type TKunci = TInstanceParadiseToggleKeys | TInstanceParadiseNumberKeys;

const FiturPage = observer(function FiturPage(_props: Route.ComponentProps) {
  const { s, fill } = useGodmodeStrings();
  const t = s.fitur;
  const { fetchInstanceConfigurations, formattedConfig, updateInstanceConfigurations } = useInstance();
  const [sedangSimpan, setSedangSimpan] = useState<TKunci | null>(null);
  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  const nyala = (kunci: TInstanceParadiseToggleKeys) => (formattedConfig?.[kunci] ?? BAWAAN[kunci]) === "1";
  const angka = (kunci: TInstanceParadiseNumberKeys) => {
    const tersimpan = Number(formattedConfig?.[kunci]);
    return Number.isFinite(tersimpan) && formattedConfig?.[kunci] ? tersimpan : ANGKA[kunci][0];
  };

  const simpan = async (kunci: TKunci, nilai: string, pesanSukses: string, nama: string) => {
    setSedangSimpan(kunci);
    const janji = updateInstanceConfigurations({ [kunci]: nilai });
    setPromiseToast(janji, {
      loading: t.saving,
      success: { title: t.saved, message: () => pesanSukses },
      error: { title: t.save_failed, message: () => nama },
    });
    try {
      await janji;
    } catch {
      // Toast di atas sudah memberi tahu; kontrol tetap menunjukkan nilai server.
    } finally {
      setSedangSimpan(null);
    }
  };

  const ubahSaklar = (kunci: TInstanceParadiseToggleKeys, nama: string) => {
    const nilai = nyala(kunci) ? "0" : "1";
    void simpan(kunci, nilai, fill(nilai === "1" ? t.on : t.off, { name: nama }), nama);
  };

  const saklar = (kunci: TInstanceParadiseToggleKeys, nama: string, deskripsi: string) => (
    <SettingRow
      title={nama}
      description={deskripsi}
      control={
        <ToggleSwitch
          value={nyala(kunci)}
          onChange={() => ubahSaklar(kunci, nama)}
          size="sm"
          disabled={sedangSimpan !== null}
          label={nama}
        />
      }
    />
  );

  const setelanAngka = (kunci: TInstanceParadiseNumberKeys, nama: string, deskripsi: string, unit: string) => {
    const [, min, max] = ANGKA[kunci];
    return (
      <SettingRow
        title={nama}
        description={deskripsi}
        control={
          <InputAngka
            value={angka(kunci)}
            min={min}
            max={max}
            unit={unit}
            label={nama}
            isDisabled={sedangSimpan !== null}
            onSave={(n) => simpan(kunci, String(n), `${nama}: ${n} ${unit}`, nama)}
          />
        }
      />
    );
  };

  const kredensialLengkap = Boolean(
    formattedConfig?.GOOGLE_CALENDAR_CLIENT_ID && formattedConfig?.GOOGLE_CALENDAR_CLIENT_SECRET
  );
  const gcalNyala = nyala("ENABLE_GOOGLE_CALENDAR_SYNC");

  return (
    <PageWrapper header={{ title: t.title, description: t.description }}>
      {formattedConfig ? (
        <div className="space-y-10">
          {KELOMPOK_MODUL.map(({ judul, modul }, i) => (
            <Section
              key={judul}
              title={t[judul]}
              // Penjelasan umum cukup sekali, di kelompok pertama.
              description={judul === "group_project" ? t.group_project_hint : i === 0 ? t.modules_hint : undefined}
              bordered
            >
              {modul.map((m) => (
                <Fragment key={m}>{saklar(kunciModul(m), t.modules[m].name, t.modules[m].desc)}</Fragment>
              ))}
            </Section>
          ))}

          <Section title={t.group_tugas} bordered>
            {saklar("ENABLE_TUGAS_KE_DM", t.dm_name, t.dm_desc)}
            {saklar("HIERARKI_GERBANG_TUGAS", t.gerbang_name, t.gerbang_desc)}
          </Section>

          <Section title={t.group_email} bordered>
            {saklar("ENABLE_DEADLINE_REMINDER", t.deadline_name, t.deadline_desc)}
            {saklar("ENABLE_CHAT_EMAIL", t.chat_name, t.chat_desc)}
            {setelanAngka("CHAT_EMAIL_QUIET_MINUTES", t.chat_quiet_name, t.chat_quiet_desc, t.unit_minutes)}
            {setelanAngka("CHAT_EMAIL_INTERVAL_MINUTES", t.chat_interval_name, t.chat_interval_desc, t.unit_minutes)}
          </Section>

          <Section title={t.group_kalender} bordered>
            <SettingRow
              title={t.gcal_name}
              description={t.gcal_desc}
              note={
                !kredensialLengkap && (
                  <p className="text-11 text-warning-primary">
                    {t.gcal_missing}{" "}
                    <Link href="/api-keys/google/" className="font-medium underline">
                      {t.gcal_missing_link}
                    </Link>
                  </p>
                )
              }
              control={
                <ToggleSwitch
                  value={gcalNyala}
                  onChange={() => ubahSaklar("ENABLE_GOOGLE_CALENDAR_SYNC", t.gcal_name)}
                  size="sm"
                  // Mematikan selalu boleh; menyalakan butuh kredensial, kalau tidak
                  // tiap putaran hanya menulis galat ke log.
                  disabled={sedangSimpan !== null || (!gcalNyala && !kredensialLengkap)}
                  label={t.gcal_name}
                />
              }
            />
          </Section>

          <Section title={t.group_dashboard} description={t.group_dashboard_hint} bordered>
            {setelanAngka("DASHBOARD_PERHATIAN_PERSEN", t.dash_attention_name, t.dash_attention_desc, t.unit_percent)}
            {setelanAngka("DASHBOARD_KRITIS_PERSEN", t.dash_critical_name, t.dash_critical_desc, t.unit_percent)}
          </Section>

          <Section title={t.group_retention} description={t.group_retention_hint} bordered>
            {setelanAngka("TRASH_RETENTION_DAYS", t.trash_name, t.trash_desc, t.unit_days)}
            {setelanAngka("LOGIN_HISTORY_RETENTION_DAYS", t.login_name, t.login_desc, t.unit_days)}
          </Section>
        </div>
      ) : (
        <Loader className="space-y-4">
          <Loader.Item height="60px" />
          <Loader.Item height="60px" />
          <Loader.Item height="60px" />
        </Loader>
      )}
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [{ title: "Features - God Mode" }];

export default FiturPage;
