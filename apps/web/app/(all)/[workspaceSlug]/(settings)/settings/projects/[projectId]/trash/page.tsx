/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Trashbin per project
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 *
 * Susunannya sengaja sama dengan Logs > Trash di God Mode: toolbar (cari, jenis,
 * jumlah), tabel, aksi ikon, dan modal konfirmasi. Yang berbeda hanya cakupan
 * (satu project) dan bahasanya (i18n aplikasi, God Mode English-only).
 */

import { useMemo, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
import useSWR from "swr";
import { RotateCcw, Search, Trash2 } from "lucide-react";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Avatar } from "@plane/propel/avatar";
import { Badge } from "@plane/propel/badge";
import { IconButton } from "@plane/propel/icon-button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Tooltip } from "@plane/propel/tooltip";
import {
  ProjectTrashService,
  countTrashTypes,
  filterTrashItems,
  type TTrashItem,
  type TTrashType,
} from "@plane/services";
import { AlertModalCore, CustomSelect, Input, Loader } from "@plane/ui";
import { cn } from "@plane/utils";
// components
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { PageHead } from "@/components/core/page-title";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { SettingsHeading } from "@/components/settings/heading";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";

const trashService = new ProjectTrashService();

const SKELETON_ROWS = ["s1", "s2", "s3", "s4", "s5"];

/** Sisa hari yang dianggap mendesak: barisnya diwarnai bahaya. */
const HARI_MENDESAK = 3;

// Kelas yang sama dengan `tableClass` God Mode (apps/admin/components/common/paradise-styles.ts).
const TABEL = {
  wrap: "overflow-x-auto rounded-md border border-subtle",
  table: "w-full min-w-[720px] text-13",
  head: "bg-layer-1 text-tertiary",
  th: "px-3 py-2 text-left font-medium",
  row: "border-t border-subtle transition-colors hover:bg-layer-1-hover",
  td: "px-3 py-2",
};

/** Jenis yang punya kunci i18n sendiri; jenis lain memakai label dari server. */
const KUNCI_JENIS: Partial<Record<TTrashType, string>> = {
  issue: "trash_ui.type_issue",
  page: "trash_ui.type_page",
  cycle: "trash_ui.type_cycle",
  module: "trash_ui.type_module",
  view: "trash_ui.type_view",
  label: "trash_ui.type_label",
  wiki_material: "trash_ui.type_wiki_material",
};

/** Tombol ikon + tooltip, cermin `IconAction` God Mode. Label sekaligus nama aksesibelnya. */
function AksiIkon({
  label,
  icon,
  onClick,
  disabled,
  variant = "ghost",
}: {
  label: string;
  icon: React.FC<{ className?: string }>;
  onClick: () => void;
  disabled?: boolean;
  variant?: "ghost" | "error-outline";
}) {
  return (
    <Tooltip tooltipContent={label}>
      <IconButton variant={variant} size="lg" icon={icon} aria-label={label} disabled={disabled} onClick={onClick} />
    </Tooltip>
  );
}

function formatWaktu(iso: string, lokal: string) {
  return new Date(iso).toLocaleString(lokal, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function TrashSettingsPage() {
  const { t, currentLocale } = useTranslation();
  const { workspaceSlug, projectId } = useParams();
  // store
  const { currentProjectDetails } = useProject();
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();
  // state
  const [jenis, setJenis] = useState<TTrashType | "">("");
  const [cari, setCari] = useState("");
  const [sibuk, setSibuk] = useState<string | null>(null);
  const [akanDibuang, setAkanDibuang] = useState<TTrashItem | null>(null);

  const canAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT);
  const pageTitle = currentProjectDetails?.name
    ? t("trash_ui.page_title", { name: currentProjectDetails.name })
    : undefined;

  // Selalu ambil semua jenis; filter jenis & cari jalan di klien supaya pilihan
  // jenis diturunkan dari isi tong sampah, bukan dari daftar tetap.
  const { data, isLoading, error, mutate } = useSWR(
    workspaceSlug && projectId && canAdmin ? ["PROJECT_TRASH", workspaceSlug.toString(), projectId.toString()] : null,
    ([, slug, pid]) => trashService.list(slug, pid),
    { revalidateOnFocus: false }
  );

  const items = useMemo(() => data?.results ?? [], [data]);
  const jenisAda = useMemo(() => countTrashTypes(items), [items]);
  const tampil = useMemo(() => filterTrashItems(items, jenis, cari), [items, jenis, cari]);

  const labelJenis = (type: TTrashType, fallback: string) => {
    const kunci = KUNCI_JENIS[type];
    return kunci ? t(kunci) : fallback;
  };

  const toastError = (err: unknown, fallback: string) => {
    const message = (err as { error?: string })?.error ?? fallback;
    setToast({ type: TOAST_TYPE.ERROR, title: t("trash_ui.failed"), message });
  };

  const handlePulihkan = async (item: TTrashItem) => {
    if (!workspaceSlug || !projectId) return;
    setSibuk(item.id);
    try {
      const hasil = await trashService.restore(workspaceSlug.toString(), projectId.toString(), item.type, item.id);
      await mutate();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("trash_ui.restored_title"),
        // Sebutkan jumlahnya: memulihkan satu work item ikut mengembalikan
        // komentar & tautannya, dan angka itu satu-satunya tanda hal itu terjadi.
        message: t("trash_ui.restored_message", {
          name: item.name,
          count: Math.max((hasil?.restored_count ?? 1) - 1, 0),
        }),
      });
    } catch (err) {
      toastError(err, t("trash_ui.restore_failed"));
    } finally {
      setSibuk(null);
    }
  };

  const handleBuang = async () => {
    const item = akanDibuang;
    if (!item || !workspaceSlug || !projectId) return;
    setSibuk(item.id);
    try {
      await trashService.purge(workspaceSlug.toString(), projectId.toString(), item.type, item.id);
      await mutate();
      setAkanDibuang(null);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("trash_ui.purged_title"),
        message: t("trash_ui.purged_message", { name: item.name }),
      });
    } catch (err) {
      toastError(err, t("trash_ui.purge_failed"));
    } finally {
      setSibuk(null);
    }
  };

  if (workspaceUserInfo && !canAdmin) return <NotAuthorizedView section="settings" isProjectView />;

  const labelFilter = jenis
    ? labelJenis(jenis, jenisAda.find((j) => j.type === jenis)?.label ?? jenis)
    : t("trash_ui.all_types");

  return (
    <SettingsContentWrapper>
      <PageHead title={pageTitle} />
      <SettingsHeading
        title={t("trash_ui.title")}
        description={
          data?.retention_days
            ? t("trash_ui.description_with_days", { days: data.retention_days })
            : t("trash_ui.description")
        }
      />

      <div className="mt-6 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative min-w-[240px] flex-1">
              <Search className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-placeholder" />
              <Input
                type="text"
                value={cari}
                onChange={(e) => setCari(e.target.value)}
                placeholder={t("trash_ui.search_placeholder")}
                aria-label={t("trash_ui.search_placeholder")}
                className="w-full pl-8"
              />
            </div>
            <CustomSelect
              value={jenis}
              label={labelFilter}
              onChange={(v: TTrashType | "") => setJenis(v)}
              buttonClassName="rounded-md border-subtle bg-layer-2"
              input
            >
              <CustomSelect.Option value="">
                {t("trash_ui.all_types")} ({items.length})
              </CustomSelect.Option>
              {jenisAda.map((j) => (
                <CustomSelect.Option key={j.type} value={j.type}>
                  {labelJenis(j.type, j.label)} ({j.count})
                </CustomSelect.Option>
              ))}
            </CustomSelect>
          </div>
          {data && <span className="text-13 text-tertiary">{t("trash_ui.count", { count: tampil.length })}</span>}
        </div>

        {isLoading ? (
          <Loader className="space-y-2">
            {SKELETON_ROWS.map((k) => (
              <Loader.Item key={k} height="52px" />
            ))}
          </Loader>
        ) : error ? (
          <div className="rounded-md border border-danger-subtle bg-danger-subtle p-8 text-center text-13 text-danger-primary">
            {t("trash_ui.load_failed")}
          </div>
        ) : tampil.length === 0 ? (
          <div className="rounded-md border border-subtle p-8 text-center text-13 text-tertiary">
            {items.length === 0 ? t("trash_ui.empty") : t("trash_ui.no_results")}
          </div>
        ) : (
          <div className={TABEL.wrap}>
            <table className={TABEL.table}>
              <thead className={TABEL.head}>
                <tr>
                  <th className={TABEL.th}>{t("trash_ui.col_item")}</th>
                  <th className={`${TABEL.th} w-32`}>{t("trash_ui.col_type")}</th>
                  <th className={`${TABEL.th} w-48`}>{t("trash_ui.col_deleted_by")}</th>
                  <th className={`${TABEL.th} w-40`}>{t("trash_ui.col_deleted")}</th>
                  <th className={`${TABEL.th} w-32`}>{t("trash_ui.col_expires")}</th>
                  <th className={`${TABEL.th} w-20`}>
                    <span className="sr-only">{t("trash_ui.restore")}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {tampil.map((item) => {
                  const penghapus = item.deleted_by?.display_name || item.deleted_by?.email;
                  return (
                    <tr key={`${item.type}-${item.id}`} className={TABEL.row}>
                      <td className={`${TABEL.td} max-w-0`}>
                        <span className="block truncate font-medium text-primary" title={item.name}>
                          {item.name}
                        </span>
                      </td>
                      <td className={TABEL.td}>
                        <Badge variant="neutral" size="sm">
                          {labelJenis(item.type, item.type_label)}
                        </Badge>
                      </td>
                      <td className={TABEL.td}>
                        {penghapus ? (
                          <div className="flex min-w-0 items-center gap-2">
                            <Avatar name={penghapus} size="base" showTooltip={false} />
                            <span className="truncate text-secondary">{penghapus}</span>
                          </div>
                        ) : (
                          <span className="text-placeholder">—</span>
                        )}
                      </td>
                      <td className={`${TABEL.td} whitespace-nowrap text-secondary`}>
                        {formatWaktu(item.deleted_at, currentLocale)}
                      </td>
                      <td className={TABEL.td}>
                        <span
                          className={cn("whitespace-nowrap text-secondary", {
                            "font-medium text-danger-primary": item.days_left <= HARI_MENDESAK,
                          })}
                        >
                          {t("trash_ui.days_left", { count: item.days_left })}
                        </span>
                      </td>
                      <td className={TABEL.td}>
                        <div className="flex items-center justify-end gap-1">
                          <AksiIkon
                            label={t("trash_ui.restore")}
                            icon={RotateCcw}
                            disabled={sibuk === item.id}
                            onClick={() => void handlePulihkan(item)}
                          />
                          <AksiIkon
                            label={t("trash_ui.purge")}
                            icon={Trash2}
                            variant="error-outline"
                            disabled={sibuk === item.id}
                            onClick={() => setAkanDibuang(item)}
                          />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Satu-satunya aksi tak terbalikkan di halaman ini, konfirmasi wajib. */}
      <AlertModalCore
        isOpen={akanDibuang !== null}
        handleClose={() => sibuk === null && setAkanDibuang(null)}
        handleSubmit={() => void handleBuang()}
        isSubmitting={akanDibuang !== null && sibuk === akanDibuang.id}
        title={t("trash_ui.purge_title")}
        content={
          <span className="whitespace-pre-line">{t("trash_ui.confirm_purge", { name: akanDibuang?.name ?? "" })}</span>
        }
        primaryButtonText={{ default: t("trash_ui.purge"), loading: t("trash_ui.purging") }}
        secondaryButtonText={t("cancel")}
      />
    </SettingsContentWrapper>
  );
}

export default observer(TrashSettingsPage);
