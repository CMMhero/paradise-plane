/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: tong sampah lintas project (dulu "TPA")
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Susunan baku daftar God Mode (sama dengan Audit log & Accounts): toolbar ala
 * tampilan work item (cari, Filters, Display), DataTable dengan kepala yang bisa
 * diurutkan, dan AlertModalCore untuk aksi yang tak bisa dibatalkan. Isi tong
 * sampah dimuat utuh lalu disaring di klien supaya pilihan filter (jenis,
 * penghapus) diturunkan dari isinya, bukan dari daftar tetap yang bisa basi.
 */

import { useMemo, useState } from "react";
import { Boxes, CalendarX2, Hourglass, RotateCcw, Trash2, UserX } from "lucide-react";
import useSWR from "swr";
// plane imports
import { Badge } from "@plane/propel/badge";
import { setToast, TOAST_TYPE } from "@plane/propel/toast";
import { InstanceTrashService, countTrashTypes, type TTrashItem, type TTrashType } from "@plane/services";
import { AlertModalCore, Loader } from "@plane/ui";
import { cn } from "@plane/utils";
// components
import {
  DataTable,
  ViewToolbar,
  applyConditions,
  applySearch,
  paginate,
  sortRows,
  useViewState,
  type TColumn,
  type TFilterField,
  type TViewState,
} from "@/components/common/data-view";
import { PageWrapper } from "@/components/common/page-wrapper";
import { Pagination, StateBox } from "@/components/common/paradise";
import { formatDateTime } from "@/components/common/paradise-styles";
import { IconAction, PersonCell } from "@/components/common/paradise-ui";
import { MenuTabs } from "@/components/common/section-tabs";
// local
import { godmodeStrings, useGodmodeStrings, type TGodmodeStrings } from "@/app/i18n/godmode";
// types
import type { Route } from "./+types/page";

const trashService = new InstanceTrashService();

const SKELETON_ROWS = ["s1", "s2", "s3", "s4", "s5", "s6"];

/** Sisa hari yang dianggap mendesak: angkanya diwarnai bahaya. */
const HARI_MENDESAK = 3;
const HARI_SEPEKAN = 7;

/** Kunci penghapus: email kalau ada, `none` untuk skrip / model yang tak dipantau. */
const kunciPenghapus = (item: TTrashItem): string => item.deleted_by?.email ?? "none";

const sisaHari = (item: TTrashItem): "urgent" | "week" | "later" =>
  item.days_left <= HARI_MENDESAK ? "urgent" : item.days_left <= HARI_SEPEKAN ? "week" : "later";

const petaJenis = (t: TGodmodeStrings["trash"]): Partial<Record<TTrashType, string>> => ({
  account: t.type_account,
  project: t.type_project,
  issue: t.type_issue,
  page: t.type_page,
  wiki_material: t.type_wiki_material,
  cycle: t.type_cycle,
  module: t.type_module,
  view: t.type_view,
  label: t.type_label,
  template: t.type_template,
  initiative: t.type_initiative,
});

const VIEW_BAWAAN: TViewState = {
  search: "",
  conditions: [],
  sort: { key: "deleted", dir: "desc" },
  hidden: [],
  perPage: 50,
};

const TrashPage = function TrashPage(_props: Route.ComponentProps) {
  const { s, fill } = useGodmodeStrings();
  const t = s.trash;
  const [sibuk, setSibuk] = useState<string | null>(null);
  const [akanDibuang, setAkanDibuang] = useState<TTrashItem | null>(null);

  const { data, isLoading, error, mutate } = useSWR("INSTANCE_TRASH", () => trashService.list(), {
    revalidateOnFocus: false,
  });
  const items = useMemo(() => data?.results ?? [], [data]);

  const typeLabel = petaJenis(t);
  const labelJenis = (type: TTrashType, fallback: string) => typeLabel[type] ?? fallback;

  const fields = useMemo<TFilterField<TTrashItem>[]>(() => {
    const penghapus = new Map<string, string>();
    for (const item of items) {
      if (item.deleted_by) penghapus.set(item.deleted_by.email, item.deleted_by.display_name || item.deleted_by.email);
    }
    return [
      {
        key: "type",
        label: t.col_type,
        icon: Boxes,
        kind: "select",
        options: countTrashTypes(items).map((j) => ({
          value: j.type,
          label: `${petaJenis(t)[j.type] ?? j.label} (${j.count})`,
        })),
        get: (item) => item.type,
      },
      {
        key: "deleted_by",
        label: t.col_deleted_by,
        icon: UserX,
        kind: "select",
        options: [
          ...[...penghapus].map(([email, nama]) => ({ value: email, label: `${nama} (${email})` })),
          { value: "none", label: t.nobody },
        ],
        get: kunciPenghapus,
      },
      { key: "deleted", label: t.col_deleted, icon: CalendarX2, kind: "date", get: (item) => item.deleted_at },
      {
        key: "expires",
        label: t.filter_expires,
        icon: Hourglass,
        kind: "select",
        options: [
          { value: "urgent", label: t.expires_urgent },
          { value: "week", label: t.expires_week },
          { value: "later", label: t.expires_later },
        ],
        get: sisaHari,
      },
    ];
  }, [items, t]);

  const view = useViewState("trash", VIEW_BAWAAN, fields);

  const toastError = (err: unknown, fallback: string) => {
    const message = (err as { error?: string })?.error ?? fallback;
    setToast({ type: TOAST_TYPE.ERROR, title: s.common.failed, message });
  };

  const handlePulihkan = async (item: TTrashItem) => {
    setSibuk(item.id);
    try {
      const hasil = await trashService.restore(item.type, item.id);
      await mutate();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t.restored,
        message:
          item.type === "account"
            ? fill(t.account_restored_message, { name: item.name })
            : fill(t.restored_message, {
                name: item.name,
                n: Math.max((hasil?.restored_count ?? 1) - 1, 0),
              }),
      });
    } catch (err) {
      toastError(err, t.restore_failed);
    } finally {
      setSibuk(null);
    }
  };

  const handleBuang = async () => {
    const item = akanDibuang;
    if (!item) return;
    setSibuk(item.id);
    try {
      await trashService.purge(item.type, item.id);
      await mutate();
      setAkanDibuang(null);
      setToast({ type: TOAST_TYPE.SUCCESS, title: t.purged, message: fill(t.purged_message, { name: item.name }) });
    } catch (err) {
      toastError(err, t.purge_failed);
    } finally {
      setSibuk(null);
    }
  };

  const columns: TColumn<TTrashItem>[] = [
    {
      key: "item",
      label: t.col_item,
      locked: true,
      className: "max-w-0",
      sortValue: (item) => item.name.toLowerCase(),
      render: (item) => (
        <span className="block truncate font-medium text-primary" title={item.name}>
          {item.name}
        </span>
      ),
    },
    {
      key: "type",
      label: t.col_type,
      headClassName: "w-32",
      sortValue: (item) => labelJenis(item.type, item.type_label),
      render: (item) => (
        <Badge variant="neutral" size="sm">
          {labelJenis(item.type, item.type_label)}
        </Badge>
      ),
    },
    {
      key: "deleted_by",
      label: t.col_deleted_by,
      headClassName: "w-56",
      sortValue: (item) => item.deleted_by?.display_name || item.deleted_by?.email,
      render: (item) =>
        item.deleted_by ? (
          <PersonCell
            userId={item.deleted_by.id}
            name={item.deleted_by.display_name}
            email={item.deleted_by.email}
            size="sm"
          />
        ) : (
          <span className="text-placeholder">—</span>
        ),
    },
    {
      key: "deleted",
      label: t.col_deleted,
      headClassName: "w-40",
      className: "whitespace-nowrap text-secondary",
      sortValue: (item) => new Date(item.deleted_at).getTime(),
      render: (item) => formatDateTime(item.deleted_at),
    },
    {
      key: "expires",
      label: t.col_expires,
      headClassName: "w-28",
      sortValue: (item) => item.days_left,
      render: (item) => (
        <span
          className={cn("whitespace-nowrap text-secondary", {
            "font-medium text-danger-primary": item.days_left <= HARI_MENDESAK,
          })}
        >
          {fill(t.days_left, { n: item.days_left })}
        </span>
      ),
    },
    {
      key: "actions",
      label: t.restore,
      locked: true,
      srOnlyLabel: true,
      headClassName: "w-20",
      render: (item) => (
        <div className="flex items-center justify-end gap-1">
          <IconAction
            label={t.restore}
            icon={RotateCcw}
            disabled={sibuk === item.id}
            onClick={() => void handlePulihkan(item)}
          />
          <IconAction
            label={t.purge}
            icon={Trash2}
            variant="error-outline"
            disabled={sibuk === item.id}
            onClick={() => setAkanDibuang(item)}
          />
        </div>
      ),
    },
  ];

  const teksCari = (item: TTrashItem) =>
    `${item.name} ${labelJenis(item.type, item.type_label)} ${item.deleted_by?.display_name ?? ""} ${item.deleted_by?.email ?? ""}`;
  const tersaring = sortRows(
    applyConditions(applySearch(items, view.search, teksCari), fields, view.conditions),
    view.sort,
    columns.find((c) => c.key === view.sort.key)?.sortValue
  );
  const halaman = paginate(tersaring, view.page, view.perPage);

  const kept = data?.retention_days ? fill(t.kept, { days: data.retention_days }) : "";
  const teksKonfirmasi = akanDibuang?.type === "account" ? t.account_purge_confirm : t.purge_confirm;

  return (
    <PageWrapper header={{ title: s.settings.tabs.logs_trash.title, description: fill(t.description, { kept }) }}>
      <MenuTabs menu="logs" />
      <div className="space-y-3">
        <ViewToolbar
          view={view}
          fields={fields}
          searchPlaceholder={t.search_placeholder}
          sortOptions={columns.filter((c) => c.sortValue).map((c) => ({ key: c.key, label: c.label }))}
          columns={columns.filter((c) => !c.locked).map((c) => ({ key: c.key, label: c.label }))}
          summary={
            data &&
            (tersaring.length === items.length
              ? fill(t.count, { n: items.length })
              : fill(t.count_filtered, { n: tersaring.length, total: items.length }))
          }
        />

        {isLoading ? (
          <Loader className="space-y-2">
            {SKELETON_ROWS.map((k) => (
              <Loader.Item key={k} height="52px" />
            ))}
          </Loader>
        ) : error ? (
          <StateBox tone="danger">{t.load_failed}</StateBox>
        ) : tersaring.length === 0 ? (
          <StateBox>{items.length === 0 ? t.empty : t.no_results}</StateBox>
        ) : (
          <DataTable
            rows={halaman.rows}
            columns={columns}
            hidden={view.hidden}
            sort={view.sort}
            onSort={view.setSort}
            rowKey={(item) => `${item.type}-${item.id}`}
            minWidth={820}
          />
        )}

        {tersaring.length > view.perPage && (
          <Pagination
            summary={fill(s.members.page_summary, { page: halaman.page, total: halaman.totalPages })}
            page={halaman.page}
            totalPages={halaman.totalPages}
            onChange={view.setPage}
            prevLabel={s.common.prev_page}
            nextLabel={s.common.next_page}
          />
        )}
      </div>

      {/* Satu-satunya aksi tak terbalikkan di halaman ini, konfirmasi wajib. */}
      <AlertModalCore
        isOpen={akanDibuang !== null}
        handleClose={() => sibuk === null && setAkanDibuang(null)}
        handleSubmit={() => void handleBuang()}
        isSubmitting={akanDibuang !== null && sibuk === akanDibuang.id}
        title={t.purge_title}
        content={<span className="whitespace-pre-line">{fill(teksKonfirmasi, { name: akanDibuang?.name ?? "" })}</span>}
        primaryButtonText={{ default: t.purge, loading: t.purging }}
        secondaryButtonText={s.common.cancel}
      />
    </PageWrapper>
  );
};

export const meta: Route.MetaFunction = () => [
  { title: `${godmodeStrings.settings.tabs.logs_trash.title} - God Mode` },
];

export default TrashPage;
