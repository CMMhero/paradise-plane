/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Kustomisasi Paradise Task Tracker: Trashbin per project
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useEffect, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "react-router";
import { RotateCcw, Trash2 } from "lucide-react";
// plane imports
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { ProjectTrashService, type TTrashItem, type TTrashType } from "@plane/services";
import { Loader } from "@plane/ui";
// components
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { PageHead } from "@/components/core/page-title";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";

const trashService = new ProjectTrashService();

const SKELETON_ROWS = ["s1", "s2", "s3", "s4", "s5"];

// `label` adalah KUNCI i18n, diterjemahkan saat dirender.
const JENIS: { value: TTrashType | ""; label: string }[] = [
  { value: "", label: "trash_ui.all_types" },
  { value: "issue", label: "trash_ui.type_issue" },
  { value: "page", label: "trash_ui.type_page" },
  { value: "cycle", label: "trash_ui.type_cycle" },
  { value: "module", label: "trash_ui.type_module" },
];

const toastError = (err: unknown, fallback: string, t: (key: string) => string) => {
  const message = (err as { error?: string })?.error ?? fallback;
  setToast({ type: TOAST_TYPE.ERROR, title: t("trash_ui.failed"), message });
};

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
  const [items, setItems] = useState<TTrashItem[]>([]);
  const [retensi, setRetensi] = useState<number | null>(null);
  const [jenis, setJenis] = useState<TTrashType | "">("");
  const [isLoading, setIsLoading] = useState(true);
  const [sibuk, setSibuk] = useState<string | null>(null);

  const canAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT);
  const pageTitle = currentProjectDetails?.name
    ? t("trash_ui.page_title", { name: currentProjectDetails.name })
    : undefined;

  const muat = useCallback(async () => {
    if (!workspaceSlug || !projectId) return;
    try {
      const data = await trashService.list(workspaceSlug.toString(), projectId.toString(), jenis || undefined);
      setItems(data.results);
      setRetensi(data.retention_days);
    } catch (err) {
      toastError(err, t("trash_ui.load_failed"), t);
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug, projectId, jenis, t]);

  useEffect(() => {
    void muat();
  }, [muat]);

  const handlePulihkan = async (item: TTrashItem) => {
    if (!workspaceSlug || !projectId) return;
    setSibuk(item.id);
    try {
      const hasil = await trashService.restore(workspaceSlug.toString(), projectId.toString(), item.type, item.id);
      await muat();
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
      toastError(err, t("trash_ui.restore_failed"), t);
    } finally {
      setSibuk(null);
    }
  };

  const handleBuang = async (item: TTrashItem) => {
    if (!workspaceSlug || !projectId) return;
    // Konfirmasi wajib: ini satu-satunya aksi di halaman ini yang tidak bisa
    // dibatalkan, dan tombolnya bersebelahan dengan "Pulihkan".
    const yakin = window.confirm(t("trash_ui.confirm_purge", { name: item.name }));
    if (!yakin) return;
    setSibuk(item.id);
    try {
      await trashService.purge(workspaceSlug.toString(), projectId.toString(), item.type, item.id);
      await muat();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("trash_ui.purged_title"),
        message: t("trash_ui.purged_message", { name: item.name }),
      });
    } catch (err) {
      toastError(err, t("trash_ui.purge_failed"), t);
    } finally {
      setSibuk(null);
    }
  };

  if (workspaceUserInfo && !canAdmin) return <NotAuthorizedView section="settings" isProjectView />;

  return (
    <SettingsContentWrapper>
      <PageHead title={pageTitle} />
      <div className="flex items-start justify-between gap-4 border-b border-subtle pb-4">
        <div>
          <h3 className="text-xl font-medium">{t("trash_ui.title")}</h3>
          <p className="text-sm mt-1 text-secondary">
            {retensi ? t("trash_ui.description_with_days", { days: retensi }) : t("trash_ui.description")}
          </p>
        </div>
        <select
          value={jenis}
          onChange={(e) => setJenis(e.target.value as TTrashType | "")}
          className="text-sm focus:border-accent-primary rounded border border-subtle bg-layer-1 px-2 py-1.5 outline-none"
        >
          {JENIS.map((j) => (
            <option key={j.value} value={j.value}>
              {j.label}
            </option>
          ))}
        </select>
      </div>

      <div className="py-4">
        {isLoading ? (
          <Loader className="space-y-2">
            {SKELETON_ROWS.map((k) => (
              <Loader.Item key={k} height="48px" />
            ))}
          </Loader>
        ) : items.length === 0 ? (
          <p className="text-sm py-10 text-center text-secondary">{t("trash_ui.empty")}</p>
        ) : (
          <div className="divide-y divide-subtle rounded border border-subtle">
            {items.map((item) => (
              <div key={`${item.type}-${item.id}`} className="flex items-center justify-between gap-4 px-4 py-3">
                <div className="min-w-0">
                  <p className="text-sm truncate font-medium text-primary">{item.name}</p>
                  <p className="text-xs mt-0.5 text-secondary">
                    {item.type_label} ·{" "}
                    {t("trash_ui.deleted_at", { time: formatWaktu(item.deleted_at, currentLocale) })}
                    {item.deleted_by
                      ? ` ${t("trash_ui.deleted_by", { name: item.deleted_by.display_name || item.deleted_by.email })}`
                      : ""}
                    {" · "}
                    <span className={item.days_left <= 3 ? "text-red-600 font-medium" : ""}>
                      {t("trash_ui.days_left", { count: item.days_left })}
                    </span>
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={sibuk === item.id}
                    onClick={() => handlePulihkan(item)}
                  >
                    <RotateCcw className="size-3.5" /> {t("trash_ui.restore")}
                  </Button>
                  <Button
                    variant="error-outline"
                    size="sm"
                    disabled={sibuk === item.id}
                    onClick={() => handleBuang(item)}
                  >
                    <Trash2 className="size-3.5" /> {t("trash_ui.purge")}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </SettingsContentWrapper>
  );
}

export default observer(TrashSettingsPage);
