/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: dashboard aktivitas
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo, useState } from "react";
import { AlertTriangle, ChevronLeft, ChevronRight } from "lucide-react";
import useSWR from "swr";
// plane imports
import { InstanceActivityService, type TLoginHistoryFilter, type TRetensi } from "@plane/services";
import { Loader } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
// local
import { RENTANG, SKELETON_ROWS, selectClass } from "./constants";
import { GrafikHarian } from "./grafik-harian";
// types
import type { Route } from "./+types/page";

const activityService = new InstanceActivityService();

function waktu(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("id-ID", {
    day: "2-digit",
    month: "short",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function Kartu({ label, nilai, catatan }: { label: string; nilai: number | string; catatan: string }) {
  return (
    <div className="rounded border border-subtle bg-layer-1 px-4 py-3">
      <div className="text-2xl font-semibold text-primary">{nilai}</div>
      <div className="mt-0.5 text-body-sm-regular text-secondary">{label}</div>
      <div className="mt-1 text-11 text-placeholder">{catatan}</div>
    </div>
  );
}

/** Peringatan retensi. Muncul jauh sebelum datanya hilang, bukan pada harinya. */
function PeringatanRetensi({ retensi }: { retensi: TRetensi }) {
  if (!retensi.perlu_peringatan) return null;
  return (
    <div className="border-amber-500/40 bg-amber-500/10 mx-4 flex items-start gap-3 rounded border p-3">
      <AlertTriangle className="text-amber-600 mt-0.5 size-4 shrink-0" />
      <div className="text-body-sm-regular">
        <div className="font-medium text-primary">
          {retensi.akan_dibuang} peristiwa akan dihapus dalam {retensi.ambang_peringatan_hari} hari
        </div>
        <div className="mt-0.5 text-secondary">
          Riwayat disimpan {retensi.retensi_hari} hari. Tertua {retensi.tertua ? waktu(retensi.tertua) : "—"}
          {retensi.sudah_lewat > 0 ? `, ${retensi.sudah_lewat} sudah lewat batas` : ""}. Ekspor dulu kalau masih
          diperlukan, sesudah dihapus tidak bisa dikembalikan. Email peringatan juga dikirim ke semua Super Admin.
        </div>
      </div>
    </div>
  );
}

const ActivityPage = function ActivityPage(_props: Route.ComponentProps) {
  const [hari, setHari] = useState(30);
  const [filter, setFilter] = useState<TLoginHistoryFilter>({ page: 1, per_page: 25, hari: 30 });

  const { data, isLoading, error } = useSWR(["INSTANCE_ACTIVITY", hari], () => activityService.summary(hari), {
    revalidateOnFocus: false,
    // Siapa yang sedang memakai berubah tiap menit, angka yang beku di layar
    // lebih menyesatkan daripada tidak ada angkanya sama sekali.
    refreshInterval: 60_000,
  });

  const { data: riwayat, isLoading: memuatRiwayat } = useSWR(
    ["INSTANCE_LOGIN_HISTORY", filter],
    () => activityService.history(filter),
    { revalidateOnFocus: false }
  );

  const ubahRentang = useMemo(
    () => (n: number) => {
      setHari(n);
      // Rentang riwayat ikut, kalau tidak, tabel di bawah bercerita tentang
      // periode yang berbeda dari kartu di atasnya.
      setFilter((f) => ({ ...f, hari: n, page: 1 }));
    },
    []
  );

  const r = data?.ringkas;
  const halaman = riwayat?.page ?? 1;
  const totalHalaman = riwayat?.total_pages ?? 1;
  const maksLogin = Math.max(...(data?.teraktif ?? []).map((t) => t.login), 1);

  return (
    <PageWrapper
      size="lg"
      header={{
        title: "Aktivitas",
        description:
          "Siapa sedang memakai, siapa masih login, dan seberapa sering orang keluar-masuk. Riwayat disimpan 3 bulan.",
      }}
    >
      {error ? (
        <div className="mx-4 rounded border border-subtle p-8 text-center text-body-sm-regular text-secondary">
          Gagal memuat aktivitas.
        </div>
      ) : null}

      {data?.retensi ? <PeringatanRetensi retensi={data.retensi} /> : null}

      <div className="mx-4 flex flex-wrap items-center gap-2">
        <span className="text-body-sm-regular text-secondary">Rentang</span>
        <select value={hari} onChange={(e) => ubahRentang(Number(e.target.value))} className={selectClass}>
          {RENTANG.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      <div className="mx-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {isLoading || !r ? (
          SKELETON_ROWS.slice(0, 4).map((k) => <Loader.Item key={k} height="84px" />)
        ) : (
          <>
            <Kartu
              label="Sedang memakai"
              nilai={r.sedang_memakai}
              catatan={`ada request <${data.ambang_aktif_menit} menit`}
            />
            <Kartu label="Masih login" nilai={r.masih_login} catatan="sesi hidup, belum tentu di layar" />
            <Kartu label="Belum pernah login" nilai={r.belum_pernah_login} catatan={`dari ${r.total_user} akun`} />
            <Kartu
              label="Login rentang ini"
              nilai={r.total_login}
              catatan={`${r.user_yang_login} orang · rata-rata ${r.rata_login_per_user}×`}
            />
          </>
        )}
      </div>

      <div className="mx-4">
        <h3 className="mb-2 text-body-sm-regular font-medium text-secondary">Login per hari</h3>
        {isLoading || !data ? <Loader.Item height="200px" /> : <GrafikHarian harian={data.harian} />}
      </div>

      <div className="mx-4">
        <h3 className="mb-2 text-body-sm-regular font-medium text-secondary">Paling sering keluar-masuk</h3>
        {isLoading || !data ? (
          <Loader.Item height="120px" />
        ) : (data.teraktif ?? []).length === 0 ? (
          <div className="rounded border border-subtle p-8 text-center text-body-sm-regular text-secondary">
            Belum ada yang login pada rentang ini.
          </div>
        ) : (
          <div className="space-y-1.5 rounded border border-subtle p-3">
            {data.teraktif.map((t) => (
              <div key={t.user_id} className="flex items-center gap-2">
                <span className="w-56 shrink-0 truncate text-11 text-secondary">{t.email}</span>
                {/* Batang + angka di ujungnya: panjangnya untuk membandingkan
                    sekilas, angkanya supaya tidak perlu menaksir dari panjang. */}
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-layer-1">
                  <span
                    className="block h-full rounded-full bg-accent-primary"
                    style={{ width: `${Math.max(2, (t.login / maksLogin) * 100)}%` }}
                  />
                </span>
                <span className="w-10 shrink-0 text-right text-11 text-placeholder">{t.login}×</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mx-4">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-body-sm-regular font-medium text-secondary">Riwayat keluar-masuk</h3>
          <select
            value={filter.jenis ?? ""}
            onChange={(e) =>
              setFilter((f) => ({
                ...f,
                jenis: (e.target.value || undefined) as TLoginHistoryFilter["jenis"],
                page: 1,
              }))
            }
            className={selectClass}
          >
            <option value="">Semua</option>
            <option value="LOGIN">Login saja</option>
            <option value="LOGOUT">Logout saja</option>
          </select>
        </div>

        {memuatRiwayat ? (
          <Loader className="space-y-2">
            {SKELETON_ROWS.map((k) => (
              <Loader.Item key={k} height="40px" />
            ))}
          </Loader>
        ) : !riwayat?.results.length ? (
          <div className="rounded border border-subtle p-8 text-center text-body-sm-regular text-secondary">
            Tidak ada peristiwa pada rentang ini.
          </div>
        ) : (
          <div className="overflow-x-auto rounded border border-subtle">
            <table className="w-full min-w-[720px] text-body-sm-regular">
              <thead className="bg-layer-1 text-secondary">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Waktu</th>
                  <th className="px-3 py-2 text-left font-medium">Orang</th>
                  <th className="px-3 py-2 text-left font-medium">Peristiwa</th>
                  <th className="px-3 py-2 text-left font-medium">Dari</th>
                  <th className="px-3 py-2 text-left font-medium">IP</th>
                </tr>
              </thead>
              <tbody>
                {riwayat.results.map((e) => (
                  <tr key={e.id} className="border-t border-subtle">
                    <td className="px-3 py-2 whitespace-nowrap text-secondary">{waktu(e.terjadi_pada)}</td>
                    <td className="px-3 py-2">
                      <div className="text-primary">{e.display_name || "—"}</div>
                      <div className="text-11 text-placeholder">{e.email}</div>
                    </td>
                    <td className="px-3 py-2">
                      <span className={e.jenis === "LOGIN" ? "text-green-600" : "text-secondary"}>
                        {e.jenis === "LOGIN" ? "Masuk" : "Keluar"}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-secondary">{e.permukaan || "—"}</td>
                    <td className="px-3 py-2 text-secondary">{e.ip || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-2 flex items-center justify-between text-body-sm-regular text-secondary">
          <span>
            {riwayat?.count ?? 0} peristiwa · halaman {halaman} dari {totalHalaman}
          </span>
          <div className="flex gap-1">
            <button
              type="button"
              disabled={halaman <= 1}
              onClick={() => setFilter((f) => ({ ...f, page: halaman - 1 }))}
              className="rounded border border-subtle p-1 disabled:opacity-40"
              aria-label="Halaman sebelumnya"
            >
              <ChevronLeft className="size-4" />
            </button>
            <button
              type="button"
              disabled={halaman >= totalHalaman}
              onClick={() => setFilter((f) => ({ ...f, page: halaman + 1 }))}
              className="rounded border border-subtle p-1 disabled:opacity-40"
              aria-label="Halaman berikutnya"
            >
              <ChevronRight className="size-4" />
            </button>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
};

export default ActivityPage;
