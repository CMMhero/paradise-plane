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

const JENIS: { value: TTrashType | ""; label: string }[] = [
  { value: "", label: "Semua jenis" },
  { value: "issue", label: "Work item" },
  { value: "page", label: "Halaman" },
  { value: "cycle", label: "Cycle" },
  { value: "module", label: "Module" },
];

const toastError = (err: unknown, fallback: string) => {
  const message = (err as { error?: string })?.error ?? fallback;
  setToast({ type: TOAST_TYPE.ERROR, title: "Gagal", message });
};

function formatWaktu(iso: string) {
  return new Date(iso).toLocaleString("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function TrashSettingsPage() {
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
  const pageTitle = currentProjectDetails?.name ? `${currentProjectDetails.name} - Tong sampah` : undefined;

  const muat = useCallback(async () => {
    if (!workspaceSlug || !projectId) return;
    try {
      const data = await trashService.list(workspaceSlug.toString(), projectId.toString(), jenis || undefined);
      setItems(data.results);
      setRetensi(data.retention_days);
    } catch (err) {
      toastError(err, "Tidak bisa memuat isi tong sampah.");
    } finally {
      setIsLoading(false);
    }
  }, [workspaceSlug, projectId, jenis]);

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
        title: "Dipulihkan",
        // Sebutkan jumlahnya: memulihkan satu work item ikut mengembalikan
        // komentar & tautannya, dan angka itu satu-satunya tanda hal itu terjadi.
        message: `"${item.name}" kembali beserta ${Math.max((hasil?.restored_count ?? 1) - 1, 0)} objek terkait.`,
      });
    } catch (err) {
      toastError(err, "Tidak bisa memulihkan.");
    } finally {
      setSibuk(null);
    }
  };

  const handleBuang = async (item: TTrashItem) => {
    if (!workspaceSlug || !projectId) return;
    // Konfirmasi wajib: ini satu-satunya aksi di halaman ini yang tidak bisa
    // dibatalkan, dan tombolnya bersebelahan dengan "Pulihkan".
    const yakin = window.confirm(
      `Buang "${item.name}" secara permanen?\n\nTidak bisa dibatalkan, barang ini tidak akan bisa dipulihkan lagi.`
    );
    if (!yakin) return;
    setSibuk(item.id);
    try {
      await trashService.purge(workspaceSlug.toString(), projectId.toString(), item.type, item.id);
      await muat();
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Dibuang permanen", message: `"${item.name}" sudah tidak ada.` });
    } catch (err) {
      toastError(err, "Tidak bisa membuang permanen.");
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
          <h3 className="text-xl font-medium">Tong sampah</h3>
          <p className="text-sm mt-1 text-secondary">
            Barang yang dihapus mampir ke sini{retensi ? ` selama ${retensi} hari` : ""} sebelum benar-benar dibuang.
            Kamu bisa memulihkannya atau membuangnya permanen.
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
          <p className="text-sm py-10 text-center text-secondary">Tong sampah kosong.</p>
        ) : (
          <div className="divide-y divide-subtle rounded border border-subtle">
            {items.map((item) => (
              <div key={`${item.type}-${item.id}`} className="flex items-center justify-between gap-4 px-4 py-3">
                <div className="min-w-0">
                  <p className="text-sm truncate font-medium text-primary">{item.name}</p>
                  <p className="text-xs mt-0.5 text-secondary">
                    {item.type_label} · dibuang {formatWaktu(item.deleted_at)}
                    {item.deleted_by ? ` oleh ${item.deleted_by.display_name || item.deleted_by.email}` : ""}
                    {" · "}
                    <span className={item.days_left <= 3 ? "text-red-600 font-medium" : ""}>
                      sisa {item.days_left} hari
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
                    <RotateCcw className="size-3.5" /> Pulihkan
                  </Button>
                  <Button
                    variant="error-outline"
                    size="sm"
                    disabled={sibuk === item.id}
                    onClick={() => handleBuang(item)}
                  >
                    <Trash2 className="size-3.5" /> Buang permanen
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
