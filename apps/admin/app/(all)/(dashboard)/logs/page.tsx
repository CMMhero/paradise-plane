/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: halaman jejak audit
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Toolbar ala tampilan work item (cari, Filters, Display); filter, cari, dan
 * urutan dijalankan di SERVER karena jejak audit bisa ratusan ribu baris.
 * Saat diurutkan menurut waktu, baris dikelompokkan per hari. Klik baris
 * membuka tabel Sebelum/Sesudah dengan nama kolom yang bisa dibaca (format.ts).
 * Kolom teknis (timestamp, urutan) selalu tampil, diurutkan paling akhir.
 */

import { useMemo, useState } from "react";
import {
  Boxes,
  CalendarDays,
  ChevronRight,
  FilePen,
  FilePlus2,
  FileX2,
  ListTree,
  Network,
  User,
  Zap,
} from "lucide-react";
import useSWR from "swr";
// plane imports
import { Badge } from "@plane/propel/badge";
import { Tooltip } from "@plane/propel/tooltip";
import {
  AUDIT_SYSTEM_ACTOR,
  InstanceAuditLogService,
  InstanceMemberService,
  type TAuditLogEntry,
  type TAuditLogFilter,
  type TAuditLogModel,
  type TAuditLogSort,
} from "@plane/services";
import { Loader } from "@plane/ui";
import { cn } from "@plane/utils";
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
import { PageWrapper } from "@/components/common/page-wrapper";
import { Pagination, StateBox } from "@/components/common/paradise";
import { dayKey, formatDateTime, formatDayHeading, formatTime } from "@/components/common/paradise-styles";
import { PersonCell } from "@/components/common/paradise-ui";
import { MenuTabs } from "@/components/common/section-tabs";
// local
import { godmodeStrings, useGodmodeStrings, type TGodmodeStrings } from "@/app/i18n/godmode";
import {
  aksiAudit,
  barisPerubahan,
  kolomDikenal,
  nilaiAudit,
  objekAudit,
  type TAksiAudit,
  type TBarisPerubahan,
} from "./format";
// types
import type { Route } from "./+types/page";

const auditLogService = new InstanceAuditLogService();
const memberService = new InstanceMemberService();

/** Kunci tetap untuk baris skeleton, index sebagai key ditolak lint. */
const SKELETON_ROWS = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"];

const GAYA_AKSI: Record<TAksiAudit, { variant: "success" | "warning" | "danger" | "neutral"; icon: typeof FilePen }> = {
  create: { variant: "success", icon: FilePlus2 },
  update: { variant: "warning", icon: FilePen },
  delete: { variant: "danger", icon: FileX2 },
  other: { variant: "neutral", icon: FilePen },
};

const MODELS: TAuditLogModel[] = ["project", "projectmember", "workspacemember", "issue", "page"];

/** Kunci kolom -> kunci urut backend (`?sort=`). Kolom tanpa entri tidak bisa diurutkan. */
const URUT_SERVER: Record<string, string> = {
  time: "timestamp",
  actor: "actor",
  action: "action",
  model: "model",
  object: "object",
  ip: "ip",
};

const VIEW_BAWAAN: TViewState = {
  search: "",
  conditions: [],
  sort: { key: "time", dir: "desc" },
  hidden: [],
  perPage: 50,
};

type TAudit = TGodmodeStrings["audit"];

const ringkasPerubahan = (baris: TBarisPerubahan[], t: TAudit, fill: TFill): string => {
  const bermakna = baris.filter((b) => !b.teknis);
  if (bermakna.length === 0) return baris.length === 0 ? t.changes_none : fill(t.changes_many, { n: baris.length });
  if (bermakna.length === 1) return bermakna[0].label;
  const dua = bermakna
    .slice(0, 2)
    .map((b) => b.label)
    .join(", ");
  return bermakna.length > 2 ? `${dua} +${bermakna.length - 2}` : dua;
};

const labelModelDari = (t: TAudit): Record<TAuditLogModel, string> => ({
  project: t.model_project,
  projectmember: t.model_projectmember,
  workspacemember: t.model_workspacemember,
  issue: t.model_issue,
  page: t.model_page,
});

const labelAksiDari = (t: TAudit): Record<Exclude<TAksiAudit, "other">, string> => ({
  create: t.action_create,
  update: t.action_update,
  delete: t.action_delete,
});

type TFill = (template: string, vars: Record<string, string | number>) => string;

const LogsPage = function LogsPage(_props: Route.ComponentProps) {
  const { s, fill } = useGodmodeStrings();
  const t = s.audit;
  const [dibuka, setDibuka] = useState<number | null>(null);

  // Opsi filter aktor: semua akun, plus entri tanpa aktor (skrip server).
  const { data: akun } = useSWR("INSTANCE_MEMBERS_ALL", () => memberService.listAll(), { revalidateOnFocus: false });

  const labelModel = labelModelDari(t);
  const labelAksi = labelAksiDari(t);

  const fields = useMemo<TFilterField<TAuditLogEntry>[]>(
    () => [
      {
        key: "actor",
        label: t.col_actor,
        icon: User,
        kind: "select",
        param: "actor",
        options: [
          { value: AUDIT_SYSTEM_ACTOR, label: t.system_actor },
          ...(akun ?? []).map((a) => ({
            value: a.id,
            label: a.display_name ? `${a.display_name} (${a.email})` : a.email,
          })),
        ],
      },
      {
        key: "action",
        label: t.col_action,
        icon: Zap,
        kind: "select",
        param: "action",
        options: (["create", "update", "delete"] as const).map((a) => ({ value: a, label: labelAksiDari(t)[a] })),
      },
      {
        key: "model",
        label: t.filter_object_type,
        icon: Boxes,
        kind: "select",
        param: "model",
        options: MODELS.map((m) => ({ value: m, label: labelModelDari(t)[m] })),
      },
      { key: "field", label: t.filter_field, icon: ListTree, kind: "select", param: "field", options: kolomDikenal() },
      { key: "date", label: t.filter_date, icon: CalendarDays, kind: "date", param: "date" },
      { key: "ip", label: t.col_ip, icon: Network, kind: "text", param: "ip", operators: ["contains"] },
    ],
    [akun, t]
  );

  const view = useViewState("audit", VIEW_BAWAAN, fields);
  const cari = useDebounced(view.search);
  const urut = URUT_SERVER[view.sort.key] ?? "timestamp";
  const filter: TAuditLogFilter = {
    ...toServerParams(fields, view.conditions),
    search: cari.trim() || undefined,
    sort: `${view.sort.dir === "desc" ? "-" : ""}${urut}` as TAuditLogSort,
    page: view.page,
    per_page: view.perPage,
  };

  const { data, isLoading, error } = useSWR(["INSTANCE_AUDIT_LOGS", filter], () => auditLogService.list(filter), {
    revalidateOnFocus: false,
    keepPreviousData: true,
  });

  const namaModel = (m: TAuditLogModel | null) => (m ? labelModel[m] : "—");
  const namaAksi = (e: TAuditLogEntry) => {
    const a = aksiAudit(e.action);
    return a === "other" ? e.action : labelAksi[a];
  };

  const columns: TColumn<TAuditLogEntry>[] = [
    {
      key: "time",
      label: t.col_time,
      sortable: true,
      locked: true,
      headClassName: "w-24",
      className: "whitespace-nowrap",
      render: (e) => (
        <Tooltip tooltipContent={formatDateTime(e.timestamp)}>
          <span className="flex items-center gap-1.5 text-secondary">
            <ChevronRight
              className={cn("size-3.5 shrink-0 text-placeholder transition-transform", {
                "rotate-90": dibuka === e.id,
              })}
              aria-hidden
            />
            {view.sort.key === "time" ? formatTime(e.timestamp) : formatDateTime(e.timestamp)}
          </span>
        </Tooltip>
      ),
    },
    {
      key: "actor",
      label: t.col_actor,
      sortable: true,
      headClassName: "w-56",
      render: (e) =>
        e.actor ? (
          <PersonCell
            userId={e.actor.id}
            name={e.actor.display_name || e.actor.email}
            email={e.actor.email}
            size="sm"
          />
        ) : (
          // Entri tanpa aktor datang dari skrip shell, di situ memang tidak
          // ada request, jadi bukan celah audit.
          <Tooltip tooltipContent={t.system_actor_hint}>
            <span className="text-tertiary italic">{t.system_actor}</span>
          </Tooltip>
        ),
    },
    {
      key: "action",
      label: t.col_action,
      sortable: true,
      headClassName: "w-28",
      render: (e) => {
        const gaya = GAYA_AKSI[aksiAudit(e.action)];
        const Ikon = gaya.icon;
        return (
          <Badge variant={gaya.variant} prependIcon={<Ikon />}>
            {namaAksi(e)}
          </Badge>
        );
      },
    },
    {
      key: "model",
      label: t.filter_object_type,
      sortable: true,
      headClassName: "w-36",
      render: (e) => <Badge variant="neutral">{namaModel(e.model)}</Badge>,
    },
    {
      key: "object",
      label: t.col_object,
      sortable: true,
      render: (e) => {
        const objek = objekAudit(e.model, e.object_repr);
        return (
          <span className="flex min-w-0 items-baseline gap-1.5" title={e.object_repr}>
            <span className="truncate font-medium text-primary">{objek.utama}</span>
            {objek.konteks && (
              <span className="shrink-0 truncate text-11 text-tertiary">
                {fill(objek.jenisKonteks === "oleh" ? t.object_by : t.object_in, { x: objek.konteks })}
              </span>
            )}
          </span>
        );
      },
    },
    {
      key: "changes",
      label: t.col_changes,
      headClassName: "w-44",
      render: (e) => {
        const baris = barisPerubahan(e.changes);
        return (
          <span
            className="line-clamp-1 text-secondary"
            title={baris
              .filter((b) => !b.teknis)
              .map((b) => b.label)
              .join(", ")}
          >
            {ringkasPerubahan(baris, t, fill)}
          </span>
        );
      },
    },
    {
      key: "ip",
      label: t.col_ip,
      sortable: true,
      headClassName: "w-32",
      className: "font-code text-11 whitespace-nowrap text-tertiary",
      render: (e) => e.remote_addr ?? "—",
    },
  ];

  const halaman = data?.page ?? 1;
  const totalHalaman = data?.total_pages ?? 1;

  return (
    <PageWrapper header={{ title: s.settings.tabs.logs_audit.title, description: t.description }}>
      <MenuTabs menu="logs" />
      <div className="space-y-3">
        <ViewToolbar
          view={view}
          fields={fields}
          searchPlaceholder={t.search_placeholder}
          sortOptions={columns.filter((c) => c.sortable).map((c) => ({ key: c.key, label: c.label }))}
          columns={columns.filter((c) => !c.locked).map((c) => ({ key: c.key, label: c.label }))}
          summary={data && fill(t.count_short, { n: data.count })}
        />

        {isLoading && !data ? (
          <Loader className="space-y-2">
            {SKELETON_ROWS.map((k) => (
              <Loader.Item key={k} height="48px" />
            ))}
          </Loader>
        ) : error ? (
          <StateBox tone="danger">{t.load_failed}</StateBox>
        ) : !data?.results.length ? (
          <StateBox>{t.empty}</StateBox>
        ) : (
          <DataTable
            rows={data.results}
            columns={columns}
            hidden={view.hidden}
            sort={view.sort}
            onSort={(sort) => {
              setDibuka(null);
              view.setSort(sort);
            }}
            rowKey={(e) => String(e.id)}
            onRowClick={(e) => setDibuka(dibuka === e.id ? null : e.id)}
            renderExpanded={(e) =>
              dibuka === e.id ? <DetailPerubahan entri={e} baris={barisPerubahan(e.changes)} t={t} /> : null
            }
            // Judul per hari hanya bermakna saat urutannya memang menurut waktu.
            groupBy={
              view.sort.key === "time"
                ? (e) => ({ key: dayKey(e.timestamp), label: formatDayHeading(e.timestamp) })
                : undefined
            }
            minWidth={980}
          />
        )}

        {data && data.count > 0 && (
          <Pagination
            summary={fill(t.count, { n: data.count, page: halaman, total: totalHalaman })}
            page={halaman}
            totalPages={totalHalaman}
            onChange={(page) => {
              setDibuka(null);
              view.setPage(page);
            }}
            prevLabel={s.common.prev_page}
            nextLabel={s.common.next_page}
          />
        )}
      </div>
    </PageWrapper>
  );
};

function DetailPerubahan({ entri, baris, t }: { entri: TAuditLogEntry; baris: TBarisPerubahan[]; t: TAudit }) {
  return (
    <div className="ml-5 space-y-2 rounded-card border border-subtle bg-surface-1 p-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-11 text-tertiary">
        <span>
          {t.exact_time}: <span className="text-secondary">{formatDateTime(entri.timestamp)}</span>
        </span>
        {entri.object_id && (
          <span>
            {t.object_id}: <span className="font-code text-secondary">{entri.object_id}</span>
          </span>
        )}
      </div>

      {baris.length === 0 ? (
        <p className="text-12 text-secondary">{t.no_changes}</p>
      ) : (
        <>
          <div className="overflow-hidden rounded-card border border-subtle">
            <table className="w-full table-fixed text-12">
              <thead className="bg-layer-1 text-tertiary">
                <tr>
                  <th className="w-44 px-3 py-1.5 text-left font-medium">{t.col_field}</th>
                  <th className="px-3 py-1.5 text-left font-medium">{t.col_before}</th>
                  <th className="px-3 py-1.5 text-left font-medium">{t.col_after}</th>
                </tr>
              </thead>
              <tbody>
                {baris.map((b) => (
                  <tr key={b.field} className="border-t border-subtle align-top">
                    <td className="px-3 py-2">
                      <div className="font-medium text-primary">{b.label}</div>
                      <div className="font-code text-10 text-placeholder">{b.field}</div>
                    </td>
                    <td className="px-3 py-2">
                      <Nilai field={b.field} mentah={b.lama} t={t} sisi="lama" />
                    </td>
                    <td className="px-3 py-2">
                      <Nilai field={b.field} mentah={b.baru} t={t} sisi="baru" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function Nilai({ field, mentah, t, sisi }: { field: string; mentah: unknown; t: TAudit; sisi: "lama" | "baru" }) {
  const v = nilaiAudit(field, mentah, t.yes, t.no);
  if (v.jenis === "kosong") return <span className="text-placeholder italic">{t.empty_value}</span>;
  if (v.jenis === "id")
    return (
      <span className="font-code text-11 text-secondary" title={v.teks}>
        {v.pendek}…
      </span>
    );
  return (
    <span
      className={cn("line-clamp-4 break-words whitespace-pre-wrap", {
        "text-danger-primary": sisi === "lama",
        "text-success-primary": sisi === "baru",
      })}
      title={v.teks.length > 160 ? v.teks : undefined}
    >
      {v.teks}
    </span>
  );
}

export const meta: Route.MetaFunction = () => [
  { title: `${godmodeStrings.settings.tabs.logs_audit.title} - God Mode` },
];

export default LogsPage;
