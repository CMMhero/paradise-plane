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
import { CustomSelect, Loader, ToggleSwitch } from "@plane/ui";
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
  AUTO_START_DATE_ON_START: "1",
  AUTO_DUE_DATE_ON_DONE: "1",
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
  AUTO_ARCHIVE_DONE_DAYS: [90, 0, 365],
  DUE_DATE_ON_EARLY_DONE: [0, 0, 1],
  OVERDUE_GRACE_DAYS: [0, 0, 30],
  DASHBOARD_ON_TIME_WINDOW_DAYS: [30, 7, 365],
  CHAT_DELETE_WINDOW_HOURS: [24, 0, 8760],
};

/** Pilihan hari arsip otomatis, 0 = mati. Cermin `SETELAN_PILIHAN` di server, yang menolak nilai lain. */
const PILIHAN_ARSIP_HARI = [0, 7, 14, 30, 60, 90, 180, 365] as const;

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

  const hariArsip = angka("AUTO_ARCHIVE_DONE_DAYS");
  const teksHariArsip = (n: number) => (n === 0 ? t.auto_archive_off : fill(t.auto_archive_after, { count: n }));
  const pilihArsip = (
    <SettingRow
      title={t.auto_archive_name}
      description={t.auto_archive_desc}
      control={
        <CustomSelect
          value={hariArsip}
          label={teksHariArsip(hariArsip)}
          onChange={(v: number) =>
            void simpan(
              "AUTO_ARCHIVE_DONE_DAYS",
              String(v),
              `${t.auto_archive_name}: ${teksHariArsip(v)}`,
              t.auto_archive_name
            )
          }
          disabled={sedangSimpan !== null}
          input
        >
          {PILIHAN_ARSIP_HARI.map((n) => (
            <CustomSelect.Option key={n} value={n}>
              {teksHariArsip(n)}
            </CustomSelect.Option>
          ))}
        </CustomSelect>
      }
    />
  );

  // 0 = Due date rencana dibiarkan, 1 = dimajukan ke hari selesai. Cermin
  // `SETELAN_PILIHAN[DUE_DATE_ON_EARLY_DONE]` di server.
  const majuSaatSelesaiAwal = angka("DUE_DATE_ON_EARLY_DONE");
  const teksSelesaiAwal = (n: number) => (n === 1 ? t.early_done_move : t.early_done_keep);
  const pilihSelesaiAwal = (
    <SettingRow
      title={t.early_done_name}
      description={t.early_done_desc}
      control={
        <CustomSelect
          value={majuSaatSelesaiAwal}
          label={teksSelesaiAwal(majuSaatSelesaiAwal)}
          onChange={(v: number) =>
            void simpan(
              "DUE_DATE_ON_EARLY_DONE",
              String(v),
              `${t.early_done_name}: ${teksSelesaiAwal(v)}`,
              t.early_done_name
            )
          }
          disabled={sedangSimpan !== null}
          input
        >
          {[0, 1].map((n) => (
            <CustomSelect.Option key={n} value={n}>
              {teksSelesaiAwal(n)}
            </CustomSelect.Option>
          ))}
        </CustomSelect>
      }
    />
  );

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
            {pilihArsip}
          </Section>

          <Section title={t.group_tanggal} description={t.group_tanggal_hint} bordered>
            {saklar("AUTO_START_DATE_ON_START", t.auto_start_name, t.auto_start_desc)}
            {saklar("AUTO_DUE_DATE_ON_DONE", t.auto_due_name, t.auto_due_desc)}
            {pilihSelesaiAwal}
            {setelanAngka("OVERDUE_GRACE_DAYS", t.grace_name, t.grace_desc, t.unit_days)}
          </Section>

          <Section title={t.group_email} bordered>
            {saklar("ENABLE_DEADLINE_REMINDER", t.deadline_name, t.deadline_desc)}
            {saklar("ENABLE_CHAT_EMAIL", t.chat_name, t.chat_desc)}
            {setelanAngka("CHAT_EMAIL_QUIET_MINUTES", t.chat_quiet_name, t.chat_quiet_desc, t.unit_minutes)}
            {setelanAngka("CHAT_EMAIL_INTERVAL_MINUTES", t.chat_interval_name, t.chat_interval_desc, t.unit_minutes)}
          </Section>

          <Section title={t.group_chat} bordered>
            {setelanAngka("CHAT_DELETE_WINDOW_HOURS", t.chat_delete_name, t.chat_delete_desc, t.unit_hours)}
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
            {setelanAngka("DASHBOARD_ON_TIME_WINDOW_DAYS", t.dash_on_time_name, t.dash_on_time_desc, t.unit_days)}
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
