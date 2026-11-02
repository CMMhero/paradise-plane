/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tabel riwayat masuk/keluar
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Toolbar ala tampilan work item (cari, Filters, Display). Filter, cari, dan
 * urutan jalan di server (`/api/instances/login-history/`), di dalam jendela
 * rentang hari yang dipilih di atas halaman, supaya tabel dan kartu di atasnya
 * bercerita tentang periode yang sama.
 */

import { useMemo } from "react";
import { CalendarDays, LogIn, MonitorSmartphone, Network, PanelsTopLeft, User } from "lucide-react";
import useSWR from "swr";
// plane imports
import {
  InstanceActivityService,
  InstanceMemberService,
  type TLoginEvent,
  type TLoginHistoryFilter,
  type TLoginHistorySort,
} from "@plane/services";
import { Loader } from "@plane/ui";
// components
import {
  DataTable,
  ViewToolbar,
  toServerParams,
  useDebounced,
  useViewState,
  type TColumn,
  type TFilterField,
  type TViewState,
} from "@/components/common/data-view";
import { Pagination, Section, StateBox } from "@/components/common/paradise";
import { formatDateTime } from "@/components/common/paradise-styles";
import { PersonCell } from "@/components/common/paradise-ui";
// local
import { useGodmodeStrings } from "@/app/i18n/godmode";
import { SKELETON_ROWS } from "./constants";

const activityService = new InstanceActivityService();
const memberService = new InstanceMemberService();

const VIEW_BAWAAN: TViewState = {
  search: "",
  conditions: [],
  sort: { key: "time", dir: "desc" },
  hidden: ["user_agent"],
  perPage: 25,
};

/** "email" -> "Email", "" -> label kosong. Nilai mentah backend, tidak diterjemahkan. */
const rapikan = (v: string, kosong: string): string =>
  v ? v.charAt(0).toUpperCase() + v.slice(1).replace(/[-_]/g, " ") : kosong;

export function RiwayatMasuk({ hari }: { hari: number }) {
  const { s, fill } = useGodmodeStrings();
  const t = s.activity;

  const { data: akun } = useSWR("INSTANCE_MEMBERS_ALL", () => memberService.listAll(), { revalidateOnFocus: false });
  // Opsi sumber & metode datang dari respons riwayat itu sendiri (nilai yang
  // memang ada di jendela ini), bukan daftar tetap yang bisa basi.
  const { data: pilihan } = useSWR(
    ["INSTANCE_LOGIN_HISTORY_OPTIONS", hari],
    () => activityService.history({ hari, per_page: 1 }).then((r) => r.pilihan),
    { revalidateOnFocus: false }
  );

  const fields = useMemo<TFilterField<TLoginEvent>[]>(
    () => [
      {
        key: "person",
        label: t.col_person,
        icon: User,
        kind: "select",
        param: "user_id",
        options: (akun ?? []).map((a) => ({
          value: a.id,
          label: a.display_name ? `${a.display_name} (${a.email})` : a.email,
        })),
      },
      {
        key: "event",
        label: t.col_event,
        icon: LogIn,
        kind: "select",
        param: "jenis",
        options: [
          { value: "LOGIN", label: t.event_login },
          { value: "LOGOUT", label: t.event_logout },
        ],
      },
      {
        key: "source",
        label: t.col_source,
        icon: PanelsTopLeft,
        kind: "select",
        param: "permukaan",
        options: (pilihan?.permukaan ?? []).map((v) => ({ value: v || "none", label: rapikan(v, t.unknown) })),
      },
      {
        key: "method",
        label: t.col_method,
        icon: MonitorSmartphone,
        kind: "select",
        param: "medium",
        options: (pilihan?.medium ?? []).map((v) => ({ value: v || "none", label: rapikan(v, t.unknown) })),
      },
      { key: "date", label: t.filter_date, icon: CalendarDays, kind: "date", param: "date" },
      { key: "ip", label: t.filter_ip, icon: Network, kind: "text", param: "ip", operators: ["contains"] },
    ],
    [akun, pilihan, t]
  );

  const view = useViewState("login-history", VIEW_BAWAAN, fields);
  const cari = useDebounced(view.search);
  const filter: TLoginHistoryFilter = {
    ...toServerParams(fields, view.conditions),
    search: cari.trim() || undefined,
    sort: `${view.sort.dir === "desc" ? "-" : ""}${view.sort.key}` as TLoginHistorySort,
    hari,
    page: view.page,
    per_page: view.perPage,
  };

  const { data, isLoading, error } = useSWR(["INSTANCE_LOGIN_HISTORY", filter], () => activityService.history(filter), {
    revalidateOnFocus: false,
    keepPreviousData: true,
  });

  const columns: TColumn<TLoginEvent>[] = [
    {
      key: "time",
      label: t.col_time,
      sortable: true,
      locked: true,
      className: "whitespace-nowrap text-secondary",
      render: (e) => formatDateTime(e.terjadi_pada),
    },
    {
      key: "person",
      label: t.col_person,
      sortable: true,
      render: (e) => <PersonCell name={e.display_name || e.email} email={e.email} size="sm" />,
    },
    {
      key: "event",
      label: t.col_event,
      sortable: true,
      render: (e) => (
        <span className={e.jenis === "LOGIN" ? "text-success-primary" : "text-secondary"}>
          {e.jenis === "LOGIN" ? t.event_login : t.event_logout}
        </span>
      ),
    },
    {
      key: "source",
      label: t.col_source,
      sortable: true,
      className: "text-secondary",
      render: (e) => rapikan(e.permukaan, "—"),
    },
    {
      key: "medium",
      label: t.col_method,
      sortable: true,
      className: "text-secondary",
      render: (e) => rapikan(e.medium, "—"),
    },
    {
      key: "ip",
      label: t.col_ip,
      sortable: true,
      className: "font-code text-11 text-tertiary",
      render: (e) => e.ip || "—",
    },
    {
      key: "user_agent",
      label: t.col_user_agent,
      className: "max-w-[320px]",
      render: (e) => (
        <span className="block truncate text-11 text-tertiary" title={e.user_agent}>
          {e.user_agent || "—"}
        </span>
      ),
    },
  ];

  const halaman = data?.page ?? 1;
  const totalHalaman = Math.max(data?.total_pages ?? 1, 1);

  return (
    <Section title={t.history_title}>
      <ViewToolbar
        view={view}
        fields={fields}
        searchPlaceholder={t.search_placeholder}
        sortOptions={columns.filter((c) => c.sortable).map((c) => ({ key: c.key, label: c.label }))}
        columns={columns.filter((c) => !c.locked).map((c) => ({ key: c.key, label: c.label }))}
        summary={data && fill(t.history_filtered, { n: data.count })}
      />

      {isLoading && !data ? (
        <Loader className="space-y-2">
          {SKELETON_ROWS.map((k) => (
            <Loader.Item key={k} height="40px" />
          ))}
        </Loader>
      ) : error ? (
        <StateBox tone="danger">{t.load_failed}</StateBox>
      ) : !data?.results.length ? (
        <StateBox>{t.history_empty}</StateBox>
      ) : (
        <DataTable
          rows={data.results}
          columns={columns}
          hidden={view.hidden}
          sort={view.sort}
          onSort={view.setSort}
          rowKey={(e) => e.id}
        />
      )}

      {data && data.count > 0 && (
        <Pagination
          summary={fill(t.history_count, { n: data.count, page: halaman, total: totalHalaman })}
          page={halaman}
          totalPages={totalHalaman}
          onChange={view.setPage}
          prevLabel={s.common.prev_page}
          nextLabel={s.common.next_page}
        />
      )}
    </Section>
  );
}
