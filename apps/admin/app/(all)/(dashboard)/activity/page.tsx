/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: dashboard aktivitas
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { AlertTriangle } from "lucide-react";
import useSWR from "swr";
// plane imports
import { InstanceActivityService, type TRetensi } from "@plane/services";
import { CustomSelect, Loader } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
import { Callout, Section, StatCard, StateBox, Toolbar } from "@/components/common/paradise";
import { formatDateTime } from "@/components/common/paradise-styles";
import { LogsTabs } from "@/components/common/section-tabs";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { RENTANG, SKELETON_ROWS } from "./constants";
import { GrafikHarian } from "./grafik-harian";
import { RiwayatMasuk } from "./riwayat";
// types
import type { Route } from "./+types/page";

const activityService = new InstanceActivityService();

/** Peringatan retensi. Muncul jauh sebelum datanya hilang, bukan pada harinya. */
function PeringatanRetensi({ retensi }: { retensi: TRetensi }) {
  const { s, fill } = useGodmodeStrings();
  const t = s.activity;
  if (!retensi.perlu_peringatan) return null;
  return (
    <Callout
      icon={<AlertTriangle className="size-4" />}
      title={fill(t.retention_title, { n: retensi.akan_dibuang, days: retensi.ambang_peringatan_hari })}
    >
      {fill(t.retention_body, {
        days: retensi.retensi_hari,
        oldest: formatDateTime(retensi.tertua),
        overdue: retensi.sudah_lewat > 0 ? fill(t.retention_overdue, { n: retensi.sudah_lewat }) : "",
      })}
    </Callout>
  );
}

const ActivityPage = function ActivityPage(_props: Route.ComponentProps) {
  const { s, fill } = useGodmodeStrings();
  const t = s.activity;
  const [hari, setHari] = useState(30);

  const { data, isLoading, error } = useSWR(["INSTANCE_ACTIVITY", hari], () => activityService.summary(hari), {
    revalidateOnFocus: false,
    // Siapa yang sedang memakai berubah tiap menit, angka yang beku di layar
    // lebih menyesatkan daripada tidak ada angkanya sama sekali.
    refreshInterval: 60_000,
  });

  // Rentang riwayat ikut (RiwayatMasuk menerima hari), kalau tidak, tabel di
  // bawah bercerita tentang periode yang berbeda dari kartu di atasnya.
  const ubahRentang = (n: number) => setHari(n);

  const r = data?.ringkas;
  const retensiHari = data?.retensi?.retensi_hari ?? 90;
  // Rentang di atas retensi hanya menghasilkan grafik yang sebagian besar kosong.
  const pilihanRentang = [...RENTANG.filter((n) => n < retensiHari), retensiHari];
  const maksLogin = Math.max(...(data?.teraktif ?? []).map((x) => x.login), 1);

  return (
    <PageWrapper header={{ title: s.logs.title, description: fill(t.description, { days: retensiHari }) }}>
      <LogsTabs />
      <div className="space-y-8">
        {error ? <StateBox tone="danger">{t.load_failed}</StateBox> : null}
        {data?.retensi ? <PeringatanRetensi retensi={data.retensi} /> : null}

        <Toolbar>
          <span className="text-13 text-tertiary">{t.range}</span>
          <CustomSelect
            value={hari}
            onChange={(n: number) => ubahRentang(Number(n))}
            label={fill(t.range_days, { n: hari })}
            placement="bottom-start"
            input
          >
            {pilihanRentang.map((n) => (
              <CustomSelect.Option key={n} value={n}>
                {fill(t.range_days, { n })}
              </CustomSelect.Option>
            ))}
          </CustomSelect>
        </Toolbar>

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {isLoading || !r ? (
            SKELETON_ROWS.slice(0, 4).map((k) => <Loader.Item key={k} height="84px" />)
          ) : (
            <>
              <StatCard
                label={t.stat_in_use}
                value={r.sedang_memakai}
                hint={fill(t.stat_in_use_hint, { n: data.ambang_aktif_menit })}
              />
              <StatCard label={t.stat_signed_in} value={r.masih_login} hint={t.stat_signed_in_hint} />
              <StatCard
                label={t.stat_never}
                value={r.belum_pernah_login}
                hint={fill(t.stat_never_hint, { n: r.total_user })}
              />
              <StatCard
                label={t.stat_signins}
                value={r.total_login}
                hint={fill(t.stat_signins_hint, { people: r.user_yang_login, avg: r.rata_login_per_user })}
              />
            </>
          )}
        </div>

        <Section title={t.daily_title}>
          {isLoading || !data ? <Loader.Item height="200px" /> : <GrafikHarian harian={data.harian} />}
        </Section>

        <Section title={t.top_title} description={t.top_hint}>
          {isLoading || !data ? (
            <Loader.Item height="120px" />
          ) : (data.teraktif ?? []).length === 0 ? (
            <StateBox>{t.top_empty}</StateBox>
          ) : (
            <div className="space-y-1.5 rounded-card border border-subtle p-3">
              {data.teraktif.map((x) => (
                <div key={x.user_id} className="flex items-center gap-2">
                  <span className="w-56 shrink-0 truncate text-11 text-secondary">{x.email}</span>
                  {/* Batang + angka di ujungnya: panjangnya untuk membandingkan
                      sekilas, angkanya supaya tidak perlu menaksir dari panjang. */}
                  <span className="h-2 flex-1 overflow-hidden rounded-control bg-layer-1">
                    <span
                      className="block h-full rounded-control bg-accent-primary"
                      style={{ width: `${Math.max(2, (x.login / maksLogin) * 100)}%` }}
                    />
                  </span>
                  <span className="w-10 shrink-0 text-right text-11 text-placeholder">{x.login}×</span>
                </div>
              ))}
            </div>
          )}
        </Section>

        <RiwayatMasuk hari={hari} />
      </div>
    </PageWrapper>
  );
};

export const meta: Route.MetaFunction = () => [{ title: "Activity - God Mode" }];

export default ActivityPage;
